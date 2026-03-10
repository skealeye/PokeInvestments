"""Base HTTP client with retry logic."""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.settings import HTTP_TIMEOUT, HTTP_MAX_RETRIES


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError))


def create_retry_decorator():
    return retry(
        retry=retry_if_exception_type((
            httpx.TimeoutException, httpx.ConnectError,
            httpx.RemoteProtocolError, httpx.HTTPStatusError
        )),
        stop=stop_after_attempt(HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )


class BaseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": "PokemonInvestments/1.0 (personal price tracker)",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )

    @create_retry_decorator()
    def get(self, path: str, **kwargs) -> dict:
        resp = self._client.get(path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
