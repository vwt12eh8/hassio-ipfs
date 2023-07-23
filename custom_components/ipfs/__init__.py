from typing import cast

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType

from .kubo_rpc import KuboRpc

CONF_GATEWAY = "gateway"
DOMAIN = "ipfs"

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)

_PLATFORMS = {
    Platform.SENSOR,
}


async def async_setup(hass: HomeAssistant, config):
    def get_kubo(service: str):
        dr = device_registry.async_get(hass)
        entries = hass.config_entries.async_entries(DOMAIN)
        device = dr.async_get(service)
        if not device:
            raise ValueError()
        id = next((x[1] for x in device.identifiers if x[0] == DOMAIN), None)
        if not id:
            raise ValueError()
        return next(
            cast(KuboRpc, hass.data[x.entry_id]) for x in entries if x.unique_id == id
        )

    async def _service_pin_add(call: ServiceCall):
        kubo = get_kubo(call.data[ATTR_DEVICE_ID])
        return await kubo.pin_add(call.data["arg"], call.data.get("recursive", None))

    hass.services.async_register(
        DOMAIN, "pin_add", _service_pin_add, supports_response=SupportsResponse.OPTIONAL
    )

    async def _service_pin_rm(call: ServiceCall):
        kubo = get_kubo(call.data[ATTR_DEVICE_ID])
        return await kubo.pin_rm(call.data["arg"], call.data.get("recursive", None))

    hass.services.async_register(
        DOMAIN, "pin_rm", _service_pin_rm, supports_response=SupportsResponse.OPTIONAL
    )

    async def _service_name_publish(call: ServiceCall):
        kubo = get_kubo(call.data[ATTR_DEVICE_ID])
        return await kubo.name_publish(
            call.data["arg"],
            call.data.get("resolve", None),
            call.data.get("lifetime", None),
            call.data.get("allow_offline", None),
            call.data.get("ttl", None),
            call.data.get("key", None),
            call.data.get("quieter", None),
            call.data.get("ipns_base", None),
        )

    hass.services.async_register(
        DOMAIN,
        "name_publish",
        _service_name_publish,
        supports_response=SupportsResponse.OPTIONAL,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    assert type(entry.unique_id) is str
    try:
        session = async_get_clientsession(hass, entry.data[CONF_VERIFY_SSL])
        hass.data[entry.entry_id] = kubo = KuboRpc(session, entry.data[CONF_URL])
        id = await kubo.id()
    except Exception as ex:
        raise ConfigEntryNotReady() from ex

    dr = device_registry.async_get(hass)
    dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        configuration_url=f"{entry.options[CONF_GATEWAY]}/ipns/webui.ipfs.io/",
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        sw_version=id["AgentVersion"].rstrip("/"),
    )

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False
    del hass.data[entry.entry_id]
    return True
