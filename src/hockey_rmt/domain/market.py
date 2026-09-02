from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerMarketState:
    provider: str
    provider_league_key: str
    provider_player_key: str

    market_state: str
    provider_ownership_type: str

    owner_team_key: str | None = None
    owner_team_name: str | None = None
