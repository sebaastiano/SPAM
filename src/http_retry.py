"""
SPAM! — HTTP Retry Utilities
==============================
Shared retry logic for all server calls.

The game server frequently returns HTTP 429 (rate limit).
This module provides:
  - aiohttp_retry_get: async GET with exponential backoff
  - aiohttp_retry_request: generic async request with backoff
  - sync_retry_get: synchronous GET with backoff (for tracker)

All 429 responses are retried automatically with exponential backoff.
Other 5xx errors also trigger retries (server may be temporarily overloaded).
"""

import asyncio
import logging
import time

import aiohttp

logger = logging.getLogger("spam.http_retry")

# Retry defaults
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY = 1.0      # seconds
DEFAULT_MAX_DELAY = 16.0      # cap for backoff
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


async def aiohttp_retry_get(
    url: str,
    headers: dict,
    session: aiohttp.ClientSession | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    timeout: aiohttp.ClientTimeout | None = None,
    params: dict | None = None,
    label: str = "",
) -> aiohttp.ClientResponse | None:
    """
    Perform an async GET with exponential backoff on retryable errors.

    Returns the response object on success (status 200-399), or None
    if all retries are exhausted. The caller is responsible for reading
    the response body before the session/context closes.

    For 429 specifically: reads Retry-After header if present.
    """
    _label = label or url.split("?")[0].split("/")[-1]
    own_session = session is None

    for attempt in range(max_retries):
        sess = session
        try:
            if sess is None or sess.closed:
                sess = aiohttp.ClientSession()
            kwargs = {"headers": headers}
            if timeout:
                kwargs["timeout"] = timeout
            if params:
                kwargs["params"] = params

            async with sess.get(url, **kwargs) as resp:
                if resp.status < 400:
                    # Success — BUT we must read the body before returning
                    # because the context manager will close the response.
                    # We attach the parsed body to avoid double-read issues.
                    body = await resp.read()
                    # Return a simple result container
                    return _RetryResponse(
                        status=resp.status,
                        body=body,
                        headers=dict(resp.headers),
                        content_type=resp.content_type,
                    )

                if resp.status in RETRYABLE_STATUSES:
                    # Check Retry-After header (429 may include it)
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait = min(float(retry_after), max_delay)
                        except ValueError:
                            wait = min(base_delay * (2 ** attempt), max_delay)
                    else:
                        wait = min(base_delay * (2 ** attempt), max_delay)

                    logger.warning(
                        f"HTTP {resp.status} on {_label} "
                        f"(attempt {attempt + 1}/{max_retries}) "
                        f"— retrying in {wait:.1f}s"
                    )
                    await asyncio.sleep(wait)
                    continue

                # Non-retryable error (400, 401, 403, 404, etc.)
                body = await resp.read()
                return _RetryResponse(
                    status=resp.status,
                    body=body,
                    headers=dict(resp.headers),
                    content_type=resp.content_type,
                )

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            wait = min(base_delay * (2 ** attempt), max_delay)
            if attempt < max_retries - 1:
                logger.warning(
                    f"{_label} request error (attempt {attempt + 1}/{max_retries}): "
                    f"{e} — retrying in {wait:.1f}s"
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    f"{_label} request failed after {max_retries} attempts: {e}"
                )
        finally:
            if own_session and sess and not sess.closed:
                await sess.close()

    return None


class _RetryResponse:
    """Lightweight container for HTTP response data after retry logic."""

    def __init__(self, status: int, body: bytes, headers: dict, content_type: str):
        self.status = status
        self._body = body
        self.headers = headers
        self.content_type = content_type

    async def json(self):
        import json
        return json.loads(self._body)

    async def text(self):
        return self._body.decode("utf-8", errors="replace")

    async def read(self):
        return self._body


def sync_retry_get(
    url: str,
    headers: dict,
    params: dict | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    timeout: float = 10.0,
    label: str = "",
):
    """
    Synchronous GET with exponential backoff on retryable errors.

    Returns requests.Response on success, or None if all retries exhausted.
    For use in the tracker sidecar (synchronous code).
    """
    import requests

    _label = label or url.split("?")[0].split("/")[-1]

    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)

            if r.status_code < 400:
                return r

            if r.status_code in RETRYABLE_STATUSES:
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = min(float(retry_after), max_delay)
                    except ValueError:
                        wait = min(base_delay * (2 ** attempt), max_delay)
                else:
                    wait = min(base_delay * (2 ** attempt), max_delay)

                logger.warning(
                    f"HTTP {r.status_code} on {_label} "
                    f"(attempt {attempt + 1}/{max_retries}) "
                    f"— retrying in {wait:.1f}s"
                )
                time.sleep(wait)
                continue

            # Non-retryable — return as-is for caller to handle
            return r

        except Exception as e:
            wait = min(base_delay * (2 ** attempt), max_delay)
            if attempt < max_retries - 1:
                logger.warning(
                    f"{_label} request error (attempt {attempt + 1}/{max_retries}): "
                    f"{e} — retrying in {wait:.1f}s"
                )
                time.sleep(wait)
            else:
                logger.error(
                    f"{_label} request failed after {max_retries} attempts: {e}"
                )

    return None
