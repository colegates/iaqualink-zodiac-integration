"""HTTP client for the Zodiac iAquaLink cloud API."""
from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from .const import (
    API_KEY,
    LOGIN_URL,
    SHADOW_URL_TEMPLATE,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class ZodiacAuthError(Exception):
    """Raised when login fails or the token is rejected."""


class ZodiacApiError(Exception):
    """Raised on transport / API errors that aren't auth-related."""


class ZodiacApiClient:
    """Thin async wrapper around the prod.zodiac-io.com endpoints used by iAquaLink."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._id_token: str | None = None
        # IdToken lifetime defaults to 3600s in the login response. Refresh slightly early.
        self._token_expiry: float = 0.0

    async def async_login(self) -> dict[str, Any]:
        """Authenticate and cache the IdToken. Returns the raw login response."""
        payload = {
            "api_key": API_KEY,
            "email": self._email,
            "password": self._password,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        try:
            async with self._session.post(
                LOGIN_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 401 or resp.status == 403:
                    raise ZodiacAuthError(f"Login rejected ({resp.status}): {body}")
                if resp.status >= 400:
                    raise ZodiacApiError(f"Login failed ({resp.status}): {body}")
        except aiohttp.ClientError as err:
            raise ZodiacApiError(f"Login transport error: {err}") from err

        oauth = body.get("userPoolOAuth") or {}
        token = oauth.get("IdToken")
        if not token:
            raise ZodiacAuthError(f"Login response missing IdToken: {body}")
        self._id_token = token
        try:
            expires_in = int(oauth.get("ExpiresIn", 3600))
        except (TypeError, ValueError):
            expires_in = 3600
        # Refresh 5 minutes before expiry.
        self._token_expiry = time.monotonic() + max(60, expires_in - 300)
        return body

    async def _ensure_token(self) -> str:
        if self._id_token is None or time.monotonic() >= self._token_expiry:
            await self.async_login()
        assert self._id_token is not None
        return self._id_token

    def _auth_headers(self, token: str, *, json_body: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": token,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if json_body:
            headers["Content-Type"] = "application/json; charset=utf-8"
        return headers

    async def async_get_shadow(self, serial: str) -> dict[str, Any]:
        """GET the AWS-IoT-style device shadow for a serial."""
        token = await self._ensure_token()
        url = SHADOW_URL_TEMPLATE.format(serial=serial)
        try:
            async with self._session.get(
                url,
                headers=self._auth_headers(token),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (401, 403):
                    # Token may have been invalidated server-side — force re-login once.
                    self._id_token = None
                    token = await self._ensure_token()
                    async with self._session.get(
                        url,
                        headers=self._auth_headers(token),
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as retry:
                        if retry.status >= 400:
                            raise ZodiacApiError(
                                f"Shadow GET failed after re-auth ({retry.status})"
                            )
                        return await retry.json(content_type=None)
                if resp.status >= 400:
                    text = await resp.text()
                    raise ZodiacApiError(f"Shadow GET failed ({resp.status}): {text}")
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise ZodiacApiError(f"Shadow GET transport error: {err}") from err

    async def async_update_shadow(self, serial: str, desired: dict[str, Any]) -> dict[str, Any]:
        """POST a desired-state update to the device shadow.

        ``desired`` is the value of ``state.desired``. For the Z400iQ, setpoint and
        mode live under ``equipment.hp_0``, e.g. ``{"equipment": {"hp_0": {"tsp": 28}}}``.
        """
        token = await self._ensure_token()
        url = SHADOW_URL_TEMPLATE.format(serial=serial)
        body = {"state": {"desired": desired}}
        try:
            async with self._session.post(
                url,
                json=body,
                headers=self._auth_headers(token, json_body=True),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                payload = await resp.json(content_type=None)
                if resp.status in (401, 403):
                    self._id_token = None
                    token = await self._ensure_token()
                    async with self._session.post(
                        url,
                        json=body,
                        headers=self._auth_headers(token, json_body=True),
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as retry:
                        retry_payload = await retry.json(content_type=None)
                        if retry.status >= 400:
                            raise ZodiacApiError(
                                f"Shadow POST failed after re-auth ({retry.status}): {retry_payload}"
                            )
                        return retry_payload
                if resp.status >= 400:
                    raise ZodiacApiError(f"Shadow POST failed ({resp.status}): {payload}")
                return payload
        except aiohttp.ClientError as err:
            raise ZodiacApiError(f"Shadow POST transport error: {err}") from err
