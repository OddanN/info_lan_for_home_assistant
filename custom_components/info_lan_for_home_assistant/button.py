"""Version: 1.0.0. Button platform for the Info-Lan integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_LOGIN, DOMAIN
from .helpers import build_device_info


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the refresh button from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([InfoLanRefreshButton(entry, coordinator)])


class InfoLanRefreshButton(CoordinatorEntity, ButtonEntity):
    """Manual refresh button entity."""

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
        self._attr_device_info = build_device_info(login, login_slug)

    async def async_press(self) -> None:
        """Handle the async button press."""
        await self.coordinator.async_refresh()

    def press(self) -> None:
        """Satisfy the sync ButtonEntity interface."""
