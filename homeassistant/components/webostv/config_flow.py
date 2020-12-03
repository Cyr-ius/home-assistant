"""Config flow to configure webostv component."""
import asyncio
import json
import logging

from aiopylgtv import PyLGTVCmdException, PyLGTVPairException, WebOsClient
import voluptuous as vol
from websockets.exceptions import ConnectionClosed

from homeassistant import config_entries
from homeassistant.const import CONF_CUSTOMIZE, CONF_HOST, CONF_ICON, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ON_ACTION,
    CONF_SOURCES,
    DEFAULT_NAME,
    DOMAIN,
    TURN_ON_DATA,
    TURN_ON_SERVICE,
    WEBOSTV_CONFIG_FILE,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_ICON): cv.string,
        vol.Optional(CONF_SOURCES): cv.string,
    },
    extra=vol.REMOVE_EXTRA,
)

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class FlowHandler(config_entries.ConfigFlow):
    """WebosTV configuration flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize workflow."""
        self.user_input = {}
        self.imported = False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_info):
        """Set the config entry up from yaml."""
        self.imported = True
        return await self.async_step_user(import_info)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            if user_input.get(CONF_CUSTOMIZE) is None:
                user_input.update({CONF_CUSTOMIZE: {CONF_SOURCES: []}})
                user_input[CONF_CUSTOMIZE][CONF_SOURCES] = user_input.get(
                    "sources", ""
                ).split(",")
            self.user_input = user_input
            return await self.async_step_pairing(user_input, True)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_pairing(self, user_input, pairing=False):
        """Display pairing form."""
        errors = {}
        if user_input is None:
            return await self.async_step_user()

        host = self.user_input.get(CONF_HOST)
        config_file = self.hass.config.path(WEBOSTV_CONFIG_FILE)
        _LOGGER.debug("LG webOS TV %s needs to be paired", host)

        if pairing is False or self.imported is True:
            self.imported = False
            client = WebOsClient(host, config_file, timeout_connect=10)
            try:
                await client.connect()
            except PyLGTVPairException:
                _LOGGER.warning("Connected to LG webOS TV %s but not paired", host)
                return self.async_abort(reason="cannot_connect")
            except (
                OSError,
                ConnectionClosed,
                ConnectionRefusedError,
                PyLGTVCmdException,
                asyncio.TimeoutError,
                asyncio.CancelledError,
            ):
                _LOGGER.error("Error to connect at %s", host)
                errors["base"] = "pairing"

            if errors:
                return self.async_show_form(step_id="pairing", errors=errors)

            if client.is_registered():
                return await self.async_step_register(self.user_input, client)

        return self.async_show_form(step_id="pairing", errors=errors)

    async def async_step_register(self, user_input, client=None):
        """Register entity."""
        if client.is_registered():
            host = user_input.get(CONF_HOST)
            return self.async_create_entry(title=host, data=user_input)

        return await self.async_step_user()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        service = data = None
        if self.config_entry.options.get(CONF_ON_ACTION):
            service = self.config_entry.options.get(CONF_ON_ACTION).get(
                TURN_ON_SERVICE, ""
            )
            data = json.dumps(
                self.config_entry.options.get(CONF_ON_ACTION).get(TURN_ON_DATA, "{}")
            )

        OPTIONS_SCHEMA = vol.Schema(
            {
                vol.Optional(
                    TURN_ON_SERVICE,
                    description={"suggested_value": service},
                ): str,
                vol.Optional(
                    TURN_ON_DATA,
                    default="{}",
                    description={"suggested_value": data},
                ): str,
            }
        )

        if user_input is not None:
            try:
                user_input = {
                    CONF_ON_ACTION: {
                        "service": user_input.get(TURN_ON_SERVICE),
                        "data": json.loads(user_input.get(TURN_ON_DATA)),
                    }
                }
                return self.async_create_entry(title="Turn on service", data=user_input)
            except json.decoder.JSONDecodeError as error:
                _LOGGER.error("Error JSON %s" % error)
                errors["base"] = "encode_json"

        return self.async_show_form(
            step_id="init", data_schema=OPTIONS_SCHEMA, errors=errors
        )
