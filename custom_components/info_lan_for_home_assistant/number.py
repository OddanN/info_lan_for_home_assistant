"""Number platform for the Info-Lan integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import CONF_LOGIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS, MAX_SCAN_INTERVAL_HOURS, \
    MIN_SCAN_INTERVAL_HOURS
from .helpers import build_device_info


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the scan interval number from a config entry."""
    async_add_entities([InfoLanScanIntervalNumber(hass, entry)])


class InfoLanScanIntervalNumber(NumberEntity):  # pylint: disable=abstract-method
    """Config entity for scan interval tuning."""

    _attr_translation_key = 'scan_interval'
    _attr_icon = 'mdi:timer-cog-outline'
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_SCAN_INTERVAL_HOURS
    _attr_native_max_value = MAX_SCAN_INTERVAL_HOURS
    _attr_native_step = 1
    _attr_native_unit_of_measurement = 'h'

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the scan interval number."""
        self.hass = hass
        self._entry = entry
        login = entry.data[CONF_LOGIN]
        login_slug = slugify(str(login))
        self._attr_unique_id = f"{entry.entry_id}_{login_slug}_scan_interval"
        self.entity_id = f"number.infolan_{login_slug}_scan_interval"
        self._attr_device_info = build_device_info(login, login_slug)

    @property
    def native_value(self) -> int:
        """Return the configured scan interval."""
        return int(self._entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS))

    async def async_set_native_value(self, value: float) -> None:
        """Update the scan interval and reload the entry."""
        value_int = max(self._attr_native_min_value, min(self._attr_native_max_value, int(round(value))))
        self.hass.config_entries.async_update_entry(self._entry,
                                                    options={**self._entry.options, CONF_SCAN_INTERVAL: value_int})
        await self.hass.config_entries.async_reload(self._entry.entry_id)
        self.async_write_ha_state()

    def set_native_value(self, value: float) -> None:
        """Satisfy the sync NumberEntity interface."""
