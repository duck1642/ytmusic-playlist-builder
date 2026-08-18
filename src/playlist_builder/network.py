from __future__ import annotations

import ssl

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager, ProxyManager


class TLS12Adapter(HTTPAdapter):
    """Requests adapter for environments where YouTube TLS 1.3 is unstable."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        super().__init__(*args, **kwargs)

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = False,
        **pool_kwargs: object,
    ) -> None:
        pool_kwargs["ssl_context"] = self.ssl_context
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: object) -> ProxyManager:
        proxy_kwargs["ssl_context"] = self.ssl_context
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def create_requests_session() -> requests.Session:
    session = requests.Session()
    session.mount("https://", TLS12Adapter())
    return session
