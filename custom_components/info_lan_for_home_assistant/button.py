"""Button platform for the Info-Lan integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_LOGIN, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([InfoLanRefreshButton(entry, coordinator)])


class InfoLanRefreshButton(CoordinatorEntity, ButtonEntity):
    _attr_translation_key = 'refresh'
    _attr_icon = 'mdi:refresh'
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        ButtonEntity.__init__(self)
        login = entry.data[CONF_LOGIN]
        login_slug = slugify(str(login))
        self._attr_unique_id = f"{entry.entry_id}_{login_slug}_refresh"
        self.entity_id = f"button.infolan_{login_slug}_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"login_{login_slug}")},
            manufacturer='Info-Lan',
            model='Personal Account',
            name=f"Info-Lan: {login}",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_refresh()
