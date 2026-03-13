"""Version: 0.0.1. Constants for the Info-Lan integration."""

DOMAIN = "info_lan_for_home_assistant"

CONF_LOGIN = "login"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL_HOURS = 12
MIN_SCAN_INTERVAL_HOURS = 1
MAX_SCAN_INTERVAL_HOURS = 24

INFO_LAN_URL = "https://stats.info-lan.ru/"
DEFAULT_CURRENCY = "RUB"
RECENT_OPERATIONS_LIMIT = 15
