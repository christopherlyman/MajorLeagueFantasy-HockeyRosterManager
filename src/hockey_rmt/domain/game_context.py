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

    availability_state: str = "available"
    provider_status: str | None = None
    provider_status_full: str | None = None


@dataclass(frozen=True)
class PlayerScheduleWindow:
    provider_player_key: str
    start_date: date
    end_date: date

    nhl_team_abbr: str | None
    team_resolution_state: str

    scheduled_games: tuple[PlayerGameContext, ...]

    @property
    def game_count(self) -> int:
        return len(self.scheduled_games)
