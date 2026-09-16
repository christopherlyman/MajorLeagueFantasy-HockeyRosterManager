from __future__ import annotations

from dataclasses import dataclass


MARKET_ACTION_ADD = "ADD"
MARKET_ACTION_DROP = "DROP"
MARKET_ACTION_STREAM = "STREAM"
MARKET_ACTION_HOLD = "HOLD"


@dataclass(frozen=True)
class MarketRecommendation:
    action: str

    add_player_key: str
    add_player_name: str

    drop_player_key: str
    drop_player_name: str

    usable_three_day_gain: float
    baseline_usable_points: float
    projected_usable_points: float

    add_three_day_expected_points: float
    drop_three_day_expected_points: float

    add_scheduled_games: int
    drop_scheduled_games: int

    add_per_game_value: float | None
    drop_per_game_value: float | None

    add_percent_rostered: int | None

    reason: str


@dataclass(frozen=True)
class MarketDecisionResult:
    state: str
    overall_action: str

    baseline_usable_points: float

    weekly_adds_remaining: int | None

    candidate_pool_count: int
    waiver_candidates_skipped: int
    droppable_skater_count: int

    recommendations: tuple[
        MarketRecommendation,
        ...,
    ]
