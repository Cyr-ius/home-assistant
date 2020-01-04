"""API for PiloteV1."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    SUPPORT_PRESET_MODE,
)
from homeassistant.util import Throttle
from homeassistant.const import TEMP_CELSIUS

from .const import DOMAIN

HEATZY_TO_HA_STATE = {
    "\u8212\u9002": PRESET_COMFORT,
    "\u7ecf\u6d4e": PRESET_ECO,
    "\u89e3\u51bb": PRESET_AWAY,
    "\u505c\u6b62": PRESET_NONE,
}

HA_TO_HEATZY_STATE = {
    PRESET_COMFORT: [1, 1, 0],
    PRESET_ECO: [1, 1, 1],
    PRESET_AWAY: [1, 1, 2],
    PRESET_NONE: [1, 1, 3],
}

MODE_LIST = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
PRESET_LIST = [PRESET_NONE, PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)


class HeatzyPiloteV1Thermostat(ClimateDevice):
    """Heaty Pilote v1."""

    def __init__(self, did, api, device):
        """Init V1."""
        self._did = did
        self._api = api
        self._heater = device
        self._heater_detail = {}

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_PRESET_MODE

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._did

    @property
    def name(self):
        """Return a name."""
        return self._heater.get("dev_alias")

    @property
    def device_info(self):
        """Return the device info."""

        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": DOMAIN,
            "model": self._heater.get("product_name"),
            "sw_version": self._heater.get("wifi_soft_version"),
        }

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return MODE_LIST

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        if self.preset_mode == PRESET_NONE:
            return HVAC_MODE_OFF
        return HVAC_MODE_HEAT

    @property
    def preset_modes(self):
        """Return a list of available preset modes.

        Requires SUPPORT_PRESET_MODE.
        """
        return PRESET_LIST

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.

        Requires SUPPORT_PRESET_MODE.
        """
        return HEATZY_TO_HA_STATE.get(self._heater_detail.get("attr", {}).get("mode"))

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        _LOGGER.debug(
            "Set PRESET MODE : {}".format(HA_TO_HEATZY_STATE.get(preset_mode))
        )
        await self._api.async_control_device(
            self.unique_id, {"raw": HA_TO_HEATZY_STATE.get(preset_mode)}
        )
        await self.async_update_heater(True)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new hvac mode."""
        _LOGGER.debug(f"Set HVAC MODE {hvac_mode}")
        if hvac_mode == HVAC_MODE_OFF:
            await self.async_turn_off()
        elif hvac_mode == HVAC_MODE_HEAT:
            await self.async_turn_on()

    async def async_turn_on(self):
        """Turn device on."""
        _LOGGER.debug("HVAC Turn On")
        await self.async_set_preset_mode(PRESET_COMFORT)

    async def async_turn_off(self):
        """Turn device off."""
        _LOGGER.debug("HVAC Turn off")
        await self.async_set_preset_mode(PRESET_NONE)

    async def async_update_heater(self, force_update=False):
        """Get the latest state from the thermostat."""
        if force_update is True:
            # Updated temperature to HA state to avoid flapping (API confirmation is slow)
            await asyncio.sleep(1)
        data_status = await self._api.async_get_device(self.unique_id)
        if data_status:
            self._heater_detail = data_status

    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """Update device."""
        await self.async_update_heater()
