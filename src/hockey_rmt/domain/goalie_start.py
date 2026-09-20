from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


GOALIE_START_SOURCE_DAILY_FACEOFF = (
    "daily_faceoff"
)

GOALIE_START_CONFIRMED = "confirmed"
GOALIE_START_LIKELY = "likely"
GOALIE_START_UNCONFIRMED = "unconfirmed"

GOALIE_START_STATES = frozenset(
    {
        GOALIE_START_CONFIRMED,
        GOALIE_START_LIKELY,
        GOALIE_START_UNCONFIRMED,
    }
)


@dataclass(frozen=True)
class DailyGoalieStartEvidence:
    source: str

    game_date: date
    game_time_utc: datetime

    is_home: bool

    provider_goalie_id: int
    goalie_name: str

    provider_team_id: int
    team_name: str

    provider_opponent_team_id: int
    opponent_team_name: str

    start_state: str

    evidence_created_at_utc: datetime | None
    evidence_source_name: str | None
    evidence_source_url: str | None
