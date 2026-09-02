from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


YAHOO_FANTASY_BASE_URL = (
    "https://fantasysports.yahooapis.com/fantasy/v2"
)


class YahooApiError(RuntimeError):
    """Yahoo Fantasy Sports API request failed."""


class YahooClient:
    def __init__(
        self,
        access_token: str,
        *,
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        token = access_token.strip()

        if not token:
            raise ValueError(
                "Yahoo access token must not be empty."
            )

        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
            }
        )

    def get_json(
        self,
        resource_path: str,
    ) -> dict[str, Any]:
        path = "/" + resource_path.lstrip("/")

        response = self.session.get(
            f"{YAHOO_FANTASY_BASE_URL}{path}",
            params={"format": "json"},
            timeout=self.timeout_seconds,
        )

        if response.status_code != 200:
            raise YahooApiError(
                "Yahoo request failed: "
                f"HTTP {response.status_code} "
                f"for {path}"
            )

        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise YahooApiError(
                "Yahoo returned invalid JSON "
                f"for {path}"
            ) from exc

        if not isinstance(payload, dict):
            raise YahooApiError(
                "Yahoo returned a non-object JSON "
                f"payload for {path}"
            )

        return payload


def write_raw_snapshot(
    payload: dict[str, Any],
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(destination)
