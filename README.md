# Info-Lan Integration for Home Assistant

![GitHub Release](https://img.shields.io/github/v/release/OddanN/info_lan_for_home_assistant?style=flat-square)
![GitHub Activity](https://img.shields.io/github/commit-activity/m/OddanN/info_lan_for_home_assistant?style=flat-square)
![License](https://img.shields.io/github/license/OddanN/info_lan_for_home_assistant?style=flat-square)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

<!--suppress HtmlDeprecatedAttribute -->
<p align="center">
  <!--suppress CheckImageSize -->
  <img src="https://raw.githubusercontent.com/OddanN/info_lan_for_home_assistant/main/custom_components/info_lan_for_home_assistant/brand/logo.png" alt="Info-Lan logo" width="200">
</p>

Интеграция Info-Lan получает данные из личного кабинета [Info-Lan](https://info-lan.ru/) и создаёт сущности Home
Assistant с основными данными по договору, тарифу, балансу и операциям по счёту.

## Установка

Проще всего установить интеграцию через [Home Assistant Community Store (HACS)](https://hacs.xyz/). После настройки HACS
нажмите кнопку ниже
(требуется настроенный My Home Assistant)
или [добавьте репозиторий вручную как custom repository](https://hacs.xyz/docs/faq/custom_repositories),
после чего интеграция станет доступна для установки как обычная HACS-интеграция.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=OddanN&repository=info_lan_for_home_assistant&category=integration)

## Настройка

После установки настройте интеграцию через интерфейс Home Assistant. YAML-конфигурация не требуется.
Перейдите в `Настройки` → `Устройства и службы`, нажмите `Добавить интеграцию`
или воспользуйтесь кнопкой ниже.

[![Add Integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg?style=flat-square)](https://my.home-assistant.io/redirect/config_flow_start/?domain=info_lan_for_home_assistant)

### Подключение

- Введите логин и пароль от личного кабинета Info-Lan.
- Завершите настройку. Интеграция выполнит авторизацию и создаст сущности аккаунта.

### Параметры интеграции

- `Интервал обновления`: период опроса в часах. По умолчанию `12`, минимум `1`, максимум `24`.

## Entities

На каждую пару логин/пароль интеграция создаёт одно устройство личного кабинета.
Каждое устройство содержит следующие **основные** сущности:

- `Баланс денег`: денежный баланс лицевого счёта в `₽`.
  Атрибуты включают `top up your balance`, `Total number of operations`, `Operation 1 ... Operation 10`,
  а также служебные поля баланса `balance_timestamp`, `promised_payment_limit`, `block_threshold` и `currency`.
- `Текущий тариф`: краткое название текущего тарифа.
  Атрибуты включают `full_name`, `valid_until`, `next_tariff` и `next_tariff_full_name`.
- `Изменение тарифа`: показывает `Запланировано` или `Не запланировано`.
  Атрибуты включают данные о текущем и следующем тарифе.
- `Обновить`: кнопка принудительного обновления данных.
- `Интервал обновления`: number-сущность для настройки периода опроса.

Устройство также содержит **диагностические** сущности:

- `Номер счета`
- `Контрагент`
  Атрибуты: `sms_number`, `sms_subscription`
- `Адрес договора`
- `Статус доступа в Интернет`
- `Последнее обновление`

По умолчанию часть диагностических сущностей может быть отключена в entity registry.

## Примечания

- Интеграция работает через сайт `https://stats.info-lan.ru/` и парсит HTML-страницу личного кабинета.
- Для авторизации используются те же логин и пароль, что и в личном кабинете Info-Lan.
- Если вы нашли ошибку или хотите предложить улучшение, создайте issue в
  [GitHub repository](https://github.com/OddanN/info_lan_for_home_assistant/issues).

## Debug

Для включения DEBUG-логов добавьте в `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.info_lan_for_home_assistant: debug
```

## License

Проект распространяется по лицензии MIT. Подробности в файле [LICENSE](LICENSE).
