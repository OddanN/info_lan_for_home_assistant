"""Version: 0.0.1. Client and parser for the Info-Lan personal account page."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html import unescape
from typing import Any

from aiohttp import ClientError, FormData
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_CURRENCY, INFO_LAN_URL, RECENT_OPERATIONS_LIMIT

_LOGGER = logging.getLogger(__name__)

_SPACE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_ROW_RE = re.compile(r"(<tr\b[^>]*>.*?</tr>)", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
_OPTION_SELECTED_RE = re.compile(
    r"<option\b[^>]*selected[^>]*>(.*?)</option>", re.IGNORECASE | re.DOTALL
)
_INPUT_VALUE_RE = re.compile(
    r'<input\b[^>]*name="(?P<name>[^"]+)"[^>]*value="(?P<value>[^"]*)"',
    re.IGNORECASE,
)
_CONTRACT_RE = re.compile(r"<title>\s*([^<]+?)\s*\(", re.IGNORECASE)
_DATE_IN_TITLE_RE = re.compile(r"^(?P<label>.+?)\s*\((?P<meta>.+?)\):?$")
_BALANCE_RE = re.compile(r"(?P<value>[-+]?\d[\d\s]*,\d+)\s*(?P<currency>[^\s.]+\.?)?")
_OPERATION_DATE_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
_SIMPLE_SUMMARY_FIELDS = (
    ("Номер договора", "contract_number"),
    ("Статус доступа в Интернет", "internet_status"),
    ("Адрес подключения", "connection_address"),
    ("Договор оформлен на", "contract_owner"),
)


class InfoLanError(Exception):
    """Base Info-Lan error."""


class InfoLanConnectionError(InfoLanError):
    """Raised when the Info-Lan website cannot be reached."""


class InfoLanAuthError(InfoLanError):
    """Raised on invalid credentials."""


class InfoLanParseError(InfoLanError):
    """Raised when the page cannot be parsed."""


@dataclass(slots=True)
class InfoLanOperation:
    """One money report row."""

    date: str
    amount: float | None
    currency: str
    operation: str
    operation_type: str
    period_from: str | None = None
    period_to: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        payload: dict[str, Any] = {
            "date": self.date,
            "amount": self.amount,
            "currency": self.currency,
            "operation": self.operation,
            "type": self.operation_type,
        }
        if self.period_from:
            payload["period_from"] = self.period_from
        if self.period_to:
            payload["period_to"] = self.period_to
        return payload


class InfoLanApiClient:
    """Info-Lan HTML client."""

    def __init__(
        self,
        hass: HomeAssistant,
        login: str,
        password: str,
    ) -> None:
        """Initialize the client."""
        self._session = async_get_clientsession(hass)
        self._login = login
        self._password = password

    async def async_fetch_data(self) -> dict[str, Any]:
        """Authenticate and return parsed account data."""
        form = FormData(default_to_multipart=True)
        form.add_field("userlogin", self._login)
        form.add_field("userpassword", self._password)
        form.add_field("button", "Войти")
        try:
            async with self._session.post(
                INFO_LAN_URL,
                data=form,
            ) as response:
                response.raise_for_status()
                html = await response.text()
        except ClientError as err:
            raise InfoLanConnectionError(str(err)) from err

        if "name=\"userlogin\"" in html and "name=\"userpassword\"" in html:
            raise InfoLanAuthError("Authentication failed")

        try:
            return _parse_account_page(html, self._login)
        except InfoLanParseError:
            raise
        except Exception as err:
            raise InfoLanParseError(str(err)) from err

    async def async_validate_credentials(self) -> dict[str, Any]:
        """Validate credentials and return account data."""
        return await self.async_fetch_data()


def _parse_account_page(html: str, fallback_login: str) -> dict[str, Any]:
    """Parse the returned personal-account HTML."""
    if "Номер договора:" not in html or "Детальный отчет по балансу" not in html:
        raise InfoLanParseError("Expected account blocks were not found")

    main_table_start = html.find("<table border=\"1\" style=\"width: 770px; margin: auto;\" class=\"stats\">")
    report_marker = html.find("Детальный отчет по балансу")
    if main_table_start == -1 or report_marker == -1:
        raise InfoLanParseError("Unable to locate main tables")

    report_table_start = html.find("<table", report_marker)
    if report_table_start == -1:
        raise InfoLanParseError("Unable to locate report table")

    main_table_html = _extract_table(html, main_table_start)
    report_table_html = _extract_table(html, report_table_start)

    summary = _parse_summary_table(main_table_html)
    operations = _parse_operations_table(report_table_html)

    contract_match = _CONTRACT_RE.search(html)
    if contract_match and not summary.get("contract_number"):
        summary["contract_number"] = _normalize_space(_strip_tags(contract_match.group(1)))

    summary["contract_number"] = summary.get("contract_number") or fallback_login
    summary["operations"] = [operation.as_dict() for operation in operations]
    summary["operations_count"] = len(operations)
    summary["recent_operations"] = [
        operation.as_dict() for operation in operations[-RECENT_OPERATIONS_LIMIT:]
    ]
    summary["login"] = fallback_login
    return summary


def _extract_table(html: str, start_index: int) -> str:
    """Extract one full table by balancing nested tags."""
    depth = 0
    index = start_index
    while index < len(html):
        next_open = html.find("<table", index)
        next_close = html.find("</table>", index)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            index = next_open + 6
            continue
        depth -= 1
        index = next_close + 8
        if depth == 0:
            return html[start_index:index]
    raise InfoLanParseError("Unbalanced table markup")


def _parse_summary_table(table_html: str) -> dict[str, Any]:
    """Parse the upper account summary table."""
    data: dict[str, Any] = {}
    for row_html in _ROW_RE.findall(table_html):
        cells = _CELL_RE.findall(row_html)
        if len(cells) < 2:
            continue

        title = _extract_title(cells[0])
        if not title:
            continue

        if _parse_special_summary_row(data, title, cells[-1]):
            continue

        value = _normalize_space(_strip_tags(cells[-1]))
        if _parse_simple_summary_field(data, title, value):
            continue

        if "Максимальный обещанный платеж" in title:
            promise_value, currency = _parse_money(value)
            data["promised_payment_limit"] = promise_value
            data["promised_payment_currency"] = currency or DEFAULT_CURRENCY
        elif "Порог блокировки" in title:
            threshold_value, currency = _parse_money(value)
            data["block_threshold"] = threshold_value
            data["block_threshold_currency"] = currency or DEFAULT_CURRENCY

    return data


def _parse_special_summary_row(data: dict[str, Any], title: str, value_html: str) -> bool:
    """Parse summary rows that need special handling."""
    for marker, handler in (
            ("Номер для SMS", _parse_sms_number_row),
            ("Получать SMS от компании", _parse_sms_subscription_row),
            ("Тариф на следующий период", _parse_next_tariff_row),
            ("Текущий баланс", _parse_balance_row),
            ("Текущий тариф", _parse_current_tariff_row),
    ):
        if marker in title:
            handler(data, title, value_html)
            return True
    return False


def _parse_simple_summary_field(data: dict[str, Any], title: str, value: str) -> bool:
    """Parse simple key/value summary rows."""
    for marker, target_key in _SIMPLE_SUMMARY_FIELDS:
        if marker in title:
            data[target_key] = value
            return True
    return False


def _parse_sms_number_row(data: dict[str, Any], _title: str, value_html: str) -> None:
    """Parse the SMS phone row."""
    data["sms_number"] = _extract_sms_number(value_html)


def _parse_sms_subscription_row(data: dict[str, Any], _title: str, value_html: str) -> None:
    """Parse the SMS subscription row."""
    data["sms_subscription"] = _extract_selected_option(value_html)


def _parse_next_tariff_row(data: dict[str, Any], _title: str, value_html: str) -> None:
    """Parse the next tariff row."""
    data["next_tariff"] = _extract_selected_option(value_html)


def _parse_balance_row(data: dict[str, Any], title: str, value_html: str) -> None:
    """Parse the balance row."""
    _label, meta = _split_label_and_meta(title)
    balance_value, currency = _parse_money(_normalize_space(_strip_tags(value_html)))
    data["current_balance"] = balance_value
    data["balance_currency"] = currency or DEFAULT_CURRENCY
    if meta:
        data["balance_timestamp"] = meta.removeprefix("на ").strip()


def _parse_current_tariff_row(data: dict[str, Any], title: str, value_html: str) -> None:
    """Parse the current tariff row."""
    _label, meta = _split_label_and_meta(title)
    data["current_tariff"] = _normalize_space(_strip_tags(value_html))
    if meta:
        data["current_tariff_valid_until"] = meta.removeprefix("действует до ").strip()


def _parse_operations_table(table_html: str) -> list[InfoLanOperation]:
    """Parse the lower money report table."""
    operations: list[InfoLanOperation] = []
    for row_html in _ROW_RE.findall(table_html):
        if "task_NOT_FOUND" in row_html:
            continue

        row_class = _extract_row_class(row_html)
        cells = _CELL_RE.findall(row_html)
        if len(cells) < 3:
            continue

        date = _normalize_space(_strip_tags(cells[0]))
        if not _OPERATION_DATE_RE.fullmatch(date):
            continue

        amount_text = _normalize_space(_strip_tags(cells[1]))
        amount, currency = _parse_money(amount_text)
        operation_text = _normalize_space(_strip_tags(cells[2]))
        operation_dates = _OPERATION_DATE_RE.findall(operation_text)

        operations.append(
            InfoLanOperation(
                date=date,
                amount=amount,
                currency=currency or DEFAULT_CURRENCY,
                operation=operation_text,
                operation_type=_normalize_operation_type(row_class, amount),
                period_from=operation_dates[0] if len(operation_dates) >= 2 else None,
                period_to=operation_dates[1] if len(operation_dates) >= 2 else None,
            )
        )

    return operations


def _extract_title(cell_html: str) -> str:
    """Extract and normalize a row title."""
    return _normalize_space(_strip_tags(cell_html)).rstrip(":")


def _extract_sms_number(cell_html: str) -> str | None:
    """Build the SMS number from the editable input fields."""
    values = {
        match.group("name"): match.group("value")
        for match in _INPUT_VALUE_RE.finditer(cell_html)
    }
    parts = [values.get("code"), values.get("first"), values.get("second"), values.get("third")]
    if not all(parts):
        return None
    return f"+7 ({parts[0]}) {parts[1]}-{parts[2]}-{parts[3]}"


def _extract_selected_option(cell_html: str) -> str | None:
    """Return the selected option text from a select element."""
    match = _OPTION_SELECTED_RE.search(cell_html)
    if not match:
        return _normalize_space(_strip_tags(cell_html)) or None
    return _normalize_space(_strip_tags(match.group(1)))


def _extract_row_class(row_html: str) -> str:
    """Extract the row CSS class."""
    match = re.search(r'class="([^"]+)"', row_html, re.IGNORECASE)
    return match.group(1) if match else ""


def _split_label_and_meta(title: str) -> tuple[str, str | None]:
    """Split titles like 'Current tariff (valid until ...)'."""
    match = _DATE_IN_TITLE_RE.match(title)
    if not match:
        return title, None
    return match.group("label").strip(), match.group("meta").strip()


def _normalize_operation_type(row_class: str, amount: float | None) -> str:
    """Map an HTML row class to a stable operation type."""
    lowered = row_class.lower()
    operation_type = "neutral"
    if "tariff" in lowered:
        operation_type = "tariff"
    elif "service" in lowered:
        operation_type = "service"
    elif "add" in lowered:
        operation_type = "credit"
    elif amount is None:
        operation_type = "unknown"
    elif amount < 0:
        operation_type = "debit"
    elif amount > 0:
        operation_type = "credit"
    return operation_type


def _parse_money(value: str) -> tuple[float | None, str | None]:
    """Parse a Russian money string like '-750,00 руб.'."""
    match = _BALANCE_RE.search(value)
    if not match:
        return None, None

    normalized = match.group("value").replace(" ", "").replace(",", ".")
    try:
        amount = float(Decimal(normalized))
    except (InvalidOperation, ValueError):
        _LOGGER.debug("Failed to parse money value from %s", value)
        amount = None

    currency_raw = match.group("currency") or ""
    currency = currency_raw.rstrip(".").upper() if currency_raw else None
    if currency == "РУБ":
        currency = DEFAULT_CURRENCY
    return amount, currency


def _strip_tags(value: str) -> str:
    """Strip HTML tags and decode entities."""
    return unescape(_TAG_RE.sub(" ", value)).replace("\xa0", " ")


def _normalize_space(value: str) -> str:
    """Collapse whitespace."""
    return _SPACE_RE.sub(" ", value).strip()
