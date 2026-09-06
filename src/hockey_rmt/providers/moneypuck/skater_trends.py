from __future__ import annotations

import csv
import io
import math
from collections.abc import Sequence

import requests

from hockey_rmt.domain.performance_trend import (
    TREND_SOURCE_MONEYPUCK,
    VALID_MONEYPUCK_SITUATIONS,
    VALID_TREND_WINDOWS,
    WINDOW_LAST_10,
    WINDOW_LAST_20,
    WINDOW_SEASON,
    SkaterPerformanceTrend,
)


MONEYPUCK_BASE_URL = (
    "https://moneypuck.com/moneypuck/"
    "playerData/seasonSummary"
)

_REQUIRED_COLUMNS = frozenset(
    {
        "playerId",
        "name",
        "team",
        "position",
        "situation",
        "games_played",
        "icetime",
        "onIce_xGoalsPercentage",
        "I_F_xGoals",
        "I_F_shotsOnGoal",
        "I_F_shotAttempts",
        "I_F_highDangerShots",
        "I_F_goals",
        "I_F_primaryAssists",
        "I_F_secondaryAssists",
        "shotsBlockedByPlayer",
        "penalties",
    }
)

_WINDOW_FILENAME = {
    WINDOW_SEASON: "skaters.csv",
    WINDOW_LAST_10: "skaters_10.csv",
    WINDOW_LAST_20: "skaters_20.csv",
}


class MoneyPuckSkaterTrendError(
    RuntimeError
):
    """MoneyPuck skater trend data was invalid."""


def _season_start_year(
    season_id: int,
) -> int:
    value = int(
        season_id
    )

    text = str(
        value
    )

    if (
        len(text) != 8
        or not text.isdigit()
    ):
        raise MoneyPuckSkaterTrendError(
            "NHL season ID must contain "
            "eight digits."
        )

    start_year = int(
        text[:4]
    )

    end_year = int(
        text[4:]
    )

    if end_year != start_year + 1:
        raise MoneyPuckSkaterTrendError(
            "NHL season ID must contain "
            "consecutive years."
        )

    return start_year


def _required_text(
    row: dict[str, str],
    field: str,
) -> str:
    value = str(
        row.get(
            field,
            "",
        )
    ).strip()

    if not value:
        raise MoneyPuckSkaterTrendError(
            "MoneyPuck row contained an "
            f"empty {field!r} value."
        )

    return value


def _required_int(
    row: dict[str, str],
    field: str,
) -> int:
    value = _required_text(
        row,
        field,
    )

    try:
        parsed = int(
            value
        )
    except ValueError as exc:
        raise MoneyPuckSkaterTrendError(
            "MoneyPuck field "
            f"{field!r} was not an integer: "
            f"{value!r}."
        ) from exc

    return parsed


def _required_float(
    row: dict[str, str],
    field: str,
) -> float:
    value = _required_text(
        row,
        field,
    )

    try:
        parsed = float(
            value
        )
    except ValueError as exc:
        raise MoneyPuckSkaterTrendError(
            "MoneyPuck field "
            f"{field!r} was not numeric: "
            f"{value!r}."
        ) from exc

    if not math.isfinite(
        parsed
    ):
        raise MoneyPuckSkaterTrendError(
            "MoneyPuck field "
            f"{field!r} was not finite."
        )

    return parsed


def _validate_window(
    window: str,
) -> str:
    value = str(
        window
    ).strip()

    if value not in VALID_TREND_WINDOWS:
        raise MoneyPuckSkaterTrendError(
            "Unsupported MoneyPuck trend "
            f"window: {value!r}."
        )

    return value


def skater_trend_url(
    *,
    season_id: int,
    window: str,
) -> str:
    start_year = (
        _season_start_year(
            season_id
        )
    )

    normalized_window = (
        _validate_window(
            window
        )
    )

    filename = _WINDOW_FILENAME[
        normalized_window
    ]

    return (
        f"{MONEYPUCK_BASE_URL}/"
        f"{start_year}/regular/"
        f"{filename}"
    )


