from typing import TypedDict, cast

from aiohttp import ClientSession


class Id(TypedDict):
    Address: list[str]
    AgentVersion: str
    ID: str
    ProtocolVersion: str
    Protocols: list[str]
    PublicKey: str


class LsEntry(TypedDict):
    Hash: str
    Name: str
    Size: int
    Type: int


class SwarmPeersEntry(TypedDict):
    Addr: str
    Peer: str
    Identify: dict


class Version(TypedDict):
    Commit: str
    Golang: str
    Repo: str
    System: str
    Version: str


class KuboRpc:
    def __init__(self, session: ClientSession, url: str):
        self._session = session
        self.url = url

    async def files_ls(
        self,
        arg: str | None,
        long: bool | None = None,
        U: bool | None = None,
    ):
        return cast(
            list[LsEntry],
            (await self._post("files/ls", arg=arg, long=long, U=U))["Entries"],
        )

    async def id(self, arg: str | None = None, format: str | None = None):
        return cast(Id, await self._post("id", arg=arg, format=format))

    async def stats_bw(self):
        return cast(dict, await self._post("stats/bw"))

    async def stats_repo(self, size_only: bool | None = None):
        return cast(dict, await self._post("stats/repo", **{"size-only": size_only}))

    async def swarm_peers(self):
        return cast(list[SwarmPeersEntry], (await self._post("swarm/peers"))["Peers"])

    async def version(
        self,
        number: bool | None = None,
        commit: bool | None = None,
        repo: bool | None = None,
        all: bool | None = None,
    ):
        return cast(
            Version,
            await self._post(
                "version", number=number, commit=commit, repo=repo, all=all
            ),
        )

    async def _post(self, ep: str, **kwargs):
        res = await self._session.post(f"{self.url}/api/v0/{ep}" + _to_query(**kwargs))
        if not res.ok:
            raise Exception(f"status: {res.status}")
        return await res.json()


def _to_query(**kwargs):
    args = [f"{x[0]}={x[1]}" for x in kwargs.items() if x[1] is not None]
    if not args:
        return ""
    return "?" + "&".join(args)
