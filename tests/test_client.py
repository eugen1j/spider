from typing import Optional

import pytest
from aiohttp import ClientResponse

from aioscrapy import SingleSessionPool

from aioscrapy.cache import MemoryCache
from aioscrapy.client import Client, FakeClient, CacheClient, RetryClient, CacheOnlyClient, CacheSkipClient, WebClient, \
    WebTextClient, WebByteClient, ImageClient, FetchError, WebFetchError


class ForRetryClient(Client[str, str]):
    def __init__(self, try_count: int):
        self._try_count = try_count
        self._tries = dict()

    async def fetch(self, key: str) -> str:
        if key not in self._tries:
            self._tries[key] = 0
        self._tries[key] += 1

        if self._tries[key] == self._try_count:
            return key
        raise FetchError()


@pytest.mark.asyncio
async def test_fake_client():
    client = FakeClient()
    key = 'key'
    assert await client.fetch(key) == key


@pytest.mark.asyncio
async def test_cache_client():
    client = CacheClient(
        FakeClient(),
        MemoryCache()
    )

    key = 'key'
    assert await client.fetch(key) == key
    assert await client.fetch(key) == key


@pytest.mark.asyncio
async def test_cache_only_client():
    cache = MemoryCache()
    fake_client = FakeClient()
    key = 'key'
    client = CacheOnlyClient(
        FakeClient(),
        cache
    )

    with pytest.raises(FetchError):
        await client.fetch(key)
    cache.set(key, await fake_client.fetch(key))
    assert await client.fetch(key) == key


@pytest.mark.asyncio
async def test_cache_skip_client():
    client = CacheSkipClient(
        FakeClient(),
        MemoryCache()
    )

    key = 'key'
    assert await client.fetch(key) == key
    with pytest.raises(FetchError):
        await client.fetch(key)


@pytest.mark.asyncio
async def test_for_retry_client():
    client = ForRetryClient(3)
    key = 'key'
    with pytest.raises(FetchError):
        await client.fetch(key)
    with pytest.raises(FetchError):
        await client.fetch(key)

    assert await client.fetch(key) is key


@pytest.mark.asyncio
async def test_retry_client_not_enough_tries():
    client = RetryClient(
        ForRetryClient(4),
        3
    )
    key = 'key'
    with pytest.raises(FetchError):
        await client.fetch(key)


@pytest.mark.asyncio
async def test_retry_client_enough_tries():
    client = RetryClient(
        ForRetryClient(4),
        4
    )
    key = 'key'
    assert await client.fetch(key) is key


@pytest.mark.asyncio
async def test_web_client_fetch_google():
    client = WebClient(SingleSessionPool())
    response = await client.fetch('https://google.com')
    assert isinstance(response, ClientResponse)


@pytest.mark.asyncio
async def test_web_text_client_fetch_google():
    client = WebTextClient(SingleSessionPool())
    response = await client.fetch('https://google.com')
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_web_byte_client_fetch_google():
    client = WebByteClient(SingleSessionPool())
    response = await client.fetch('https://google.com')
    assert isinstance(response, bytes)


@pytest.mark.asyncio
async def test_image_client_fetch_google():
    client = ImageClient(SingleSessionPool())
    with pytest.raises(WebFetchError):
        assert await client.fetch('https://google.com') is None
    assert isinstance(await client.fetch('https://google.com/favicon.ico'), bytes)
