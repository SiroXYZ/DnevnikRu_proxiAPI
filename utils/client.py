"""Dnevnik API HTTP client with token-owner storage and ban checks."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from config import DNEVNIK_BASE_URL
from utils.access_store import (
    ensure_storage,
    extract_owner_id,
    get_owner_id_by_token,
    is_owner_banned,
    register_token_owner,
    touch_token,
)

# ================= CONFIG =================
MAX_CONCURRENT = 10
GLOBAL_BURST_LIMIT = 100
GLOBAL_BURST_SLEEP = 1.5
RETRIES = 5
DELAY = 0.3

ensure_storage()


class GlobalBurstLimiter:
    def __init__(self, limit: int, sleep_time: float):
        self.limit = limit
        self.sleep_time = sleep_time
        self.count = 0
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            self.count += 1

            if self.count >= self.limit:
                print(f"[RATE] GLOBAL burst {self.limit} -> sleep {self.sleep_time}s")
                await asyncio.sleep(self.sleep_time)
                self.count = 0


GLOBAL_LIMITER = GlobalBurstLimiter(GLOBAL_BURST_LIMIT, GLOBAL_BURST_SLEEP)


class DnevnikAPIClient:
    def __init__(self, token: str):
        self.access_token = token
        self.base_url = DNEVNIK_BASE_URL.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.proxy = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        self.owner_id: Optional[str] = None
        self._identity_ready = False

    def _get_headers(self):
        return {
            "Access-Token": self.access_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _fetch_context_data(self) -> Dict[str, Any]:
        if not self.session:
            raise RuntimeError("Use 'async with'")

        url = f"{self.base_url}/users/me/context"
        async with self.session.request(
            "GET",
            url,
            proxy=self.proxy,
            ssl=False,
        ) as response:
            text = await response.text()
            response.raise_for_status()
            return json.loads(text)

    async def _resolve_owner_identity(self) -> str:
        """Resolve owner_id only once per token and cache it in SQLite."""
        if self._identity_ready and self.owner_id:
            return self.owner_id

        cached_owner_id = get_owner_id_by_token(self.access_token)
        if cached_owner_id:
            self.owner_id = cached_owner_id
            self._identity_ready = True
            if is_owner_banned(cached_owner_id):
                raise PermissionError("Token owner is BANNED")
            return cached_owner_id

        if not self.session:
            raise RuntimeError("Use 'async with'")

        context_data = await self._fetch_context_data()
        owner_id = extract_owner_id(context_data)
        if not owner_id:
            raise ValueError("Unable to resolve owner id from context")

        register_token_owner(self.access_token, owner_id)
        self.owner_id = owner_id
        self._identity_ready = True

        if is_owner_banned(owner_id):
            raise PermissionError("Token owner is BANNED")

        return owner_id

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self._get_headers(),
            connector=aiohttp.TCPConnector(limit=0, ssl=False),
        )
        await self._resolve_owner_identity()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs):
        if not self.session:
            raise RuntimeError("Use 'async with'")

        owner_id = await self._resolve_owner_identity()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with self.semaphore:
            await GLOBAL_LIMITER.acquire()

            last_error: Optional[Exception] = None

            for attempt in range(1, RETRIES + 1):
                try:
                    async with self.session.request(
                        method,
                        url,
                        proxy=self.proxy,
                        ssl=False,
                        **kwargs,
                    ) as response:
                        text = await response.text()

                        if response.status in (429, 433):
                            last_error = RuntimeError(
                                f"Rate limited with status {response.status}"
                            )
                            await asyncio.sleep(DELAY * attempt)
                            continue

                        response.raise_for_status()
                        parsed = json.loads(text)

                        touch_token(self.access_token, owner_id)
                        return parsed

                except Exception as exc:
                    last_error = exc
                    if attempt == RETRIES:
                        raise
                    await asyncio.sleep(DELAY)

            if last_error is not None:
                raise last_error
            raise RuntimeError("Request failed without a captured error")

    async def get(self, endpoint: str, params=None):
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data=None):
        return await self._request("POST", endpoint, json=data)

    async def get_all(self, endpoints: List[str]):
        tasks = [asyncio.create_task(self.get(ep)) for ep in endpoints]
        return await asyncio.gather(*tasks)

    async def post_all(self, requests: List[Tuple[str, Dict]]):
        tasks = [asyncio.create_task(self.post(ep, data)) for ep, data in requests]
        return await asyncio.gather(*tasks)
