"""Config flow to configure Heatzy."""
import logging

import voluptuous as vol

from homeassistant import config_entries
<<<<<<< HEAD
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import aiohttp_client, storage

from .api import HeatzyAPI
from .authenticator import HeatzyAuthenticator
from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION
=======
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from heatzypy import HeatzyClient
from .const import DOMAIN
>>>>>>> 6e0c3981a... Replace api to heatzypy

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)

_LOGGER = logging.getLogger(__name__)


class HeatzyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Heatzy config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Heatzy flow."""
        self.username = None
        self.password = None

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        errors = {}
        if user_input is not None:
            self.username = user_input[CONF_USERNAME]
            self.password = user_input[CONF_PASSWORD]

            try:
                api = HeatzyClient(self.username, self.password)
                devices = await api.async_get_devices()
                if devices is not None:
                    return await self.async_step_register()

            except Exception:
                errors["base"] = "login_inccorect"

        # If there was no user input, do not show the errors.
        else:
            errors = {}

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_register(self, user_input=None):
        """Step for register component."""

        return self.async_create_entry(
            title=DOMAIN,
            data={
                "id": DOMAIN,
                CONF_USERNAME: self.username,
                CONF_PASSWORD: self.password,
            },
        )
        return self.async_show_form(step_id="register")