def parse_skater_performance_trends(
    csv_text: str,
    *,
    season_id: int,
    window: str,
) -> tuple[
    SkaterPerformanceTrend,
    ...,
]:
    normalized_window = (
        _validate_window(
            window
        )
    )

    _season_start_year(
        season_id
    )

    reader = csv.DictReader(
        io.StringIO(
            csv_text
        )
    )

    fields = frozenset(
        reader.fieldnames
        or ()
    )

    missing = sorted(
        _REQUIRED_COLUMNS
        - fields
    )

    if missing:
        raise MoneyPuckSkaterTrendError(
            "MoneyPuck skater schema was "
            "missing required columns: "
            f"{missing!r}."
        )

    result: list[
        SkaterPerformanceTrend
    ] = []

    seen_keys: set[
        tuple[
            int,
            str,
            str,
        ]
    ] = set()

    for row in reader:
        player_id = (
            _required_int(
                row,
                "playerId",
            )
        )

        games_played = (
            _required_int(
                row,
                "games_played",
            )
        )

        if games_played < 0:
            raise MoneyPuckSkaterTrendError(
                "MoneyPuck games_played "
                "was negative for NHL playerId "
                f"{player_id}: {games_played}."
            )

        team = _required_text(
            row,
            "team",
        )

        situation = (
            _required_text(
                row,
                "situation",
            )
        )

        if (
            situation
            not in
            VALID_MONEYPUCK_SITUATIONS
        ):
            raise MoneyPuckSkaterTrendError(
                "Unexpected MoneyPuck "
                "situation "
                f"{situation!r}."
            )

        key = (
            player_id,
            team,
            situation,
        )

        if key in seen_keys:
            raise MoneyPuckSkaterTrendError(
                "Duplicate MoneyPuck "
                "player/team/situation row: "
                f"{key!r}."
            )

        seen_keys.add(
            key
        )

        result.append(
            SkaterPerformanceTrend(
                source=(
                    TREND_SOURCE_MONEYPUCK
                ),
                season_id=int(
                    season_id
                ),
                window=(
                    normalized_window
                ),
                nhl_player_id=(
                    player_id
                ),
                full_name=(
                    _required_text(
                        row,
                        "name",
                    )
                ),
                nhl_team_abbr=(
                    team
                ),
                position=(
                    _required_text(
                        row,
                        "position",
                    )
                ),
                situation=(
                    situation
                ),
                games_played=(
                    games_played
                ),
                ice_time_seconds=(
                    _required_float(
                        row,
                        "icetime",
                    )
                ),
                individual_expected_goals=(
                    _required_float(
                        row,
                        "I_F_xGoals",
                    )
                ),
                shots_on_goal=(
                    _required_float(
                        row,
                        "I_F_shotsOnGoal",
                    )
                ),
                shot_attempts=(
                    _required_float(
                        row,
                        "I_F_shotAttempts",
                    )
                ),
                high_danger_shots=(
                    _required_float(
                        row,
                        "I_F_highDangerShots",
                    )
                ),
                goals=(
                    _required_float(
                        row,
                        "I_F_goals",
                    )
                ),
                primary_assists=(
                    _required_float(
                        row,
                        "I_F_primaryAssists",
                    )
                ),
                secondary_assists=(
                    _required_float(
                        row,
                        "I_F_secondaryAssists",
                    )
                ),
                shots_blocked=(
                    _required_float(
                        row,
                        "shotsBlockedByPlayer",
                    )
                ),
                penalties=(
                    _required_float(
                        row,
                        "penalties",
                    )
                ),
                on_ice_expected_goals_percentage=(
                    _required_float(
                        row,
                        "onIce_xGoalsPercentage",
                    )
                ),
            )
        )

    if not result:
        raise MoneyPuckSkaterTrendError(
            "MoneyPuck skater dataset "
            "contained no rows."
        )

    return tuple(
        result
    )


def fetch_skater_performance_trends(
    *,
    season_id: int,
    window: str,
    session: requests.Session | None = None,
    timeout_seconds: float = 30.0,
) -> tuple[
    SkaterPerformanceTrend,
    ...,
]:
    client = (
        session
        if session is not None
        else requests.Session()
    )

    response = client.get(
        skater_trend_url(
            season_id=season_id,
            window=window,
        ),
        timeout=float(
            timeout_seconds
        ),
    )

    if response.status_code != 200:
        raise MoneyPuckSkaterTrendError(
            "MoneyPuck skater download "
            "failed with HTTP "
            f"{response.status_code}."
        )

    return (
        parse_skater_performance_trends(
            response.text,
            season_id=season_id,
            window=window,
        )
    )
