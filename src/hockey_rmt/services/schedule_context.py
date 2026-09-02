from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from hockey_rmt.domain.game import HockeyGame
from hockey_rmt.domain.game_context import (
    PlayerGameContext,
)
from hockey_rmt.domain.player import Player


class ScheduleContextError(RuntimeError):
    """Player schedule context could not be resolved."""


def build_player_game_context(
    player: Player,
    games: Sequence[HockeyGame],
    game_date: date,
) -> PlayerGameContext:
    team = (
        player.nhl_team_abbr.strip()
        if player.nhl_team_abbr
        else ""
    )

    if not team:
        return PlayerGameContext(
            provider_player_key=(
                player.provider_player_key
            ),
            game_date=game_date,
            nhl_team_abbr=None,
            schedule_state="unknown_team",
        )

    matching_games = [
        game
        for game in games
        if game.game_date == game_date
        and team in {
            game.away_team_abbr,
            game.home_team_abbr,
        }
    ]

    if not matching_games:
        return PlayerGameContext(
            provider_player_key=(
                player.provider_player_key
            ),
            game_date=game_date,
            nhl_team_abbr=team,
            schedule_state="off",
        )

    if len(matching_games) > 1:
        raise ScheduleContextError(
            "Multiple NHL games found for "
            f"team {team!r} on "
            f"{game_date.isoformat()}."
        )

    game = matching_games[0]

    if team == game.home_team_abbr:
        home_away = "home"
        opponent = game.away_team_abbr
    else:
        home_away = "away"
        opponent = game.home_team_abbr

    return PlayerGameContext(
        provider_player_key=(
            player.provider_player_key
        ),
        game_date=game_date,
        nhl_team_abbr=team,
        schedule_state="scheduled",
        provider_game_id=(
            game.provider_game_id
        ),
        opponent_team_abbr=opponent,
        home_away=home_away,
        start_time_utc=(
            game.start_time_utc
        ),
    )
