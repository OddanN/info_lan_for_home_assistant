"""Version: 0.0.1. Sensor platform for the Info-Lan integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import CONF_LOGIN, DEFAULT_CURRENCY, DOMAIN
from .coordinator import InfoLanDataUpdateCoordinator

TOP_UP_YOUR_BALANCE_URL = "https://info-lan.ru/up/"
TARIFF_CHANGE_PLANNED = "Запланировано"
TARIFF_CHANGE_NOT_PLANNED = "Не запланировано"


@dataclass(frozen=True, slots=True)
class InfoLanSensorDescription:
    """Description of a text sensor."""

    key: str
    translation_key: str
    value_key: str
    icon: str
    entity_category: EntityCategory | None = None
    enabled_by_default: bool = True


SENSOR_DESCRIPTIONS: tuple[InfoLanSensorDescription, ...] = (
    InfoLanSensorDescription(
        "contract_number",
        "contract_number",
        "contract_number",
        "mdi:card-account-details-outline",
        EntityCategory.DIAGNOSTIC,
    ),
    InfoLanSensorDescription(
        "internet_status",
        "internet_status",
        "internet_status",
        "mdi:web",
        EntityCategory.DIAGNOSTIC,
        False,
    ),
    InfoLanSensorDescription(
        "connection_address",
        "connection_address",
        "connection_address",
        "mdi:home-map-marker",
        EntityCategory.DIAGNOSTIC,
    ),
    InfoLanSensorDescription(
        "contract_owner",
        "contract_owner",
        "contract_owner",
        "mdi:account-circle-outline",
        EntityCategory.DIAGNOSTIC,
    ),
    InfoLanSensorDescription("current_tariff", "current_tariff", "current_tariff", "mdi:speedometer"),
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
    entities.append(InfoLanLastUpdateSensor(coordinator, entry))
    entities.append(InfoLanTariffChangeSensor(coordinator, entry))
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
        login = entry.data[CONF_LOGIN]
        self._login = login
        self._login_slug = slugify(str(login))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"login_{self._login_slug}")},
            manufacturer="Info-Lan",
            model="Personal Account",
            name=f"Info-Lan: {login}",
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
        login = self.coordinator.data.get("login") or self._entry.data.get(CONF_LOGIN)
        if login:
            attrs["login"] = login
        return attrs


def _format_operation(operation: dict[str, Any]) -> str:
    """Convert an operation dict to a compact human-readable string."""
    date = operation.get("date")
    title = operation.get("operation")
    amount = operation.get("amount")
    currency = operation.get("currency")

    parts = [str(part) for part in (date, title) if part]
    if amount is not None:
        amount_part = str(amount)
        if currency:
            amount_part = f"{amount_part} {currency}"
        parts.append(amount_part)
    return " | ".join(parts)


def _copy_optional_attr(
        attrs: dict[str, Any],
        live_data: dict[str, Any],
        restored_attrs: dict[str, Any],
        source_key: str,
        attr_name: str | None = None,
) -> None:
    """Copy an attribute from live data or restored attributes when available."""
    target_name = attr_name or source_key
    value = live_data.get(source_key)
    if value is not None:
        attrs[target_name] = value
    elif target_name in restored_attrs:
        attrs[target_name] = restored_attrs[target_name]


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
        self._attr_icon = description.icon
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = description.enabled_by_default
        self._attr_unique_id = f"{entry.entry_id}_{self._login_slug}_{description.key}"
        self.entity_id = f"sensor.infolan_{self._login_slug}_{description.key}"

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
        if self._description.key == "contract_owner":
            self._add_contract_owner_attributes(attrs)
        if self._description.key == "current_tariff":
            self._add_current_tariff_attributes(attrs)
        return attrs

    def _add_contract_owner_attributes(self, attrs: dict[str, Any]) -> None:
        """Append SMS-related attributes to the counterparty sensor."""
        for source_key in ("sms_number", "sms_subscription"):
            _copy_optional_attr(attrs, self.coordinator.data, self._restored_attrs, source_key)

    def _add_current_tariff_attributes(self, attrs: dict[str, Any]) -> None:
        """Append tariff metadata to the current tariff sensor."""
        _copy_optional_attr(
            attrs,
            self.coordinator.data,
            self._restored_attrs,
            "current_tariff_full_name",
            "full_name",
        )
        _copy_optional_attr(attrs, self.coordinator.data, self._restored_attrs, "next_tariff")
        _copy_optional_attr(
            attrs,
            self.coordinator.data,
            self._restored_attrs,
            "next_tariff_full_name",
        )
        _copy_optional_attr(
            attrs,
            self.coordinator.data,
            self._restored_attrs,
            "current_tariff_valid_until",
            "valid_until",
        )


def _build_tariff_change_attributes(payload: dict[str, Any], restored_attrs: dict[str, Any]) -> dict[str, Any]:
    """Build tariff change attributes."""
    current_tariff = str(payload.get("current_tariff") or "").strip()
    next_tariff = str(payload.get("next_tariff") or "").strip()
    current_full_name = str(payload.get("current_tariff_full_name") or "").strip()
    next_full_name = str(payload.get("next_tariff_full_name") or "").strip()

    if not current_tariff:
        current_tariff = str(restored_attrs.get("current_tariff") or "").strip()
    if not next_tariff:
        next_tariff = str(restored_attrs.get("next_tariff") or "").strip()
    if not current_full_name:
        current_full_name = str(restored_attrs.get("current_tariff_full_name") or "").strip()
    if not next_full_name:
        next_full_name = str(restored_attrs.get("next_tariff_full_name") or "").strip()

    if not current_tariff or not next_tariff or current_tariff == next_tariff:
        return {}

    attributes = {
        "name": f'текущий "{current_tariff}" будет "{next_tariff}"',
        "current_tariff": current_tariff,
        "next_tariff": next_tariff,
    }
    if current_full_name:
        attributes["current_tariff_full_name"] = current_full_name
    if next_full_name:
        attributes["next_tariff_full_name"] = next_full_name
    return attributes


class InfoLanBalanceSensor(InfoLanBaseSensor):
    """Current balance sensor."""

    _attr_translation_key = "current_balance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:wallet-outline"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: InfoLanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the balance sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{self._login_slug}_current_balance"
        self.entity_id = f"sensor.infolan_{self._login_slug}_current_balance"

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
        attrs["top up your balance"] = TOP_UP_YOUR_BALANCE_URL

        total_operations = self.coordinator.data.get("operations_count")
        if total_operations is None:
            total_operations = self._restored_attrs.get("Total number of operations")
        if total_operations is not None:
            attrs["Total number of operations"] = int(total_operations)

        operations = self.coordinator.data.get("operations")
        if not operations:
            operations = self._restored_attrs.get("recent_operations") or []
        for index, operation in enumerate(reversed(list(operations)[-10:]), start=1):
            attrs[f"Operation {index}"] = _format_operation(operation)
        return attrs


class InfoLanLastUpdateSensor(InfoLanBaseSensor):
    """Last successful update timestamp sensor."""

    _attr_translation_key = "last_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: InfoLanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the last update sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{self._login_slug}_last_update"
        self.entity_id = f"sensor.infolan_{self._login_slug}_last_update"

    @property
    def native_value(self):
        """Return the last successful update time."""
        value = self.coordinator.data.get("updated_at")
        if value is None:
            value = self._restored_state
        if value is None:
            return None
        return dt_util.parse_datetime(str(value))


class InfoLanTariffChangeSensor(InfoLanBaseSensor):
    """Tariff change status sensor."""

    _attr_translation_key = "tariff_change"
    _attr_icon = "mdi:swap-horizontal-bold"

    def __init__(self, coordinator: InfoLanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the tariff change sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_{self._login_slug}_tariff_change"
        self.entity_id = f"sensor.infolan_{self._login_slug}_tariff_change"

    @property
    def native_value(self) -> str:
        """Return whether a tariff change is planned."""
        if _build_tariff_change_attributes(self.coordinator.data, self._restored_attrs):
            return TARIFF_CHANGE_PLANNED
        if self._restored_state:
            return self._restored_state
        return TARIFF_CHANGE_NOT_PLANNED

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return tariff change attributes."""
        attrs = super().extra_state_attributes
        attrs.update(_build_tariff_change_attributes(self.coordinator.data, self._restored_attrs))
        return attrs
