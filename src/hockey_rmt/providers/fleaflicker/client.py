from __future__ import annotations

from typing import Any, Mapping

import requests


FLEAFLICKER_API_BASE_URL = (
    "https://www.fleaflicker.com/api"
)


class FleaflickerApiError(RuntimeError):
    """Fleaflicker API request failed."""


class FleaflickerClient:
    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "Fleaflicker timeout must be positive."
            )

        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    "HockeyRosterManager/0.1"
                ),
            }
        )

    def get_json(
        self,
        endpoint: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> dict[str, Any]:
        resource = endpoint.strip()

        if not resource:
            raise ValueError(
                "Fleaflicker endpoint must not be empty."
            )

        path = "/" + resource.lstrip("/")

        response = self.session.get(
            f"{FLEAFLICKER_API_BASE_URL}{path}",
            params=dict(params or {}),
            timeout=self.timeout_seconds,
        )

        if response.status_code != 200:
            raise FleaflickerApiError(
                "Fleaflicker request failed: "
                f"HTTP {response.status_code} "
                f"for {path}"
            )

        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise FleaflickerApiError(
                "Fleaflicker returned invalid JSON "
                f"for {path}"
            ) from exc

        if not isinstance(payload, dict):
            raise FleaflickerApiError(
                "Fleaflicker returned a non-object JSON "
                f"payload for {path}"
            )

        return payload
