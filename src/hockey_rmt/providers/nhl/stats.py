from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import requests

from hockey_rmt.domain.player_stats import (
    GoalieSeasonStats,
    SkaterSeasonStats,
)


STATS_BASE_URL = (
    "https://api.nhle.com/stats/rest/en"
)


class NhlStatsError(RuntimeError):
    """Official NHL statistical retrieval failed."""


SKATER_SUMMARY_FIELDS = (
    "playerId",
    "skaterFullName",
    "gamesPlayed",
    "goals",
    "assists",
    "penaltyMinutes",
    "ppPoints",
    "shPoints",
    "shots",
)

SKATER_REALTIME_FIELDS = (
    "playerId",
    "skaterFullName",
    "gamesPlayed",
    "hits",
    "blockedShots",
)

GOALIE_SUMMARY_FIELDS = (
    "playerId",
    "goalieFullName",
    "gamesPlayed",
    "wins",
    "goalsAgainst",
    "saves",
    "shutouts",
)


def _required_value(
    row: Mapping[str, Any],
    field: str,
) -> Any:
    if (
        field not in row
        or row[field] is None
    ):
        raise NhlStatsError(
            "NHL statistics row is missing "
            f"required field {field!r}."
        )

    return row[field]


def _required_int(
    row: Mapping[str, Any],
    field: str,
) -> int:
    value = _required_value(
        row,
        field,
    )

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise NhlStatsError(
            "NHL statistics field "
            f"{field!r} was not integer-like: "
            f"{value!r}."
        ) from exc


def _required_name(
    row: Mapping[str, Any],
    field: str,
) -> str:
    value = str(
        _required_value(
            row,
            field,
        )
    ).strip()

    if not value:
        raise NhlStatsError(
            "NHL statistics field "
            f"{field!r} was blank."
        )

    return value


