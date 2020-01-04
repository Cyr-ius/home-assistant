"""Climate sensors for Heatzy."""
import logging

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from heatzypy import HeatzyClient
from .const import (
    HEATZY_PILOTE_V1_PRODUCT_KEY,
    HEATZY_PILOTE_V2_PRODUCT_KEY,
)
from .pilote_v1 import HeatzyPiloteV1Thermostat
from .pilote_v2 import HeatzyPiloteV2Thermostat

PRODUCT_KEY_TO_DEVICE_IMPLEMENTATION = {
    HEATZY_PILOTE_V1_PRODUCT_KEY: HeatzyPiloteV1Thermostat,
    HEATZY_PILOTE_V2_PRODUCT_KEY: HeatzyPiloteV2Thermostat,
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Configure Heatzy API using Home Assistant configuration and fetch all Heatzy devices."""
    username = config_entry.data.get(CONF_USERNAME)
    password = config_entry.data.get(CONF_PASSWORD)

    api = HeatzyClient(username, password)
    devices = await api.async_get_devices()
    heaters = filter(None.__ne__, map(setup_heatzy_device(api), devices))

    devices = []
    for heater in heaters:
        devices.append(heater)

    _LOGGER.info("Found {count} heaters".format(count=len(devices)))
    async_add_entities(devices, True)


def setup_heatzy_device(api):
    """Set heatzy device."""

    def find_heatzy_device_implementation(device):
        """Find Home Assistant implementation for the Heatzy device.

        Implementation search is based on device 'product_key'.

        If the implementation is not found, returns None.
        """
        DeviceImplementation = PRODUCT_KEY_TO_DEVICE_IMPLEMENTATION.get(
            device.get("product_key")
        )
        if DeviceImplementation is None:
            _LOGGER.warn(
                "Device %s with product key %s is not supported",
                device.get("did"),
                device.get("product_key"),
            )
            return None
        return DeviceImplementation(api, device)

    return find_heatzy_device_implementation
