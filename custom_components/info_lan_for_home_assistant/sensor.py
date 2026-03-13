"""Version: 0.0.1. Sensor platform for the Info-Lan integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_LOGIN, DEFAULT_CURRENCY, DOMAIN
from .coordinator import InfoLanDataUpdateCoordinator


@dataclass(frozen=True, slots=True)
class InfoLanSensorDescription:
    """Description of a text sensor."""

    key: str
    translation_key: str
    value_key: str


SENSOR_DESCRIPTIONS: tuple[InfoLanSensorDescription, ...] = (
    InfoLanSensorDescription("contract_number", "contract_number", "contract_number"),
    InfoLanSensorDescription("internet_status", "internet_status", "internet_status"),
    InfoLanSensorDescription("connection_address", "connection_address", "connection_address"),
    InfoLanSensorDescription("contract_owner", "contract_owner", "contract_owner"),
    InfoLanSensorDescription("sms_number", "sms_number", "sms_number"),
    InfoLanSensorDescription("sms_subscription", "sms_subscription", "sms_subscription"),
    InfoLanSensorDescription("current_tariff", "current_tariff", "current_tariff"),
    InfoLanSensorDescription("next_tariff", "next_tariff", "next_tariff"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Info-Lan sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = [
        InfoLanTextSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(InfoLanBalanceSensor(coordinator, entry))
    entities.append(InfoLanOperationsSensor(coordinator, entry))
    async_add_entities(entities)


class InfoLanBaseSensor(
    CoordinatorEntity[InfoLanDataUpdateCoordinator], RestoreEntity, SensorEntity
):
    """Base class for Info-Lan sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: InfoLanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize a base sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._restored_state: str | None = None
        self._restored_attrs: dict[str, Any] = {}
        contract_number = coordinator.data.get("contract_number") or entry.data[CONF_LOGIN]
        self._contract_slug = slugify(str(contract_number))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"contract_{contract_number}")},
            manufacturer="Info-Lan",
            model="Personal Account",
            name=f"Info-Lan {contract_number}",
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last known state before the first successful update."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        self._restored_state = last_state.state
        self._restored_attrs = dict(last_state.attributes)

    @property
    def available(self) -> bool:
        """Keep entities available while live or restored data exists."""
        return self._has_live_data or self._restored_state is not None

    @property
    def _has_live_data(self) -> bool:
        """Return whether the coordinator currently has live data."""
        return bool(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return common attributes."""
        attrs = {}
        last_update = self.coordinator.data.get("updated_at")
        if last_update is not None:
            attrs["last_update"] = last_update
        elif "last_update" in self._restored_attrs:
            attrs["last_update"] = self._restored_attrs["last_update"]

        login = self.coordinator.data.get("login") or self._entry.data.get(CONF_LOGIN)
        if login:
            attrs["login"] = login
        return attrs


class InfoLanTextSensor(InfoLanBaseSensor):
    """Text sensor backed by one parsed field."""

    def __init__(
        self,
        coordinator: InfoLanDataUpdateCoordinator,
        entry: ConfigEntry,
        description: InfoLanSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._description = description
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{entry.entry_id}_{self._contract_slug}_{description.key}"

    @property
    def native_value(self) -> str | None:
        """Return the parsed value."""
        value = self.coordinator.data.get(self._description.value_key)
        if value is not None:
            return str(value)
        return self._restored_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes for current tariff."""
        attrs = super().extra_state_attributes
        if self._description.key == "current_tariff":
            valid_until = self.coordinator.data.get("current_tariff_valid_until")
            if valid_until:
                attrs["valid_until"] = valid_until
            elif "valid_until" in self._restored_attrs:
                attrs["valid_until"] = self._restored_attrs["valid_until"]
        return attrs


class InfoLanBalanceSensor(InfoLanBaseSensor):
    """Current balance sensor."""

    _attr_translation_key = "current_balance"
    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(self, coordinator: InfoLanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the balance sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{self._contract_slug}_current_balance"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the balance currency."""
        return str(self.coordinator.data.get("balance_currency") or DEFAULT_CURRENCY)

    @property
    def native_value(self) -> float | None:
        """Return the current balance."""
        value = self.coordinator.data.get("current_balance")
        if isinstance(value, (int, float)):
            return value
        if self._restored_state is None:
            return None
        try:
            return float(self._restored_state)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return balance metadata."""
        attrs = super().extra_state_attributes
        for source_key, attr_name in (
            ("balance_timestamp", "balance_timestamp"),
            ("promised_payment_limit", "promised_payment_limit"),
            ("block_threshold", "block_threshold"),
        ):
            value = self.coordinator.data.get(source_key)
            if value is not None:
                attrs[attr_name] = value
            elif attr_name in self._restored_attrs:
                attrs[attr_name] = self._restored_attrs[attr_name]
        attrs["currency"] = self.native_unit_of_measurement
        return attrs


class InfoLanOperationsSensor(InfoLanBaseSensor):
    """Operations list summary sensor."""

    _attr_translation_key = "operations"

    def __init__(self, coordinator: InfoLanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the operations sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{self._contract_slug}_operations"

    @property
    def native_value(self) -> int:
        """Return the number of parsed operations."""
        value = self.coordinator.data.get("operations_count")
        if value is not None:
            return int(value)
        if self._restored_state is None:
            return 0
        try:
            return int(float(self._restored_state))
        except (TypeError, ValueError):
            return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return recent operations and aggregates."""
        attrs = super().extra_state_attributes
        operations = self.coordinator.data.get("operations", [])
        recent_operations = self.coordinator.data.get("recent_operations", [])
        attrs["recent_operations"] = (
            recent_operations
            if recent_operations
            else self._restored_attrs.get("recent_operations", [])
        )
        if operations:
            attrs["first_operation"] = operations[0]
            attrs["latest_operation"] = operations[-1]
        else:
            if "first_operation" in self._restored_attrs:
                attrs["first_operation"] = self._restored_attrs["first_operation"]
            if "latest_operation" in self._restored_attrs:
                attrs["latest_operation"] = self._restored_attrs["latest_operation"]
        return attrs
