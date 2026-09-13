from __future__ import annotations

from dataclasses import dataclass


ADJUSTMENT_APPLIED = "adjusted"
ADJUSTMENT_BASELINE_ONLY = "baseline_only"
ADJUSTMENT_NOT_APPLICABLE = "not_applicable"
ADJUSTMENT_STRENGTH_UNAVAILABLE = (
    "strength_unavailable"
)


@dataclass(frozen=True)
class PlayerProjectionAdjustment:
    provider_player_key: str
    full_name: str

    projection_season_id: int
    player_type: str
    nhl_player_id: int | None

    adjustment_state: str

    baseline_fantasy_points_per_game: (
        float | None
    )

    adjusted_fantasy_points_per_game: (
        float | None
    )

    deployment_factor: float
    trend_role_factor: float
    process_factor: float
    production_factor: float
    combined_factor: float

    deployment_even_strength_group: (
        str | None
    )

    deployment_power_play_group: (
        str | None
    )

    current_production_games: int | None
    current_production_fantasy_points_per_game: (
        float | None
    )

    role_state: str | None
    process_state: str | None
    finishing_state: str | None

    reasons: tuple[
        str,
        ...,
    ]
