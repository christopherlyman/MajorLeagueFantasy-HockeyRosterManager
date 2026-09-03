from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkaterProjectionCalibration:
    training_target_season_id: int
    training_player_count: int
    minimum_training_games: int
    training_mean_age: float
    bias_adjustment: float
    age_slope_per_year: float


@dataclass(frozen=True)
class CalibratedSkaterProjection:
    nhl_player_id: int
    full_name: str

    historical_baseline_fppg: float

    player_age: float
    calibration_bias_adjustment: float
    age_adjustment: float

    projected_fantasy_points_per_game: float

    historical_seasons_used: int
    historical_games_played: int
    effective_games_played: float
