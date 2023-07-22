from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType

from .kubo_rpc import KuboRpc

CONF_GATEWAY = "gateway"
DOMAIN = "ipfs"

_PLATFORMS = {
    Platform.SENSOR,
}


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
