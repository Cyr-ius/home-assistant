"""Heatzy platform configuration."""
import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
<<<<<<< HEAD
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import aiohttp_client, config_validation as cv, storage

from .api import HeatzyAPI
from .authenticator import HeatzyAuthenticator
from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION
=======

from heatzypy import HeatzyClient
from .const import DOMAIN
>>>>>>> 6e0c3981a... Replace api to heatzypy

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config_entry):
    """Load configuration for Heatzy component."""

    if not hass.config_entries.async_entries(DOMAIN) and DOMAIN in config_entry:
        heatzy_config = config_entry[DOMAIN]
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=heatzy_config
            )
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up Heatzy as config entry."""

    if config_entry.data is not None:
        api = HeatzyClient(config_entry.data["username"], config_entry.data["password"])
        devices = await api.async_get_devices()
        if devices is not None:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(config_entry, "climate")
            )
            return True

    return False


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_unload(config_entry, "climate")
    )
    return True
