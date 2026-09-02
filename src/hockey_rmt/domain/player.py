from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    provider: str
    provider_player_key: str
    provider_player_id: str

    full_name: str

    nhl_team_key: str | None
    nhl_team_name: str | None
    nhl_team_abbr: str | None

    position_type: str
    primary_position: str
    eligible_positions: tuple[str, ...]

    status: str | None
    status_full: str | None

    is_undroppable: bool
