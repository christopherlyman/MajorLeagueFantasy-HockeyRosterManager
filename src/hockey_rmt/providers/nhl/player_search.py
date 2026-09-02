from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import requests

from hockey_rmt.domain.player_identity import (
    NhlPlayerIdentity,
)


SEARCH_URL = (
    "https://search.d3.nhle.com/"
    "api/v1/search/player"
)


class NhlPlayerSearchError(RuntimeError):
    """NHL player-search retrieval or parsing failed."""


def _optional_int(
    value: Any,
) -> int | None:
    if value in (
        None,
        "",
    ):
        return None

    return int(value)


def parse_player_registry(
    payload: Any,
) -> tuple[NhlPlayerIdentity, ...]:
    if not isinstance(
        payload,
        list,
    ):
        raise NhlPlayerSearchError(
            "NHL player-search payload "
            "was not a list."
        )

    players: dict[
        int,
        NhlPlayerIdentity,
    ] = {}

    for row in payload:
        if not isinstance(
            row,
            dict,
        ):
            raise NhlPlayerSearchError(
                "NHL player-search row "
                "was not an object."
            )

        player_id = row.get(
            "playerId"
        )

        full_name = row.get(
            "name"
        )

        if (
            player_id is None
            or not full_name
        ):
            continue

        player_id = int(
            player_id
        )

        active_value = row.get(
            "active"
        )

        active = (
            active_value
            if isinstance(
                active_value,
                bool,
            )
            else None
        )

        position = str(
            row.get(
                "positionCode"
            )
            or ""
        ).upper() or None

        team_abbr = str(
            row.get(
                "teamAbbrev"
            )
            or ""
        ).upper() or None

        player = NhlPlayerIdentity(
            nhl_player_id=player_id,
            full_name=str(
                full_name
            ),
            position=position,
            team_abbr=team_abbr,
            active=active,
            last_season_id=(
                _optional_int(
                    row.get(
                        "lastSeasonId"
                    )
                )
            ),
        )

        existing = players.get(
            player_id
        )

        if (
            existing is not None
            and existing != player
        ):
            raise NhlPlayerSearchError(
                "Conflicting NHL player-search "
                f"rows for playerId "
                f"{player_id!r}."
            )

        players[
            player_id
        ] = player

    return tuple(
        players[player_id]
        for player_id
        in sorted(players)
    )


def fetch_player_registry(
    *,
    timeout_seconds: int = 60,
    session: requests.Session | None = None,
) -> tuple[NhlPlayerIdentity, ...]:
    http = (
        session
        if session is not None
        else requests.Session()
    )

    try:
        response = http.get(
            SEARCH_URL,
            params={
                "culture": "en-us",
                "limit": 50000,
                "q": "*",
            },
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "HockeyRosterManager/0.1"
                ),
            },
            timeout=timeout_seconds,
        )

        response.raise_for_status()

        payload = response.json()

    except requests.RequestException as exc:
        raise NhlPlayerSearchError(
            "NHL player-search request failed."
        ) from exc

    except requests.exceptions.JSONDecodeError as exc:
        raise NhlPlayerSearchError(
            "NHL player-search response "
            "was not valid JSON."
        ) from exc

    return parse_player_registry(
        payload
    )
