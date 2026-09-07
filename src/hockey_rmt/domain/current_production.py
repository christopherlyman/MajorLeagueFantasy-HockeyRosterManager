from __future__ import annotations

from dataclasses import dataclass

from hockey_rmt.domain.player_stats import (
    FantasyPointComponent,
)


CURRENT_PRODUCTION_SOURCE_OFFICIAL_NHL = (
    "official_nhl_stats"
)

CURRENT_PRODUCTION_AVAILABLE = (
    "available"
)

CURRENT_PRODUCTION_NO_SAMPLE = (
    "no_sample"
)

CURRENT_PRODUCTION_IDENTITY_UNRESOLVED = (
    "identity_unresolved"
)


@dataclass(frozen=True)
class CurrentSeasonProduction:
    provider_player_key: str
    full_name: str

    season_id: int
    player_type: str

    nhl_player_id: int | None

    production_state: str
    production_source: str

    games_played: int

    fantasy_points: float | None
    fantasy_points_per_game: float | None

    components: tuple[
        FantasyPointComponent,
        ...,
    ] | None
