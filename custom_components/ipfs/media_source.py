from re import match

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import CONF_GATEWAY, DOMAIN
from .kubo_rpc import KuboRpc, LsEntry


async def async_get_media_source(hass: HomeAssistant):
    return MyMediaSource(DOMAIN)


class MyMediaSource(MediaSource):
    name = "IPFS MFS"

    async def async_resolve_media(self, item: MediaSourceItem):
        if "/" not in item.identifier:
            raise BrowseError()
        path = item.identifier.split("/", 1)
        if len(path) < 2:
            raise BrowseError()
        entry = _get_entry(item.hass, path[0])
        kubo = _get_kubo(item.hass, entry)
        file = (await kubo.files_ls(arg=f"/{'/'.join(path[1:])}", long=True))[0]
        url = (
            f"{entry.options[CONF_GATEWAY]}/ipfs/{file['Hash']}?filename={file['Name']}"
        )
        async with await async_get_clientsession(item.hass).get(url) as res:
            mime = res.content_type
        return PlayMedia(url, mime)

    async def async_browse_media(self, item: MediaSourceItem):
        if item.identifier:
            path = item.identifier.split("/")
            kubo = _get_kubo(item.hass, _get_entry(item.hass, path[0]))
            files = await kubo.files_ls(arg=f"/{'/'.join(path[1:])}", long=True)
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=item.identifier,
                children=[_to_media(item.identifier, x) for x in files],
                media_class=MediaClass.DIRECTORY,
                media_content_type="",
                title=item.identifier.split("/")[-1],
                can_play=False,
                can_expand=True,
            )
        else:
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=None,
                children=[
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=x.unique_id,
                        media_class=MediaClass.DIRECTORY,
                        media_content_type="",
                        title=x.title,
                        can_play=False,
                        can_expand=True,
                    )
                    for x in item.hass.config_entries.async_entries(DOMAIN)
                ],
                media_class=MediaClass.DIRECTORY,
                media_content_type="",
                title=self.name,
                can_play=False,
                can_expand=True,
            )


def _get_entry(hass: HomeAssistant, id: str):
    return next(
        x for x in hass.config_entries.async_entries(DOMAIN) if x.unique_id == id
    )


def _get_kubo(hass: HomeAssistant, entry: ConfigEntry):
    kubo = hass.data.get(entry.entry_id)
    if not isinstance(kubo, KuboRpc):
        raise BrowseError()
    return kubo


def _to_media(basepath: str, x: LsEntry):
    res = BrowseMediaSource(
        domain=DOMAIN,
        identifier=f'{basepath}/{x["Name"]}',
        media_class=MediaClass.URL,
        media_content_type="",
        title=x["Name"],
        can_play=False,
        can_expand=False,
    )
    if x["Type"] == 1:
        res.can_expand = True
        res.media_class = MediaClass.DIRECTORY
    elif match(r".*\.(gif|jpe?g|png|svg)$", x["Name"]):
        res.can_play = True
        res.media_class = MediaClass.IMAGE
        res.media_content_type = MediaType.IMAGE
    elif match(r".*\.(avi|mp4|wmv)$", x["Name"]):
        res.can_play = True
        res.media_class = MediaClass.MOVIE
        res.media_content_type = MediaType.MOVIE
    elif match(r".*\.(flac|mp3|m4a|ogg|wav|wma)$", x["Name"]):
        res.can_play = True
        res.media_class = MediaClass.MUSIC
        res.media_content_type = MediaType.MUSIC

    return res