def _fetch_report(
    path: str,
    *,
    season_id: int,
    game_type_id: int = 2,
    timeout_seconds: int = 30,
    session: requests.Session | None = None,
) -> tuple[Mapping[str, Any], ...]:
    http = (
        session
        if session is not None
        else requests.Session()
    )

    try:
        response = http.get(
            f"{STATS_BASE_URL}/{path}",
            params={
                "isAggregate": "true",
                "isGame": "false",
                "start": 0,
                "limit": -1,
                "sort": "playerId",
                "dir": "asc",
                "cayenneExp": (
                    f"seasonId={season_id} "
                    f"and gameTypeId={game_type_id}"
                ),
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
        raise NhlStatsError(
            "NHL statistics request failed "
            f"for report {path!r}."
        ) from exc

    except ValueError as exc:
        raise NhlStatsError(
            "NHL statistics response was not "
            "valid JSON."
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise NhlStatsError(
            "NHL statistics response was not "
            "an object."
        )

    rows = payload.get(
        "data"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise NhlStatsError(
            "NHL statistics response did not "
            "contain a data list."
        )

    try:
        total = int(
            payload.get(
                "total"
            )
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise NhlStatsError(
            "NHL statistics response did not "
            "contain a valid total."
        ) from exc

    if len(rows) != total:
        raise NhlStatsError(
            "NHL statistics row count did not "
            "match reported total: "
            f"rows={len(rows)}, total={total}."
        )

    result: list[
        Mapping[str, Any]
    ] = []

    ids: list[int] = []

    for row in rows:
        if not isinstance(
            row,
            Mapping,
        ):
            raise NhlStatsError(
                "NHL statistics row was not "
                "an object."
            )

        player_id = _required_int(
            row,
            "playerId",
        )

        ids.append(
            player_id
        )

        result.append(
            row
        )

    if len(ids) != len(set(ids)):
        raise NhlStatsError(
            "NHL statistics report contained "
            "duplicate playerId values."
        )

    if ids != sorted(ids):
        raise NhlStatsError(
            "NHL statistics report was not "
            "returned in deterministic "
            "playerId order."
        )

    return tuple(result)


def _require_fields(
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> None:
    for row in rows:
        for field in fields:
            _required_value(
                row,
                field,
            )


def _validate_optional_season_id(
    rows: Sequence[Mapping[str, Any]],
    requested_season_id: int,
) -> None:
    for row in rows:
        value = row.get(
            "seasonId"
        )

        if value is None:
            continue

        try:
            row_season_id = int(
                value
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise NhlStatsError(
                "NHL statistics row contained "
                "a non-integer seasonId: "
                f"{value!r}."
            ) from exc

        if (
            row_season_id
            != requested_season_id
        ):
            raise NhlStatsError(
                "NHL statistics row seasonId "
                "did not match requested season: "
                f"row={row_season_id}, "
                f"requested={requested_season_id}."
            )


def fetch_skater_season_stats(
    *,
    season_id: int,
    game_type_id: int = 2,
    timeout_seconds: int = 30,
    session: requests.Session | None = None,
) -> tuple[SkaterSeasonStats, ...]:
    summary_rows = _fetch_report(
        "skater/summary",
        season_id=season_id,
        game_type_id=game_type_id,
        timeout_seconds=timeout_seconds,
        session=session,
    )

    realtime_rows = _fetch_report(
        "skater/realtime",
        season_id=season_id,
        game_type_id=game_type_id,
        timeout_seconds=timeout_seconds,
        session=session,
    )

    _require_fields(
        summary_rows,
        SKATER_SUMMARY_FIELDS,
    )

    _require_fields(
        realtime_rows,
        SKATER_REALTIME_FIELDS,
    )

    _validate_optional_season_id(
        summary_rows,
        season_id,
    )

    _validate_optional_season_id(
        realtime_rows,
        season_id,
    )

    summary_by_id = {
        _required_int(
            row,
            "playerId",
        ): row
        for row in summary_rows
    }

    realtime_by_id = {
        _required_int(
            row,
            "playerId",
        ): row
        for row in realtime_rows
    }

    summary_ids = set(
        summary_by_id
    )

    realtime_ids = set(
        realtime_by_id
    )

    if summary_ids != realtime_ids:
        raise NhlStatsError(
            "NHL skater summary and realtime "
            "playerId sets did not match: "
            f"summary_only="
            f"{len(summary_ids - realtime_ids)}, "
            f"realtime_only="
            f"{len(realtime_ids - summary_ids)}."
        )

    result: list[
        SkaterSeasonStats
    ] = []

    for player_id in sorted(
        summary_ids
    ):
        summary = summary_by_id[
            player_id
        ]

        realtime = realtime_by_id[
            player_id
        ]

        summary_gp = _required_int(
            summary,
            "gamesPlayed",
        )

        realtime_gp = _required_int(
            realtime,
            "gamesPlayed",
        )

        if summary_gp != realtime_gp:
            raise NhlStatsError(
                "NHL skater gamesPlayed mismatch "
                f"for playerId {player_id}: "
                f"summary={summary_gp}, "
                f"realtime={realtime_gp}."
            )

        result.append(
            SkaterSeasonStats(
                nhl_player_id=player_id,
                full_name=_required_name(
                    summary,
                    "skaterFullName",
                ),
                season_id=season_id,
                games_played=summary_gp,
                goals=_required_int(
                    summary,
                    "goals",
                ),
                assists=_required_int(
                    summary,
                    "assists",
                ),
                penalty_minutes=_required_int(
                    summary,
                    "penaltyMinutes",
                ),
                power_play_points=(
                    _required_int(
                        summary,
                        "ppPoints",
                    )
                ),
                short_handed_points=(
                    _required_int(
                        summary,
                        "shPoints",
                    )
                ),
                shots=_required_int(
                    summary,
                    "shots",
                ),
                hits=_required_int(
                    realtime,
                    "hits",
                ),
                blocked_shots=_required_int(
                    realtime,
                    "blockedShots",
                ),
            )
        )

    return tuple(result)


def fetch_goalie_season_stats(
    *,
    season_id: int,
    game_type_id: int = 2,
    timeout_seconds: int = 30,
    session: requests.Session | None = None,
) -> tuple[GoalieSeasonStats, ...]:
    rows = _fetch_report(
        "goalie/summary",
        season_id=season_id,
        game_type_id=game_type_id,
        timeout_seconds=timeout_seconds,
        session=session,
    )

    _require_fields(
        rows,
        GOALIE_SUMMARY_FIELDS,
    )

    _validate_optional_season_id(
        rows,
        season_id,
    )

    return tuple(
        GoalieSeasonStats(
            nhl_player_id=_required_int(
                row,
                "playerId",
            ),
            full_name=_required_name(
                row,
                "goalieFullName",
            ),
            season_id=season_id,
            games_played=_required_int(
                row,
                "gamesPlayed",
            ),
            wins=_required_int(
                row,
                "wins",
            ),
            goals_against=_required_int(
                row,
                "goalsAgainst",
            ),
            saves=_required_int(
                row,
                "saves",
            ),
            shutouts=_required_int(
                row,
                "shutouts",
            ),
        )
        for row in rows
    )
