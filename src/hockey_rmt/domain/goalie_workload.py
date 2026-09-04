from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class GoalieWorkloadProjection:
    source: str
    source_snapshot_date: date
    projection_season_id: int

    full_name: str
    nhl_team_abbr: str

    projected_games_started: float


@dataclass(frozen=True)
class GoalieSeasonWorkload:
    nhl_player_id: int
    full_name: str
    season_id: int
    games_started: int
