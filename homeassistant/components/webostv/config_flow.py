"""Config flow to configure webostv component."""
import json
import logging

from aiopylgtv import PyLGTVPairException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CUSTOMIZE, CONF_HOST, CONF_ICON, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from . import CannotConnect, async_control_connect
from .const import (
    CONF_ON_ACTION,
    CONF_SOURCES,
    DEFAULT_NAME,
    DEFAULT_SOURCES,
    DOMAIN,
    TURN_ON_DATA,
    TURN_ON_SERVICE,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_ICON): cv.string,
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_info):
        """Set the config entry up from yaml."""
        return await self.async_step_user(import_info)

    async def async_step_user(self, user_input=None, is_imported=False):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:

            host = user_input[CONF_HOST]
            # check exist
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Get Turn_on service
            turn_on_service = user_input.get(CONF_ON_ACTION, {})
            services = {}
            for service in turn_on_service:
                services.update(service)
            user_input[CONF_ON_ACTION] = services

            # Get Sources
            sources = user_input[CONF_SOURCES] = user_input.get(CONF_CUSTOMIZE, {}).get(
                CONF_SOURCES, []
            )
            user_input.pop(CONF_CUSTOMIZE, None)
            if isinstance(sources, list) is False:
                user_input[CONF_SOURCES] = sources.split(",")

            # save for pairing
            self.user_input = user_input

            return await self.async_step_pairing()

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_pairing(self, user_input=None):
        """Display pairing form."""
        errors = {}

        host = self.user_input.get(CONF_HOST)
        _LOGGER.debug("LG webOS TV %s needs to be paired", host)

        if user_input is not None:
            self.imported = False
            try:
                client = await async_control_connect(self.hass, host)
            except PyLGTVPairException:
                return self.async_abort(reason="error_pairing")
            except CannotConnect:
                errors["base"] = "cannot_connect"

            if errors:
                return self.async_show_form(step_id="pairing", errors=errors)

            if client.is_registered():
                return await self.async_step_register(self.user_input, client)

        return self.async_show_form(
            step_id="pairing", data_schema=vol.Schema({}), errors=errors
        )

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
        self.options = config_entry.options

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            try:
                data_input = {
                    CONF_ON_ACTION: {
                        "service": user_input.get(TURN_ON_SERVICE, ""),
                        "data": json.loads(user_input.get(TURN_ON_DATA)),
                    },
                    CONF_SOURCES: user_input[CONF_SOURCES],
                }
                return self.async_create_entry(title="", data=data_input)
            except json.decoder.JSONDecodeError as error:
                _LOGGER.error("Error JSON %s" % error)
                errors["base"] = "encode_json"

        client = await async_control_connect(
            self.hass, self.config_entry.data[CONF_HOST]
        )
        service = self.options.get(CONF_ON_ACTION, {}).get(TURN_ON_SERVICE, "")
        data = json.dumps(self.options.get(CONF_ON_ACTION, {}).get(TURN_ON_DATA, "{}"))
        sources = await async_default_sources(client)

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
                vol.Optional(
                    CONF_SOURCES,
                    description={
                        "suggested_value": self.options.get(
                            CONF_SOURCES, DEFAULT_SOURCES
                        )
                    },
                ): cv.multi_select(sources),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=OPTIONS_SCHEMA, errors=errors
        )


async def async_default_sources(client) -> list:
    """Construct sources list."""
    sources = []
    for app in client.apps.values():
        sources.append(app["title"])
    for source in client.inputs.values():
        sources.append(source["label"])
    return sources
