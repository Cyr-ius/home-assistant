"""Test the WebOS Tv config flow."""
from homeassistant import config_entries, setup
from homeassistant.components.webostv.const import (
    CONF_SOURCES,
    DOMAIN,
    TURN_ON_DATA,
    TURN_ON_SERVICE,
)
from homeassistant.const import CONF_HOST, CONF_ICON, CONF_NAME
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM

from tests.async_mock import patch
from tests.common import MockConfigEntry

MOCK_YAML_CONFIG = {
    CONF_HOST: "1.2.3.4",
    CONF_NAME: "LG MYTV",
    CONF_ICON: "mdi:test",
}

MOCK_OPTIIONS = {
    TURN_ON_SERVICE: "service.test",
    TURN_ON_DATA: "message:Hello,title:World",
    CONF_SOURCES: "HDMI1",
}

MOCK_API = {}


async def test_form_import(hass):
    """Test we can import yaml config."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MOCK_YAML_CONFIG,
    )

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["step_id"] == "pairing"

    with patch(
        "homeassistant.components.webostv.config_flow.async_control_connect",
        return_value=MOCK_API,
    ), patch(
        "homeassistant.components.qnap.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.qnap.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    await hass.async_block_till_done()
    assert result["type"] == RESULT_TYPE_CREATE_ENTRY

    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})


async def test_options_flow(hass):
    """Test options config flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.2.3.4",
        },
        unique_id=123456,
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.webostv.config_flow.async_control_connect",
        return_value=MOCK_API,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=MOCK_OPTIIONS
    )
    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    await hass.async_block_till_done()
