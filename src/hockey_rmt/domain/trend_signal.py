from __future__ import annotations

from dataclasses import dataclass


TREND_IMPROVING = "improving"
TREND_STABLE = "stable"
TREND_DECLINING = "declining"
TREND_MIXED = "mixed"
TREND_INSUFFICIENT_SAMPLE = "insufficient_sample"

ROLE_EXPANDING = "expanding"
ROLE_STABLE = "stable"
ROLE_SHRINKING = "shrinking"
ROLE_MIXED = "mixed"
ROLE_INSUFFICIENT_SAMPLE = "insufficient_sample"

FINISHING_HOT = "hot"
FINISHING_NEUTRAL = "neutral"
FINISHING_COLD = "cold"
FINISHING_MIXED = "mixed"
FINISHING_INSUFFICIENT_SAMPLE = "insufficient_sample"

SAMPLE_AVAILABLE = "available"
SAMPLE_INSUFFICIENT = "insufficient_sample"


@dataclass(frozen=True)
class MetricTrendEvidence:
    metric_name: str

    season_value: float
    last_20_value: float
    last_10_value: float

    last_20_change: float
    last_10_change: float

    state: str


@dataclass(frozen=True)
class SkaterTrendInterpretation:
    source: str
    season_id: int

    nhl_player_id: int
    full_name: str
    nhl_team_abbr: str
    position: str

    season_games_played: int
    last_20_games_played: int
    last_10_games_played: int

    role_sample_state: str
    process_sample_state: str

    toi_usage: MetricTrendEvidence
    power_play_toi_usage: MetricTrendEvidence
    role_state: str

    process_metrics: tuple[
        MetricTrendEvidence,
        ...,
    ]
    process_state: str
    process_improving_metrics: int
    process_stable_metrics: int
    process_declining_metrics: int
    process_mixed_metrics: int

    finishing_state: str

    season_goals_minus_expected_per_60: float
    last_20_goals_minus_expected_per_60: float
    last_10_goals_minus_expected_per_60: float
