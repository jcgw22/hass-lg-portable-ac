"""Config flow for LG Portable AC integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

from .const import CONF_REMOTE_ENTITY_ID, DOMAIN


class LGPortableACConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LG Portable AC."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the user step -- select a Broadlink remote entity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_REMOTE_ENTITY_ID]
            await self.async_set_unique_id(f"lg_pac_{entity_id}")
            self._abort_if_unique_id_configured()
            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(entity_id)
            entity_name = (
                entry.name or entry.original_name or entity_id
                if entry
                else entity_id
            )
            return self.async_create_entry(
                title=f"LG Portable AC ({entity_name})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REMOTE_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(domain=REMOTE_DOMAIN)
                    ),
                }
            ),
            errors=errors,
        )
