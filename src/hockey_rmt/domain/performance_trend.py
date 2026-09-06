from __future__ import annotations

from dataclasses import dataclass


TREND_SOURCE_MONEYPUCK = "moneypuck"

WINDOW_SEASON = "season"
WINDOW_LAST_10 = "last_10"
WINDOW_LAST_20 = "last_20"

VALID_TREND_WINDOWS = frozenset(
    {
        WINDOW_SEASON,
        WINDOW_LAST_10,
        WINDOW_LAST_20,
    }
)

SITUATION_ALL = "all"
SITUATION_5_ON_5 = "5on5"
SITUATION_5_ON_4 = "5on4"
SITUATION_4_ON_5 = "4on5"
SITUATION_OTHER = "other"

VALID_MONEYPUCK_SITUATIONS = frozenset(
    {
        SITUATION_ALL,
        SITUATION_5_ON_5,
        SITUATION_5_ON_4,
        SITUATION_4_ON_5,
        SITUATION_OTHER,
    }
)


@dataclass(frozen=True)
class SkaterPerformanceTrend:
    source: str

    season_id: int
    window: str

    nhl_player_id: int
    full_name: str
    nhl_team_abbr: str
    position: str
    situation: str

    ice_time: float

    individual_expected_goals: float
    shots_on_goal: float
    shot_attempts: float
    high_danger_shots: float

    goals: float
    primary_assists: float
    secondary_assists: float

    shots_blocked: float
    penalties: float

    on_ice_expected_goals_percentage: float
