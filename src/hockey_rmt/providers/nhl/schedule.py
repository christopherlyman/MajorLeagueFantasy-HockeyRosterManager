from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping

from hockey_rmt.domain.game import HockeyGame
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
    text = str(value or "").strip()

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


def parse_schedule(
    payload: Mapping[str, Any],
) -> tuple[HockeyGame, ...]:
    weeks = payload.get(
        "gameWeek"
    )

    if not isinstance(weeks, list):
        raise NhlScheduleError(
            "NHL schedule payload did not "
            "contain a gameWeek list."
        )

    games: list[HockeyGame] = []
    seen_ids: set[str] = set()

    for day in weeks:
        if not isinstance(day, Mapping):
            raise NhlScheduleError(
                "NHL gameWeek entry was not "
                "an object."
            )

        try:
            game_date = date.fromisoformat(
                str(day["date"])
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

        if not isinstance(day_games, list):
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

            provider_game_id = str(
                game["id"]
            )

            if provider_game_id in seen_ids:
                raise NhlScheduleError(
                    "NHL schedule returned "
                    "duplicate game "
                    f"{provider_game_id!r}."
                )

            seen_ids.add(
                provider_game_id
            )

            provider_game_type = int(
                game["gameType"]
            )

            away = game.get(
                "awayTeam"
            ) or {}

            home = game.get(
                "homeTeam"
            ) or {}

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

            games.append(
                HockeyGame(
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
            )

    return tuple(games)


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
