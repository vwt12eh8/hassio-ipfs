from asyncio import gather
from datetime import timedelta
from logging import getLogger
from typing import cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DATA_BYTES,
    DATA_GIBIBYTES,
    DATA_RATE_BYTES_PER_SECOND,
    DATA_RATE_KIBIBYTES_PER_SECOND,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DOMAIN
from .kubo_rpc import KuboRpc, SwarmPeers

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    kubo: KuboRpc = hass.data[entry.entry_id]
    bw = DataUpdateCoordinator[dict](
        hass,
        _LOGGER,
        name="stats/bw",
        update_interval=timedelta(seconds=5),
        update_method=kubo.stats_bw,
    )
    peers = DataUpdateCoordinator[SwarmPeers](
        hass,
        _LOGGER,
        name="swarm/peers",
        update_interval=timedelta(seconds=10),
        update_method=kubo.swarm_peers,
    )
    repo = DataUpdateCoordinator[dict](
        hass,
        _LOGGER,
        name="stats/repo",
        update_interval=timedelta(seconds=30),
        update_method=kubo.stats_repo,
    )
    await gather(
        bw.async_config_entry_first_refresh(),
        peers.async_config_entry_first_refresh(),
        repo.async_config_entry_first_refresh(),
    )
    device = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, cast(str, entry.unique_id))},
        name=entry.title,
    )
    async_add_entities(
        [
            RateEntity(bw, "RateIn", "Rate in", "mdi:download-network", device),
            RateEntity(bw, "RateOut", "Rate out", "mdi:upload-network", device),
            TotalEntity(bw, "TotalIn", "Total in", "mdi:download", device),
            TotalEntity(bw, "TotalOut", "Total out", "mdi:upload", device),
            PeersEntity(peers, device),
            RepoSizeEntity(repo, "RepoSize", "Repo size", None, device),
            NumObjectsEntity(repo, device),
        ]
    )


class DataEntity(CoordinatorEntity[DataUpdateCoordinator[dict]], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict],
        key: str,
        name: str,
        icon: str | None,
        device: DeviceInfo,
    ):
        super().__init__(coordinator)
        self._attr_device_info = device
        self._attr_icon = icon
        self._attr_name = name
        self._attr_unique_id = f"stats/bw/{key}"
        self._key = key

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data[self._key]


class PeersEntity(CoordinatorEntity[DataUpdateCoordinator[SwarmPeers]], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:cube-outline"
    _attr_name = "Peers"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_unique_id = "swarm/peers"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[SwarmPeers],
        device: DeviceInfo,
    ):
        super().__init__(coordinator)
        self._attr_device_info = device

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return len(self.coordinator.data["Peers"])


class NumObjectsEntity(CoordinatorEntity[DataUpdateCoordinator[dict]], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:cube-outline"
    _attr_name = "Objects"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_unique_id = "stats/repo/NumObjects"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict],
        device: DeviceInfo,
    ):
        super().__init__(coordinator)
        self._attr_device_info = device

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data["NumObjects"]


class RepoSizeEntity(DataEntity):
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = DATA_BYTES

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return None
        return {"storage_max": self.coordinator.data["StorageMax"]}


class RateEntity(DataEntity):
    _attr_device_class = SensorDeviceClass.DATA_RATE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = DATA_RATE_BYTES_PER_SECOND
    _attr_suggested_display_precision = 1
    _attr_suggested_unit_of_measurement = DATA_RATE_KIBIBYTES_PER_SECOND


class TotalEntity(DataEntity):
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = DATA_BYTES
    _attr_suggested_display_precision = 2
    _attr_suggested_unit_of_measurement = DATA_GIBIBYTES
