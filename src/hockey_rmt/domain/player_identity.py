from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NhlPlayerIdentity:
    nhl_player_id: int
    full_name: str
    position: str | None
    team_abbr: str | None
    active: bool | None
    last_season_id: int | None


@dataclass(frozen=True)
class PlayerIdentityResolution:
    provider_player_key: str

    resolution_state: str
    resolution_method: str | None

    nhl_player_id: int | None
    nhl_full_name: str | None
    nhl_position: str | None
    nhl_team_abbr: str | None
