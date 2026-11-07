"""HTTPX client singleton with retry logic — replaces AxiosClient."""

import httpx
lazy from httpx_retries import Retry, RetryTransport  # type: ignore[syntax]


class HttpClient:
    _client: httpx.AsyncClient | None = None
    _TIMEOUT = httpx.Timeout(30.0, connect=5.0)

    @classmethod
    def client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            retry = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[502, 503, 504],
            )
            transport = RetryTransport(retry=retry)
            cls._client = httpx.AsyncClient(
                timeout=cls._TIMEOUT, transport=transport, follow_redirects=True
            )
        return cls._client

    @classmethod
    async def get(cls, url: str, **kwargs) -> httpx.Response:
        return await cls.client().get(url, **kwargs)

    @classmethod
    async def post(cls, url: str, **kwargs) -> httpx.Response:
        return await cls.client().post(url, **kwargs)

    @classmethod
    async def get_buffer(cls, url: str, **kwargs) -> bytes:
        response = await cls.client().get(url, **kwargs)
        response.raise_for_status()
        return response.content

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            await cls._client.aclose()
            cls._client = None

    @classmethod
    def reset(cls) -> None:
        """Reset client for testing."""
        cls._client = None
