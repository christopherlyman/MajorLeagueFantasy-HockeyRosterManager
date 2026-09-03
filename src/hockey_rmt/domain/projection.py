from __future__ import annotations

from dataclasses import dataclass


HISTORICAL_PROJECTION_AVAILABLE = (
    "historical_projection_available"
)

NO_NHL_HISTORY = (
    "no_nhl_history"
)


@dataclass(frozen=True)
class HistoricalRateProjection:
    nhl_player_id: int
    full_name: str
    player_type: str

    projection_state: str

    projected_fantasy_points_per_game: float | None

    historical_seasons_used: int
    historical_games_played: int
    effective_games_played: float

    unshrunk_fantasy_points_per_game: float | None
    population_mean_fantasy_points_per_game: float | None

    shrinkage_games: float
