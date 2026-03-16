"""Number platform for the Info-Lan integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import CONF_LOGIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN, MAX_SCAN_INTERVAL_HOURS, \
    MIN_SCAN_INTERVAL_HOURS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([InfoLanScanIntervalNumber(hass, entry, coordinator)])


class InfoLanScanIntervalNumber(NumberEntity):
    _attr_translation_key = 'scan_interval'
    _attr_icon = 'mdi:timer-cog-outline'
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_SCAN_INTERVAL_HOURS
    _attr_native_max_value = MAX_SCAN_INTERVAL_HOURS
    _attr_native_step = 1
    _attr_native_unit_of_measurement = 'h'

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator) -> None:
        self.hass = hass
        self._entry = entry
        login = entry.data[CONF_LOGIN]
        login_slug = slugify(str(login))
        self._attr_unique_id = f"{entry.entry_id}_{login_slug}_scan_interval"
        self.entity_id = f"number.infolan_{login_slug}_scan_interval"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"login_{login_slug}")},
            manufacturer='Info-Lan',
            model='Personal Account',
            name=f"Info-Lan: {login}",
        )

    @property
    def native_value(self) -> int:
        return int(self._entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS))

    async def async_set_native_value(self, value: float) -> None:
        value_int = max(self._attr_native_min_value, min(self._attr_native_max_value, int(round(value))))
        self.hass.config_entries.async_update_entry(self._entry,
                                                    options={**self._entry.options, CONF_SCAN_INTERVAL: value_int})
        await self.hass.config_entries.async_reload(self._entry.entry_id)
        self.async_write_ha_state()
