# Info-Lan Integration for Home Assistant

![GitHub Release](https://img.shields.io/github/v/release/OddanN/info_lan_for_home_assistant?style=flat-square)
![GitHub Activity](https://img.shields.io/github/commit-activity/m/OddanN/info_lan_for_home_assistant?style=flat-square)
![GitHub Downloads](https://img.shields.io/github/downloads/OddanN/info_lan_for_home_assistant/total?style=flat-square)
![License](https://img.shields.io/github/license/OddanN/info_lan_for_home_assistant?style=flat-square)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

<p align="center">
  <img src="logo.png" alt="Info-Lan logo" width="200">
</p>

The Info-Lan Integration allows you to connect your Home Assistant instance to the [Info-Lan](https://info-lan.ru/)
personal account page and expose the main contract, tariff, balance, and payment history data as Home Assistant
entities.

## Installation

Installation is easiest via the [Home Assistant Community Store
(HACS)](https://hacs.xyz/), which is the best place to get third-party integrations for Home Assistant. Once you have
HACS set up, simply click the button below (requires My Home Assistant configured) or follow the
[instructions for adding a custom repository](https://hacs.xyz/docs/faq/custom_repositories) and then the integration
will be available to install like any other.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=OddanN&repository=info_lan_for_home_assistant&category=integration)

## Configuration

After installing, you can configure the integration using the Integrations UI. No manual YAML configuration is
required. Go to Settings / Devices & Services and press the Add Integration button, or click the shortcut button below
(requires My Home Assistant configured).

[![Add Integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg?style=flat-square)](https://my.home-assistant.io/redirect/config_flow_start/?domain=info_lan_for_home_assistant)

### Setup Wizard

- **Login**: Your Info-Lan account login.
- **Password**: Your Info-Lan account password.

### Integration Options

- **Update Interval**: Polling interval in hours. Default is 12 hours, minimum is 1 hour, maximum is 24 hours.

## Usage

### Entities

Once configured, the integration creates one device for the Info-Lan contract and the following entities:

- `sensor.info_lan_<suffix>_contract_number`: Contract number.
- `sensor.info_lan_<suffix>_internet_status`: Internet access status.
- `sensor.info_lan_<suffix>_connection_address`: Connection address.
- `sensor.info_lan_<suffix>_contract_owner`: Contract owner.
- `sensor.info_lan_<suffix>_sms_number`: SMS phone number.
- `sensor.info_lan_<suffix>_sms_subscription`: Selected company SMS subscription mode.
- `sensor.info_lan_<suffix>_current_tariff`: Current tariff. Includes the tariff validity date in attributes.
- `sensor.info_lan_<suffix>_next_tariff`: Tariff selected for the next period.
- `sensor.info_lan_<suffix>_current_balance`: Current balance as a monetary sensor. Includes balance timestamp,
  promised payment limit, and block threshold in attributes.
- `sensor.info_lan_<suffix>_operations`: Total number of parsed operations. Includes recent operations, first
  operation, and latest operation in attributes.

### Notes About Operations

Info-Lan returns the entire payment history table in one HTML page. To keep entity state compact, the integration stores
the total operation count in the sensor state and only keeps the recent operations in attributes instead of the full
history.

## Notes

- The integration uses the Info-Lan website at `https://stats.info-lan.ru/` and parses the returned HTML page.
- The current implementation exposes sensor entities only.
- For support or to report issues, please open an issue on the
  [GitHub repository](https://github.com/OddanN/info_lan_for_home_assistant/issues).

## Debug

For DEBUG add to `configuration.yaml`

```yaml
logger:
  default: info
  logs:
    custom_components.info_lan_for_home_assistant: debug
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
