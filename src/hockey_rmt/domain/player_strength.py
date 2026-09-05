from __future__ import annotations

from dataclasses import dataclass


STRENGTH_AVAILABLE = "available"
STRENGTH_IDENTITY_UNRESOLVED = (
    "identity_unresolved"
)
STRENGTH_NO_PROJECTION = "no_projection"


SOURCE_ESTABLISHED_SKATER = (
    "established_skater"
)
SOURCE_ROOKIE_SKATER = (
    "rookie_skater"
)
SOURCE_LONG_ABSENCE_SKATER = (
    "long_absence_skater"
)
SOURCE_GOALIE_QUALITY = (
    "goalie_quality"
)


@dataclass(frozen=True)
class PlayerStrengthProjection:
    provider_player_key: str
    full_name: str

    projection_season_id: int
    player_type: str

    nhl_player_id: int | None

    strength_state: str
    projection_source: str | None
    source_state: str | None

    projected_fantasy_points_per_game: (
        float | None
    )
