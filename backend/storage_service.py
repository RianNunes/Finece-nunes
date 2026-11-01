"""Private object storage client. Object keys never reach the browser."""
import asyncio
import logging
import os

import httpx
from fastapi import HTTPException

logger = logging.getLogger("finance.storage")


class ObjectStorage:
    def __init__(self):
        self.key = None
        self.lock = asyncio.Lock()
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15))

    @property
    def url(self):
        return os.environ["INTEGRATION_PROXY_URL"].rstrip("/") + "/objstore/api/v1/storage"

    async def initialize(self, force=False):
        async with self.lock:
            if self.key and not force:
                return self.key
            try:
                response = await self.client.post(
                    f"{self.url}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30
                )
                response.raise_for_status()
                self.key = response.json()["storage_key"]
            except (httpx.HTTPError, KeyError, ValueError):
                logger.warning("Object storage initialization unavailable")
                raise HTTPException(503, "Armazenamento indisponível no momento. Tente novamente em instantes.")
            return self.key

    async def request(self, method, path, **kwargs):
        key = await self.initialize()
        headers = kwargs.pop("headers", {})
        for attempt in range(2):
            try:
                response = await self.client.request(
                    method, f"{self.url}/objects/{path}", headers={"X-Storage-Key": key, **headers}, **kwargs
                )
            except httpx.HTTPError:
                raise HTTPException(503, "Não foi possível conectar ao armazenamento. Tente novamente.")
            if response.status_code == 404 and attempt == 0:
                key = await self.initialize(force=True)
                continue
            if response.status_code == 503 and attempt == 0:
                await asyncio.sleep(0.5)
                continue
            if response.is_success:
                return response
            logger.warning("Object storage operation returned status %s", response.status_code)
            if response.status_code == 439:
                raise HTTPException(507, "O limite de armazenamento foi atingido. Novos envios estão indisponíveis.")
            if response.status_code == 404:
                raise HTTPException(404, "O conteúdo deste arquivo não está disponível.")
            if response.status_code in (402, 403):
                raise HTTPException(503, "O armazenamento está temporariamente indisponível para esta conta.")
            raise HTTPException(503, "Não foi possível concluir a operação no armazenamento. Tente novamente.")

    async def put(self, path, data, content_type):
        response = await self.request("PUT", path, content=data, headers={"Content-Type": content_type})
        return response.json()

    async def get(self, path):
        response = await self.request("GET", path)
        return response.content

    async def close(self):
        await self.client.aclose()


storage = ObjectStorage()