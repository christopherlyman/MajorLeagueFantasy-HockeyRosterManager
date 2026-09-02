from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RosterPosition:
    position: str
    count: int
    is_starting: bool
    position_type: str | None = None


@dataclass(frozen=True)
class ScoringRule:
    source_stat_id: int
    name: str
    abbreviation: str
    group: str
    position_type: str
    points: float


@dataclass(frozen=True)
class LeagueDefinition:
    provider: str
    provider_league_key: str
    league_name: str
    sport: str
    season_year: int

    max_teams: int
    scoring_format: str
    roster_period: str
    lineup_deadline: str

    start_date: date
    end_date: date

    max_weekly_adds: int | None
    waiver_type: str
    waiver_rule: str
    waiver_days: int | None
    uses_faab: bool

    playoff_teams: int | None
    playoff_start_week: int | None

    roster_positions: tuple[RosterPosition, ...]
    scoring_rules: tuple[ScoringRule, ...]
