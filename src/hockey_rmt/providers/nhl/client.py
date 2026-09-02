from __future__ import annotations

from typing import Any

import requests


NHL_BASE_URL = "https://api-web.nhle.com/v1"


class NhlApiError(RuntimeError):
    """NHL API request failed."""


class NhlClient:
    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
    ) -> None:
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
        resource_path: str,
    ) -> dict[str, Any]:
        path = "/" + resource_path.lstrip("/")

        response = self.session.get(
            f"{NHL_BASE_URL}{path}",
            timeout=self.timeout_seconds,
        )

        if response.status_code != 200:
            raise NhlApiError(
                "NHL request failed: "
                f"HTTP {response.status_code} "
                f"for {path}"
            )

        try:
            payload = response.json()
        except (
            requests.exceptions.JSONDecodeError
        ) as exc:
            raise NhlApiError(
                "NHL returned invalid JSON "
                f"for {path}"
            ) from exc

        if not isinstance(payload, dict):
            raise NhlApiError(
                "NHL returned a non-object JSON "
                f"payload for {path}"
            )

        return payload
