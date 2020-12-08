"""Support for LG webOS Smart TV."""
import asyncio
import logging

from aiopylgtv import PyLGTVCmdException, PyLGTVPairException, WebOsClient
import voluptuous as vol
from websockets.exceptions import ConnectionClosed

from homeassistant import exceptions
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_CUSTOMIZE,
    CONF_HOST,
    CONF_ICON,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_BUTTON,
    ATTR_COMMAND,
    ATTR_PAYLOAD,
    ATTR_SOUND_OUTPUT,
    COMPONENTS,
    CONF_ON_ACTION,
    CONF_SOURCES,
    DEFAULT_NAME,
    DOMAIN,
    SERVICE_BUTTON,
    SERVICE_COMMAND,
    SERVICE_SELECT_SOUND_OUTPUT,
    WEBOSTV_CONFIG_FILE,
)

CUSTOMIZE_SCHEMA = vol.Schema(
    {vol.Optional(CONF_SOURCES, default=[]): vol.All(cv.ensure_list, [cv.string])}
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Optional(CONF_CUSTOMIZE, default={}): CUSTOMIZE_SCHEMA,
                        vol.Required(CONF_HOST): cv.string,
                        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                        vol.Optional(CONF_ON_ACTION): cv.SCRIPT_SCHEMA,
                        vol.Optional(CONF_ICON): cv.string,
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

CALL_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids})

BUTTON_SCHEMA = CALL_SCHEMA.extend({vol.Required(ATTR_BUTTON): cv.string})

COMMAND_SCHEMA = CALL_SCHEMA.extend(
    {vol.Required(ATTR_COMMAND): cv.string, vol.Optional(ATTR_PAYLOAD): dict}
)

SOUND_OUTPUT_SCHEMA = CALL_SCHEMA.extend({vol.Required(ATTR_SOUND_OUTPUT): cv.string})

SERVICE_TO_METHOD = {
    SERVICE_BUTTON: {"method": "async_button", "schema": BUTTON_SCHEMA},
    SERVICE_COMMAND: {"method": "async_command", "schema": COMMAND_SCHEMA},
    SERVICE_SELECT_SOUND_OUTPUT: {
        "method": "async_select_sound_output",
        "schema": SOUND_OUTPUT_SCHEMA,
    },
}

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the roomba environment."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    for index, conf in enumerate(config[DOMAIN]):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
            )
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Set the config entry up."""
    if not config_entry.options:
        options = {}
        options[CONF_ON_ACTION] = config_entry.data.get(CONF_ON_ACTION, {})
        options[CONF_SOURCES] = config_entry.data.get(CONF_SOURCES, [])
        hass.config_entries.async_update_entry(config_entry, options=options)

    host = config_entry.data[CONF_HOST]
    config_file = hass.config.path(WEBOSTV_CONFIG_FILE)

    client = WebOsClient(host, config_file)
    hass.data[DOMAIN][host] = {"client": client}

    if client.is_registered():

        async def async_service_handler(service):
            method = SERVICE_TO_METHOD.get(service.service)
            data = service.data.copy()
            data["method"] = method["method"]
            async_dispatcher_send(hass, DOMAIN, data)

        for service in SERVICE_TO_METHOD:
            schema = SERVICE_TO_METHOD[service]["schema"]
            hass.services.async_register(
                DOMAIN, service, async_service_handler, schema=schema
            )

        for component in COMPONENTS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(config_entry, component)
            )

        hass.async_create_task(
            hass.helpers.discovery.async_load_platform(
                "notify",
                DOMAIN,
                {CONF_HOST: host, CONF_ICON: config_entry.data.get(CONF_ICON)},
                hass.data[DOMAIN],
            )
        )

        if not config_entry.update_listeners:
            config_entry.add_update_listener(async_update_options)

        async def async_on_stop(event):
            """Unregister callbacks and disconnect."""
            client.clear_state_update_callbacks()
            await client.disconnect()

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_on_stop)

        await async_connect(client)

    else:
        _LOGGER.warning("LG webOS TV %s needs to be paired, see Integration", host)
        return False

    return True


async def async_update_options(hass, config_entry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    host = config_entry.data[CONF_HOST]
    client = hass.data[DOMAIN][host]["client"]
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in COMPONENTS
            ]
        )
    )

    if unload_ok:
        client.clear_state_update_callbacks()
        await client.disconnect()

    return unload_ok


async def async_connect(client):
    """Attempt a connection, but fail gracefully if tv is off for example."""
    try:
        await client.connect()
    except (
        OSError,
        ConnectionClosed,
        ConnectionRefusedError,
        asyncio.TimeoutError,
        asyncio.CancelledError,
        PyLGTVPairException,
        PyLGTVCmdException,
    ):
        pass


async def async_control_connect(hass, host: str) -> WebOsClient:
    """LG Connection."""
    config_file = hass.config.path(WEBOSTV_CONFIG_FILE)
    client = WebOsClient(host, config_file, timeout_connect=10)
    try:
        await client.connect()
    except PyLGTVPairException as error:
        _LOGGER.warning("Connected to LG webOS TV %s but not paired", host)
        raise PyLGTVPairException(error)
    except (
        OSError,
        ConnectionClosed,
        ConnectionRefusedError,
        PyLGTVCmdException,
        asyncio.TimeoutError,
        asyncio.CancelledError,
    ) as error:
        _LOGGER.error("Error to connect at %s", host)
        raise CannotConnect(error)

    return client


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
