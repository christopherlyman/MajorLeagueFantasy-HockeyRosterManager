from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class PlayerGameContext:
    provider_player_key: str
    game_date: date

    nhl_team_abbr: str | None
    schedule_state: str

    provider_game_id: str | None = None
    opponent_team_abbr: str | None = None
    home_away: str | None = None
    start_time_utc: datetime | None = None
