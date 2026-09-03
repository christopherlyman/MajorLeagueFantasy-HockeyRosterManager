from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkaterSeasonStats:
    nhl_player_id: int
    full_name: str
    season_id: int
    games_played: int

    goals: int
    assists: int
    penalty_minutes: int

    power_play_points: int
    short_handed_points: int

    shots: int
    hits: int
    blocked_shots: int


@dataclass(frozen=True)
class GoalieSeasonStats:
    nhl_player_id: int
    full_name: str
    season_id: int
    games_played: int

    wins: int
    goals_against: int
    saves: int
    shutouts: int


@dataclass(frozen=True)
class FantasyPointComponent:
    category: str
    stat_value: float
    points_per_unit: float
    fantasy_points: float


@dataclass(frozen=True)
class HistoricalFantasyValue:
    nhl_player_id: int
    full_name: str
    player_type: str
    season_id: int
    games_played: int

    fantasy_points: float
    fantasy_points_per_game: float | None

    components: tuple[
        FantasyPointComponent,
        ...,
    ]
