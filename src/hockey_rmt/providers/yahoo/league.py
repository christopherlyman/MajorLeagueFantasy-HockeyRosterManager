from __future__ import annotations

from pathlib import Path

from hockey_rmt.domain.league import LeagueDefinition
from hockey_rmt.providers.yahoo.client import (
    YahooApiError,
    YahooClient,
    write_raw_snapshot,
)
from hockey_rmt.providers.yahoo.settings import (
    parse_league_settings,
)


def fetch_league_definition(
    client: YahooClient,
    league_key: str,
    *,
    raw_destination: Path | None = None,
) -> LeagueDefinition:
    key = league_key.strip()

    if not key:
        raise ValueError(
            "Yahoo league key must not be empty."
        )

    payload = client.get_json(
        f"/league/{key}/settings"
    )

    if raw_destination is not None:
        write_raw_snapshot(
            payload,
            raw_destination,
        )

    league = parse_league_settings(
        payload
    )

    if league.provider_league_key != key:
        raise YahooApiError(
            "Yahoo returned league "
            f"{league.provider_league_key!r} "
            f"when {key!r} was requested."
        )

    return league
