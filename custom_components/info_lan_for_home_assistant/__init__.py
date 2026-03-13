"""Version: 0.0.1. The Info-Lan integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import InfoLanApiClient, InfoLanAuthError
from .const import CONF_LOGIN, DOMAIN
from .coordinator import InfoLanDataUpdateCoordinator

type InfoLanConfigEntry = ConfigEntry[InfoLanApiClient]

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up the integration from YAML."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: InfoLanConfigEntry) -> bool:
    """Set up Info-Lan from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    client = InfoLanApiClient(
        hass=hass,
        login=entry.data[CONF_LOGIN],
        password=entry.data[CONF_PASSWORD],
    )
    coordinator = InfoLanDataUpdateCoordinator(hass, client, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except InfoLanAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except Exception as err:
        raise ConfigEntryNotReady(str(err)) from err

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    entry.runtime_data = client
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
