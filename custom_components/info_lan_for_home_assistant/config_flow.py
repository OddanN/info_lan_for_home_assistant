"""Version: 0.0.1. Config flow for the Info-Lan integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD

from .api import (
    InfoLanApiClient,
    InfoLanAuthError,
    InfoLanConnectionError,
    InfoLanError,
)
from .const import CONF_LOGIN, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN
from .options_flow import InfoLanOptionsFlow


# noinspection PyTypeChecker
class InfoLanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Info-Lan."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            login = user_input[CONF_LOGIN].strip()
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(login.lower())
            self._abort_if_unique_id_configured()

            client = InfoLanApiClient(
                hass=self.hass,
                login=login,
                password=password,
            )
            try:
                data = await client.async_fetch_data()
            except InfoLanAuthError:
                errors["base"] = "invalid_auth"
            except InfoLanConnectionError:
                errors["base"] = "cannot_connect"
            except InfoLanError:
                errors["base"] = "unknown"
            else:
                title = data.get("contract_number") or login
                owner = data.get("contract_owner")
                if owner:
                    title = f"{title} ({owner})"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_LOGIN: login,
                        CONF_PASSWORD: password,
                    },
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL_HOURS},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOGIN): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> InfoLanOptionsFlow:
        """Get the options flow for this handler."""
        return InfoLanOptionsFlow(config_entry)
