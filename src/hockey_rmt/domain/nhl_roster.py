from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentNhlGoalie:
    nhl_player_id: int
    nhl_team_abbr: str
