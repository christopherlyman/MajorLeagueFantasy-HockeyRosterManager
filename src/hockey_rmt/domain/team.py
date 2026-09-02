from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FantasyTeam:
    provider: str
    provider_team_key: str
    provider_team_id: str
    name: str

    is_owned_by_current_user: bool

    waiver_priority: int | None
    weekly_adds_used: int | None
