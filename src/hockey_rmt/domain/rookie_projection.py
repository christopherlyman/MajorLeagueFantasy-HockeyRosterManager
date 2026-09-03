from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RookieSkaterProjectionModel:
    training_season_ids: tuple[int, ...]
    training_player_count: int
    minimum_training_games: int

    intercept: float
    age_coefficient: float
    inverse_sqrt_draft_coefficient: float

    age_center: float
    undrafted_effective_pick: int


@dataclass(frozen=True)
class RookieSkaterProjection:
    nhl_player_id: int
    full_name: str

    player_age: float

    draft_overall: int | None
    effective_draft_pick: int

    intercept_component: float
    age_adjustment: float
    draft_adjustment: float

    projected_fantasy_points_per_game: float
