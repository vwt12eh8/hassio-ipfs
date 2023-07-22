from typing import Any, cast

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_URL, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from voluptuous import Optional, Required, Schema

from . import CONF_GATEWAY, DOMAIN
from .kubo_rpc import KuboRpc


class MyConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input:
            url = cast(str, user_input[CONF_URL]).rstrip("/")
            session = async_get_clientsession(self.hass, user_input[CONF_VERIFY_SSL])
            client = KuboRpc(session, url)
            id = await client.id()
            entry = await self.async_set_unique_id(id["ID"])

            gateway = user_input.get(CONF_GATEWAY)
            if not gateway and entry:
                gateway = entry.options[CONF_GATEWAY]
            if not gateway:
                gateway = "https://ipfs.io"
            gateway = gateway.rstrip("/")

            return self.async_create_entry(
                title=id["ID"][-8:],
                data={
                    CONF_URL: url,
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                },
                options={
                    CONF_GATEWAY: gateway,
                },
            )

        if not user_input:
            user_input = {
                CONF_URL: "",
                CONF_VERIFY_SSL: True,
                CONF_GATEWAY: "",
            }
        return self.async_show_form(
            step_id="user",
            data_schema=Schema(
                {
                    Required(CONF_URL, default=user_input[CONF_URL]): str,
                    Required(
                        CONF_VERIFY_SSL, default=user_input[CONF_VERIFY_SSL]
                    ): bool,
                    Optional(CONF_GATEWAY, default=user_input[CONF_GATEWAY]): str,
                }
            ),
            last_step=True,
        )

    @staticmethod
    def async_get_options_flow(entry: ConfigEntry):
        return MyOptionsFlow(entry)


class MyOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input:
            return self.async_create_entry(
                data={
                    CONF_GATEWAY: user_input[CONF_GATEWAY],
                },
            )
        else:
            return self.async_show_form(
                step_id="init",
                data_schema=Schema(
                    {
                        Required(
                            CONF_GATEWAY, default=self.entry.options[CONF_GATEWAY]
                        ): str,
                    }
                ),
                last_step=True,
            )
