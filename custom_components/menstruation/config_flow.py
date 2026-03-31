from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.core import callback

from .const import CONF_NAME, CONF_PERSON, DEFAULT_NAME, DOMAIN


class MenstruationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input: dict | None = None):
        if user_input is not None:
            person_entity_id = user_input[CONF_PERSON]
            await self.async_set_unique_id(person_entity_id)
            self._abort_if_unique_id_configured()

            person_state = self.hass.states.get(person_entity_id)
            person_name = (
                person_state.name
                if person_state is not None and person_state.name
                else person_entity_id
            )
            name = user_input.get(CONF_NAME) or f"{person_name} {DEFAULT_NAME}"
            return self.async_create_entry(
                title=name,
                data={CONF_NAME: name, CONF_PERSON: person_entity_id},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_PERSON): selector.selector(
                    {"entity": {"domain": "person"}}
                ),
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return MenstruationOptionsFlow(config_entry)


class MenstruationOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({vol.Required(CONF_NAME, default=self._entry.title): str})
        return self.async_show_form(step_id="init", data_schema=schema)
