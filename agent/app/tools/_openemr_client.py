# AI-generated: Claude Code (claude.ai/code) — OpenEMR REST API client with OAuth2
import httpx
from app.config import settings

_token_cache: dict[str, str] = {}


async def _get_access_token() -> str:
    """Get or refresh an OAuth2 access token from OpenEMR."""
    if "access_token" in _token_cache:
        return _token_cache["access_token"]

    async with httpx.AsyncClient(timeout=10, verify=False) as client:
        resp = await client.post(
            f"{settings.openemr_base_url}/oauth2/default/token",
            data={
                "grant_type": "password",
                "client_id": settings.openemr_client_id,
                "client_secret": settings.openemr_client_secret,
                "username": settings.openemr_username,
                "password": settings.openemr_password,
                "scope": "openid api:oemr api:fhir",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["access_token"] = data["access_token"]
        return data["access_token"]


async def openemr_api(
    method: str, path: str, params: dict | None = None, json: dict | None = None
) -> dict | list | None:
    """Make an authenticated request to the OpenEMR REST API."""
    token = await _get_access_token()
    url = f"{settings.openemr_base_url}/apis/default{path}"

    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        resp = await client.request(
            method,
            url,
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 401:
            _token_cache.clear()
            token = await _get_access_token()
            resp = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
            )
        resp.raise_for_status()
        return resp.json()
# end AI-generated
