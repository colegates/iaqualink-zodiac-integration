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
        _LOGGER.debug("Logging in as %s", self._email)
        try:
            async with self._session.post(
                LOGIN_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 401 or resp.status == 403:
                    _LOGGER.warning("Login rejected for %s (%s)", self._email, resp.status)
                    raise ZodiacAuthError(f"Login rejected ({resp.status}): {body}")
                if resp.status >= 400:
                    _LOGGER.error("Login failed (%s): %s", resp.status, body)
                    raise ZodiacApiError(f"Login failed ({resp.status}): {body}")
        except aiohttp.ClientError as err:
            _LOGGER.error("Login transport error: %s", err)
            raise ZodiacApiError(f"Login transport error: {err}") from err

        oauth = body.get("userPoolOAuth") or {}
        token = oauth.get("IdToken")
        if not token:
            _LOGGER.error("Login response missing IdToken (keys=%s)", list(body.keys()))
            raise ZodiacAuthError("Login response missing IdToken")
        self._id_token = token
        try:
            expires_in = int(oauth.get("ExpiresIn", 3600))
        except (TypeError, ValueError):
            expires_in = 3600
        # Refresh 5 minutes before expiry.
        self._token_expiry = time.monotonic() + max(60, expires_in - 300)
        _LOGGER.debug("Login OK; token valid for ~%ss", expires_in)
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
                    _LOGGER.info("Shadow GET %s returned %s; re-authenticating", serial, resp.status)
                    self._id_token = None
                    token = await self._ensure_token()
                    async with self._session.get(
                        url,
                        headers=self._auth_headers(token),
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as retry:
                        if retry.status in (401, 403):
                            raise ZodiacAuthError(
                                f"Shadow GET still {retry.status} after re-auth"
                            )
                        if retry.status >= 400:
                            raise ZodiacApiError(
                                f"Shadow GET failed after re-auth ({retry.status})"
                            )
                        return await retry.json(content_type=None)
                if resp.status == 429:
                    _LOGGER.warning("iAquaLink rate limit (429) for shadow GET %s", serial)
                    raise ZodiacApiError("Rate limited by iAquaLink (429 Too Many Requests)")
                if resp.status >= 400:
                    text = await resp.text()
                    _LOGGER.error("Shadow GET failed (%s): %s", resp.status, text)
                    raise ZodiacApiError(f"Shadow GET failed ({resp.status}): {text}")
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            _LOGGER.warning("Shadow GET transport error: %s", err)
            raise ZodiacApiError(f"Shadow GET transport error: {err}") from err

    async def async_update_shadow(self, serial: str, desired: dict[str, Any]) -> dict[str, Any]:
        """POST a desired-state update to the device shadow.

        ``desired`` is the value of ``state.desired``. For the Z400iQ, setpoint and
        mode live under ``equipment.hp_0``, e.g. ``{"equipment": {"hp_0": {"tsp": 28}}}``.
        """
        token = await self._ensure_token()
        url = SHADOW_URL_TEMPLATE.format(serial=serial)
        body = {"state": {"desired": desired}}
        _LOGGER.debug("Shadow POST %s desired=%s", serial, desired)
        try:
            async with self._session.post(
                url,
                json=body,
                headers=self._auth_headers(token, json_body=True),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                payload = await resp.json(content_type=None)
                if resp.status in (401, 403):
                    _LOGGER.info("Shadow POST %s returned %s; re-authenticating", serial, resp.status)
                    self._id_token = None
                    token = await self._ensure_token()
                    async with self._session.post(
                        url,
                        json=body,
                        headers=self._auth_headers(token, json_body=True),
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as retry:
                        retry_payload = await retry.json(content_type=None)
                        if retry.status in (401, 403):
                            raise ZodiacAuthError(
                                f"Shadow POST still {retry.status} after re-auth"
                            )
                        if retry.status >= 400:
                            raise ZodiacApiError(
                                f"Shadow POST failed after re-auth ({retry.status}): {retry_payload}"
                            )
                        return retry_payload
                if resp.status == 429:
                    _LOGGER.warning("iAquaLink rate limit (429) for shadow POST %s", serial)
                    raise ZodiacApiError("Rate limited by iAquaLink (429 Too Many Requests)")
                if resp.status >= 400:
                    _LOGGER.error("Shadow POST failed (%s): %s", resp.status, payload)
                    raise ZodiacApiError(f"Shadow POST failed ({resp.status}): {payload}")
                return payload
        except aiohttp.ClientError as err:
            _LOGGER.warning("Shadow POST transport error: %s", err)
            raise ZodiacApiError(f"Shadow POST transport error: {err}") from err
