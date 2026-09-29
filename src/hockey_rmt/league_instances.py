from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LeagueOperationalConfig:
    """Season-specific rules absent from provider metadata."""

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


@dataclass(frozen=True)
class LeagueInstanceConfig:
    """Season-specific provider binding for a stable league."""

    logical_key: str
    display_name: str
    provider: str
    season_year: int
    provider_league_key: str
    managed_team_key: str
    competition_level: str | None = None
    operational: LeagueOperationalConfig | None = None


_LEAGUE_INSTANCES = {
    "nfhl_redraft": LeagueInstanceConfig(
        logical_key="nfhl_redraft",
        display_name="NFHL Redraft",
        provider="yahoo",
        season_year=2026,
        provider_league_key="477.l.10961",
        managed_team_key="477.l.10961.t.1",
    ),
    "oth_redraft": LeagueInstanceConfig(
        logical_key="oth_redraft",
        display_name="OTH Redraft",
        provider="fleaflicker",
        season_year=2026,
        provider_league_key="12090",
        managed_team_key="63197",
        competition_level="D3",
        operational=LeagueOperationalConfig(
            scoring_format="head_to_head_points",
            roster_period="daily",
            lineup_deadline="game_start",
            start_date=date(2026, 9, 29),
            end_date=date(2027, 4, 10),
            max_weekly_adds=7,
            waiver_type="rolling_priority",
            waiver_rule="all_players_after_game_start",
            waiver_days=1,
            uses_faab=False,
            playoff_teams=6,
            playoff_start_week=24,
        ),
    ),
}


def get_league_instance(
    logical_key: str,
) -> LeagueInstanceConfig:
    key = logical_key.strip()

    if not key:
        raise ValueError(
            "Logical league key must not be empty."
        )

    try:
        return _LEAGUE_INSTANCES[key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown logical league key {key!r}."
        ) from exc


def league_instance_keys() -> tuple[str, ...]:
    return tuple(_LEAGUE_INSTANCES)
