# AI-generated: Claude Code (claude.ai/code) — OpenEMR REST API client with OAuth2
import asyncio
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_token_cache: dict[str, str | float] = {}

# Token expiry buffer: refresh 60s before actual expiry
_TOKEN_EXPIRY_BUFFER = 60
# Default token lifetime if server doesn't specify (30 min)
_DEFAULT_TOKEN_LIFETIME = 1800

MAX_RETRIES = 3
RETRY_BACKOFF = [0.5, 1.0, 2.0]


class OpenEMRApiError(Exception):
    """Raised when OpenEMR API returns an unrecoverable error."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"OpenEMR API error {status_code}: {detail}")


def _token_expired() -> bool:
    """Check if the cached token is expired or about to expire."""
    expires_at = _token_cache.get("expires_at")
    if expires_at is None:
        return True
    return time.time() >= expires_at


async def _get_access_token(force_refresh: bool = False) -> str:
    """Get or refresh an OAuth2 access token from OpenEMR."""
    if not force_refresh and "access_token" in _token_cache and not _token_expired():
        return _token_cache["access_token"]

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                resp = await client.post(
                    f"{settings.openemr_base_url}/oauth2/default/token",
                    data={
                        "grant_type": "password",
                        "client_id": settings.openemr_client_id,
                        "client_secret": settings.openemr_client_secret,
                        "username": settings.openemr_username,
                        "password": settings.openemr_password,
                        "user_role": "users",
                        "scope": (
                            "openid api:oemr api:fhir "
                            "user/patient.read user/patient.write "
                            "user/allergy.read "
                            "user/appointment.read "
                            "user/medication.read "
                            "user/medical_problem.read "
                            "user/vital.read"
                        ),
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                _token_cache["access_token"] = data["access_token"]
                expires_in = data.get("expires_in", _DEFAULT_TOKEN_LIFETIME)
                _token_cache["expires_at"] = time.time() + expires_in - _TOKEN_EXPIRY_BUFFER
                return data["access_token"]
        except httpx.TimeoutException:
            logger.warning("Token request timed out (attempt %d/%d)", attempt + 1, MAX_RETRIES)
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                logger.warning("Token server error %d (attempt %d/%d)", e.response.status_code, attempt + 1, MAX_RETRIES)
            else:
                raise OpenEMRApiError(e.response.status_code, f"Token request failed: {e.response.text[:200]}")
        except httpx.ConnectError as e:
            logger.warning("Connection failed to OpenEMR (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_BACKOFF[attempt])

    raise OpenEMRApiError(503, "Failed to obtain access token after retries")


async def openemr_api(
    method: str, path: str, params: dict | None = None, json: dict | None = None
) -> dict | list | None:
    """Make an authenticated request to the OpenEMR REST API.

    Includes automatic token refresh, retry with backoff for transient errors,
    and structured error reporting.
    """
    url = f"{settings.openemr_base_url}/apis/default{path}"

    for attempt in range(MAX_RETRIES):
        token = await _get_access_token()
        try:
            async with httpx.AsyncClient(timeout=20, verify=False) as client:
                resp = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers={"Authorization": f"Bearer {token}"},
                )

                if resp.status_code == 401:
                    # Token expired or revoked — force refresh and retry
                    logger.info("Got 401, refreshing token (attempt %d/%d)", attempt + 1, MAX_RETRIES)
                    _token_cache.clear()
                    if attempt < MAX_RETRIES - 1:
                        continue
                    raise OpenEMRApiError(401, "Authentication failed after token refresh")

                if resp.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "OpenEMR server error %d on %s %s (attempt %d/%d)",
                        resp.status_code, method, path, attempt + 1, MAX_RETRIES,
                    )
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
                    continue

                if resp.status_code == 404:
                    return None

                if resp.status_code >= 400:
                    raise OpenEMRApiError(resp.status_code, resp.text[:200])

                return resp.json()

        except httpx.TimeoutException:
            logger.warning("Request timed out: %s %s (attempt %d/%d)", method, path, attempt + 1, MAX_RETRIES)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            raise OpenEMRApiError(504, f"Request timed out after {MAX_RETRIES} attempts: {method} {path}")

        except httpx.ConnectError as e:
            logger.warning("Connection error: %s %s (attempt %d/%d): %s", method, path, attempt + 1, MAX_RETRIES, e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            raise OpenEMRApiError(503, f"Cannot connect to OpenEMR after {MAX_RETRIES} attempts")

    raise OpenEMRApiError(503, f"Request failed after {MAX_RETRIES} retries: {method} {path}")
# end AI-generated
