from __future__ import annotations

from dataclasses import dataclass
from datetime import date


DAILY_VALUE_AVAILABLE = "available"
DAILY_VALUE_OFF = "off"

DAILY_VALUE_SCHEDULE_UNKNOWN = (
    "schedule_unknown"
)

DAILY_VALUE_STRENGTH_UNAVAILABLE = (
    "strength_unavailable"
)

DAILY_VALUE_SOURCE_SEASON_STRENGTH = (
    "season_strength"
)


@dataclass(frozen=True)
class DailyExpectedValue:
    provider_player_key: str
    full_name: str

    season_id: int
    game_date: date
    player_type: str

    nhl_player_id: int | None
    nhl_team_abbr: str | None

    schedule_state: str
    value_state: str

    baseline_source: str | None

    baseline_fantasy_points_per_game: (
        float | None
    )

    expected_fantasy_points: float | None

    provider_game_id: str | None = None
    opponent_team_abbr: str | None = None
    home_away: str | None = None
