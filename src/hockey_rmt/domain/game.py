from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class HockeyGame:
    provider: str
    provider_game_id: str

    provider_game_type: int
    game_type: str

    game_date: date
    start_time_utc: datetime
    game_state: str

    away_team_abbr: str
    home_team_abbr: str
