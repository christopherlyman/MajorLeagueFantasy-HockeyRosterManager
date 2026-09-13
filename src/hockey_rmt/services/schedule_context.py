from __future__ import annotations

from hockey_rmt.domain.player_availability import (
    classify_player_availability,
)

from collections.abc import Sequence
from datetime import date, timedelta

from hockey_rmt.domain.game import HockeyGame
from hockey_rmt.domain.game_context import (
    PlayerGameContext,
    PlayerScheduleWindow,
)
from hockey_rmt.domain.hockey_team import (
    TeamIdentityCrosswalk,
)
from hockey_rmt.domain.player import Player


class ScheduleContextError(RuntimeError):
    """Player schedule context could not be resolved."""


def _crosswalk_by_yahoo_team_key(
    crosswalk: Sequence[TeamIdentityCrosswalk],
) -> dict[str, TeamIdentityCrosswalk]:
    result: dict[
        str,
        TeamIdentityCrosswalk,
    ] = {}

    for row in crosswalk:
        key = row.source_team_key

        if key in result:
            raise ScheduleContextError(
                "Duplicate team crosswalk entry "
                f"for {key!r}."
            )

        result[key] = row

    return result


def _game_index(
    games: Sequence[HockeyGame],
) -> dict[tuple[date, str], HockeyGame]:
    result: dict[
        tuple[date, str],
        HockeyGame,
    ] = {}

    for game in games:
        for team in (
            game.away_team_abbr,
            game.home_team_abbr,
        ):
            key = (
                game.game_date,
                team,
            )

            if key in result:
                raise ScheduleContextError(
                    "Multiple NHL games found for "
                    f"team {team!r} on "
                    f"{game.game_date.isoformat()}."
                )

            result[key] = game

    return result


def _scheduled_context(
    *,
    player: Player,
    team_abbr: str,
    game: HockeyGame,
) -> PlayerGameContext:
    if team_abbr == game.home_team_abbr:
        home_away = "home"
        opponent = game.away_team_abbr

    elif team_abbr == game.away_team_abbr:
        home_away = "away"
        opponent = game.home_team_abbr

    else:
        raise ScheduleContextError(
            "Requested team "
            f"{team_abbr!r} does not participate "
            f"in NHL game "
            f"{game.provider_game_id!r}."
        )

    return PlayerGameContext(
        provider_player_key=(
            player.provider_player_key
        ),
        game_date=game.game_date,
        nhl_team_abbr=team_abbr,
        schedule_state="scheduled",
        provider_game_id=(
            game.provider_game_id
        ),
        opponent_team_abbr=opponent,
        home_away=home_away,
        start_time_utc=(
            game.start_time_utc
        ),
        availability_state=(
            classify_player_availability(
                provider=player.provider,
                status=player.status,
            )
        ),
        provider_status=player.status,
        provider_status_full=(
            player.status_full
        ),
    )


def resolve_player_nhl_team_abbr(
    player: Player,
    crosswalk: Sequence[TeamIdentityCrosswalk],
) -> str | None:
    if not player.nhl_team_key:
        return None

    by_key = _crosswalk_by_yahoo_team_key(
        crosswalk
    )

    row = by_key.get(
        player.nhl_team_key
    )

    if row is None:
        raise ScheduleContextError(
            "Yahoo NHL team key "
            f"{player.nhl_team_key!r} for "
            f"player "
            f"{player.provider_player_key!r} "
            "was not present in the canonical "
            "team crosswalk."
        )

    return row.canonical_team_abbr


def build_player_game_context(
    player: Player,
    games: Sequence[HockeyGame],
    game_date: date,
    crosswalk: Sequence[TeamIdentityCrosswalk],
) -> PlayerGameContext:
    team = resolve_player_nhl_team_abbr(
        player,
        crosswalk,
    )

    if not team:
        return PlayerGameContext(
            provider_player_key=(
                player.provider_player_key
            ),
            game_date=game_date,
            nhl_team_abbr=None,
            schedule_state="unknown_team",
            availability_state=(
                classify_player_availability(
                    provider=player.provider,
                    status=player.status,
                )
            ),
            provider_status=player.status,
            provider_status_full=(
                player.status_full
            ),
        )

    index = _game_index(games)

    game = index.get(
        (
            game_date,
            team,
        )
    )

    if game is None:
        return PlayerGameContext(
            provider_player_key=(
                player.provider_player_key
            ),
            game_date=game_date,
            nhl_team_abbr=team,
            schedule_state="off",
            availability_state=(
                classify_player_availability(
                    provider=player.provider,
                    status=player.status,
                )
            ),
            provider_status=player.status,
            provider_status_full=(
                player.status_full
            ),
        )

    return _scheduled_context(
        player=player,
        team_abbr=team,
        game=game,
    )


def build_player_schedule_windows(
    players: Sequence[Player],
    games: Sequence[HockeyGame],
    crosswalk: Sequence[TeamIdentityCrosswalk],
    *,
    start_date: date,
    end_date: date,
) -> tuple[PlayerScheduleWindow, ...]:
    if end_date < start_date:
        raise ValueError(
            "Schedule end date must not "
            "precede start date."
        )

    crosswalk_by_key = (
        _crosswalk_by_yahoo_team_key(
            crosswalk
        )
    )

    games_by_team_date = _game_index(
        games
    )

    windows: list[
        PlayerScheduleWindow
    ] = []

    for player in players:
        if not player.nhl_team_key:
            windows.append(
                PlayerScheduleWindow(
                    provider_player_key=(
                        player.provider_player_key
                    ),
                    start_date=start_date,
                    end_date=end_date,
                    nhl_team_abbr=None,
                    team_resolution_state=(
                        "unknown_team"
                    ),
                    scheduled_games=(),
                )
            )

            continue

        team_row = crosswalk_by_key.get(
            player.nhl_team_key
        )

        if team_row is None:
            raise ScheduleContextError(
                "Yahoo NHL team key "
                f"{player.nhl_team_key!r} for "
                f"player "
                f"{player.provider_player_key!r} "
                "was not present in the canonical "
                "team crosswalk."
            )

        team_abbr = (
            team_row.canonical_team_abbr
        )

        scheduled: list[
            PlayerGameContext
        ] = []

        current_date = start_date

        while current_date <= end_date:
            game = games_by_team_date.get(
                (
                    current_date,
                    team_abbr,
                )
            )

            if game is not None:
                scheduled.append(
                    _scheduled_context(
                        player=player,
                        team_abbr=team_abbr,
                        game=game,
                    )
                )

            current_date += timedelta(
                days=1
            )

        windows.append(
            PlayerScheduleWindow(
                provider_player_key=(
                    player.provider_player_key
                ),
                start_date=start_date,
                end_date=end_date,
                nhl_team_abbr=team_abbr,
                team_resolution_state=(
                    "resolved"
                ),
                scheduled_games=tuple(
                    scheduled
                ),
            )
        )

    return tuple(windows)
