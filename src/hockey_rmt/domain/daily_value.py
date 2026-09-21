from __future__ import annotations

from datetime import datetime

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


DAILY_VALUE_PLAYER_UNAVAILABLE = (
    "player_unavailable"
)

DAILY_VALUE_GOALIE_START_UNKNOWN = (
    "goalie_start_unknown"
)
DAILY_VALUE_GOALIE_START_LIKELY = (
    "goalie_start_likely"
)
DAILY_VALUE_GOALIE_START_UNCONFIRMED = (
    "goalie_start_unconfirmed"
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

    adjustment_state: str | None = None

    adjusted_fantasy_points_per_game: (
        float | None
    ) = None

    adjustment_factor: float | None = None

    provider_game_id: str | None = None
    opponent_team_abbr: str | None = None
    home_away: str | None = None
    start_time_utc: datetime | None = None

    availability_state: str = "available"
    provider_status: str | None = None
    provider_status_full: str | None = None

    goalie_start_state: str | None = None
    goalie_start_source: str | None = None
    goalie_start_provider_goalie_id: int | None = None
    goalie_start_evidence_created_at_utc: (
        datetime | None
    ) = None
    goalie_start_evidence_source_name: (
        str | None
    ) = None
    goalie_start_evidence_source_url: (
        str | None
    ) = None
