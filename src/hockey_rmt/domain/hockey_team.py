from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HockeyTeam:
    provider: str
    provider_team_key: str | None
    name: str
    abbreviation: str


@dataclass(frozen=True)
class TeamIdentityCrosswalk:
    source_provider: str
    source_team_key: str
    source_team_abbr: str

    canonical_team_name: str
    canonical_team_abbr: str
