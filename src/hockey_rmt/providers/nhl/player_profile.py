from __future__ import annotations

from datetime import date
from typing import Any, Mapping

import requests

from hockey_rmt.domain.player_profile import (
    NhlPlayerProfile,
)


WEB_BASE_URL = "https://api-web.nhle.com/v1"


class NhlPlayerProfileError(
    RuntimeError
):
    """Official NHL player profile retrieval failed."""


def _optional_int(
    mapping: Mapping[str, Any],
    field: str,
) -> int | None:
    value = mapping.get(field)

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NhlPlayerProfileError(
            f"NHL player profile field "
            f"{field!r} was not an integer: "
            f"{value!r}."
        ) from exc


def fetch_player_profile(
    *,
    nhl_player_id: int,
    timeout_seconds: float = 60.0,
) -> NhlPlayerProfile:
    response = requests.get(
        (
            f"{WEB_BASE_URL}/player/"
            f"{int(nhl_player_id)}/landing"
        ),
        headers={
            "Accept": "application/json",
            "User-Agent": "HockeyRosterManager/0.1",
        },
        timeout=timeout_seconds,
    )

    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise NhlPlayerProfileError(
            "NHL player landing response "
            "was not valid JSON."
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise NhlPlayerProfileError(
            "NHL player landing response "
            "was not an object."
        )

    birth_date_text = payload.get(
        "birthDate"
    )

    if not birth_date_text:
        raise NhlPlayerProfileError(
            "NHL player landing response "
            "did not contain birthDate."
        )

    try:
        birth_date = date.fromisoformat(
            str(birth_date_text)
        )
    except ValueError as exc:
        raise NhlPlayerProfileError(
            "NHL player landing birthDate "
            f"was invalid: {birth_date_text!r}."
        ) from exc

    draft = payload.get(
        "draftDetails"
    )

    if draft is None:
        draft = {}

    if not isinstance(
        draft,
        Mapping,
    ):
        raise NhlPlayerProfileError(
            "NHL player landing draftDetails "
            "was not an object."
        )

    season_totals = payload.get(
        "seasonTotals",
        [],
    )

    if not isinstance(
        season_totals,
        list,
    ):
        raise NhlPlayerProfileError(
            "NHL player landing seasonTotals "
            "was not a list."
        )

    nhl_seasons = set()

    for row in season_totals:
        if not isinstance(
            row,
            Mapping,
        ):
            continue

        league = str(
            row.get("leagueAbbrev")
            or ""
        ).upper()

        if league != "NHL":
            continue

        if row.get("gameTypeId") != 2:
            continue

        season_value = row.get(
            "season"
        )

        if season_value is None:
            continue

        try:
            season_id = int(
                season_value
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise NhlPlayerProfileError(
                "NHL regular-season row "
                "contained invalid season: "
                f"{season_value!r}."
            ) from exc

        games_played = row.get(
            "gamesPlayed"
        )

        try:
            games_played_int = int(
                games_played or 0
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise NhlPlayerProfileError(
                "NHL regular-season row "
                "contained invalid gamesPlayed: "
                f"{games_played!r}."
            ) from exc

        if games_played_int > 0:
            nhl_seasons.add(
                season_id
            )

    return NhlPlayerProfile(
        nhl_player_id=int(
            nhl_player_id
        ),
        birth_date=birth_date,
        draft_year=_optional_int(
            draft,
            "year",
        ),
        draft_round=_optional_int(
            draft,
            "round",
        ),
        draft_overall=_optional_int(
            draft,
            "overallPick",
        ),
        nhl_regular_season_ids=tuple(
            sorted(
                nhl_seasons
            )
        ),
    )
