from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Mapping

from hockey_rmt.domain.game import HockeyGame
from hockey_rmt.domain.hockey_team import HockeyTeam
from hockey_rmt.providers.nhl.client import (
    NhlClient,
)


class NhlScheduleError(RuntimeError):
    """NHL schedule parsing failed."""


def _canonical_game_type(
    provider_game_type: int,
) -> str:
    known = {
        1: "preseason",
        2: "regular_season",
    }

    return known.get(
        provider_game_type,
        "unknown",
    )


def _parse_utc_datetime(
    value: object,
) -> datetime:
    text = str(
        value or ""
    ).strip()

    if not text:
        raise NhlScheduleError(
            "NHL game did not contain "
            "a startTimeUTC value."
        )

    try:
        parsed = datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise NhlScheduleError(
            "Invalid NHL startTimeUTC "
            f"value {text!r}."
        ) from exc

    if parsed.tzinfo is None:
        raise NhlScheduleError(
            "NHL startTimeUTC was not "
            "timezone-aware."
        )

    return parsed


def _parse_game(
    game: Mapping[str, Any],
    *,
    game_date: date,
) -> HockeyGame:
    provider_game_id = str(
        game["id"]
    )

    provider_game_type = int(
        game["gameType"]
    )

    away = (
        game.get("awayTeam")
        or {}
    )

    home = (
        game.get("homeTeam")
        or {}
    )

    away_abbr = str(
        away.get("abbrev")
        or ""
    )

    home_abbr = str(
        home.get("abbrev")
        or ""
    )

    if not away_abbr or not home_abbr:
        raise NhlScheduleError(
            "NHL game "
            f"{provider_game_id!r} "
            "did not contain both "
            "team abbreviations."
        )

    return HockeyGame(
        provider="nhl",
        provider_game_id=(
            provider_game_id
        ),
        provider_game_type=(
            provider_game_type
        ),
        game_type=(
            _canonical_game_type(
                provider_game_type
            )
        ),
        game_date=game_date,
        start_time_utc=(
            _parse_utc_datetime(
                game.get(
                    "startTimeUTC"
                )
            )
        ),
        game_state=str(
            game.get(
                "gameState"
            )
            or ""
        ),
        away_team_abbr=(
            away_abbr
        ),
        home_team_abbr=(
            home_abbr
        ),
    )


def parse_schedule(
    payload: Mapping[str, Any],
) -> tuple[HockeyGame, ...]:
    weeks = payload.get(
        "gameWeek"
    )

    if not isinstance(
        weeks,
        list,
    ):
        raise NhlScheduleError(
            "NHL schedule payload did not "
            "contain a gameWeek list."
        )

    games: list[
        HockeyGame
    ] = []

    seen_ids: set[
        str
    ] = set()

    for day in weeks:
        if not isinstance(
            day,
            Mapping,
        ):
            raise NhlScheduleError(
                "NHL gameWeek entry was not "
                "an object."
            )

        try:
            game_date = (
                date.fromisoformat(
                    str(
                        day["date"]
                    )
                )
            )
        except (
            KeyError,
            ValueError,
        ) as exc:
            raise NhlScheduleError(
                "NHL gameWeek entry had an "
                "invalid date."
            ) from exc

        day_games = day.get(
            "games",
            [],
        )

        if not isinstance(
            day_games,
            list,
        ):
            raise NhlScheduleError(
                "NHL gameWeek games value "
                "was not a list."
            )

        for game in day_games:
            if not isinstance(
                game,
                Mapping,
            ):
                raise NhlScheduleError(
                    "NHL game entry was not "
                    "an object."
                )

            parsed = _parse_game(
                game,
                game_date=game_date,
            )

            if (
                parsed.provider_game_id
                in seen_ids
            ):
                raise NhlScheduleError(
                    "NHL schedule returned "
                    "duplicate game "
                    f"{parsed.provider_game_id!r}."
                )

            seen_ids.add(
                parsed.provider_game_id
            )

            games.append(
                parsed
            )

    return tuple(
        games
    )


def parse_club_season_schedule(
    payload: Mapping[str, Any],
) -> tuple[HockeyGame, ...]:
    raw_games = payload.get(
        "games"
    )

    if not isinstance(
        raw_games,
        list,
    ):
        raise NhlScheduleError(
            "NHL club season schedule did "
            "not contain a games list."
        )

    games: list[
        HockeyGame
    ] = []

    seen_ids: set[
        str
    ] = set()

    for game in raw_games:
        if not isinstance(
            game,
            Mapping,
        ):
            raise NhlScheduleError(
                "NHL club season game "
                "was not an object."
            )

        try:
            game_date = (
                date.fromisoformat(
                    str(
                        game["gameDate"]
                    )
                )
            )
        except (
            KeyError,
            ValueError,
        ) as exc:
            raise NhlScheduleError(
                "NHL club season game had "
                "an invalid gameDate."
            ) from exc

        parsed = _parse_game(
            game,
            game_date=game_date,
        )

        if (
            parsed.provider_game_id
            in seen_ids
        ):
            raise NhlScheduleError(
                "NHL club season schedule "
                "returned duplicate game "
                f"{parsed.provider_game_id!r}."
            )

        seen_ids.add(
            parsed.provider_game_id
        )

        games.append(
            parsed
        )

    return tuple(
        games
    )


def fetch_schedule(
    client: NhlClient,
    anchor_date: date,
) -> tuple[HockeyGame, ...]:
    payload = client.get_json(
        f"/schedule/"
        f"{anchor_date.isoformat()}"
    )

    return parse_schedule(
        payload
    )


def fetch_club_season_schedule(
    client: NhlClient,
    *,
    team_abbr: str,
    season_id: int,
) -> tuple[HockeyGame, ...]:
    team = str(
        team_abbr
    ).strip().upper()

    if not team:
        raise NhlScheduleError(
            "NHL team abbreviation "
            "must not be empty."
        )

    payload = client.get_json(
        "/club-schedule-season/"
        f"{team}/{int(season_id)}"
    )

    games = (
        parse_club_season_schedule(
            payload
        )
    )

    for game in games:
        if (
            team
            not in {
                game.away_team_abbr,
                game.home_team_abbr,
            }
        ):
            raise NhlScheduleError(
                "Club season schedule for "
                f"{team} contained game "
                f"{game.provider_game_id!r} "
                "without that team."
            )

    return games


def fetch_regular_season_game_counts(
    client: NhlClient,
    *,
    teams: Sequence[HockeyTeam],
    season_id: int,
) -> dict[str, int]:
    if not teams:
        raise NhlScheduleError(
            "No NHL teams were supplied "
            "for season schedule validation."
        )

    counts: dict[
        str,
        int,
    ] = {}

    for team in teams:
        abbreviation = str(
            team.abbreviation
        ).strip().upper()

        if not abbreviation:
            raise NhlScheduleError(
                "Canonical NHL team had "
                "no abbreviation."
            )

        if abbreviation in counts:
            raise NhlScheduleError(
                "Duplicate canonical NHL "
                "team abbreviation "
                f"{abbreviation!r}."
            )

        games = (
            fetch_club_season_schedule(
                client,
                team_abbr=abbreviation,
                season_id=season_id,
            )
        )

        regular_games = [
            game
            for game in games
            if (
                game.game_type
                == "regular_season"
            )
        ]

        if not regular_games:
            raise NhlScheduleError(
                "No regular-season games "
                "were found for "
                f"{abbreviation} in "
                f"{season_id}."
            )

        counts[
            abbreviation
        ] = len(
            regular_games
        )

    return counts
