"""Config flow to configure webostv component."""
import logging

from aiopylgtv import PyLGTVPairException, WebOsClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CUSTOMIZE, CONF_HOST, CONF_ICON, CONF_NAME
from homeassistant.helpers import config_validation as cv

from . import async_request_configuration, async_setup_tv_finalize
from .const import (
    CONF_ON_ACTION,
    CONF_SOURCES,
    DEFAULT_NAME,
    DOMAIN,
    WEBOSTV_CONFIG_FILE,
)

CUSTOMIZE_SCHEMA = vol.Schema(
    {vol.Optional(CONF_SOURCES, default=[]): vol.All(cv.ensure_list, [cv.string])}
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CUSTOMIZE, default={}): CUSTOMIZE_SCHEMA,
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_ON_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_ICON): str,
    }
)

_LOGGER = logging.getLogger(__name__)


class WebostvFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """WebosTV configuration flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_import(self, import_info):
        """Set the config entry up from yaml."""
        return await self.async_step_init(import_info)

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            try:
                host = user_input[CONF_HOST]
                config_file = self.hass.config.path(WEBOSTV_CONFIG_FILE)

                client = WebOsClient(host, config_file)
                self.hass.data[DOMAIN][host] = {"client": client}

                if client.is_registered():
                    await async_setup_tv_finalize(self.hass, user_input, client)
                else:
                    await self.async_step_pairing(user_input, client)
            except Exception as error:
                _LOGGER.debug(error)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_pairing(self, user_input, client):
        """Display pairing form."""
        errors = {}
        host = user_input[CONF_HOST]
        try:
            _LOGGER.warning("LG webOS TV needs to be paired")
            await async_request_configuration(self.hass, user_input, client)
        except PyLGTVPairException:
            _LOGGER.error("Error pairing to Webostv at %s", host)
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unknown error connecting with Webostv at %s", host)
            errors["base"] = "pairing"

        if errors:
            return self.async_show_form(step_id="pairing", errors=errors)

        return self.async_create_entry(title=host, data=user_input)
