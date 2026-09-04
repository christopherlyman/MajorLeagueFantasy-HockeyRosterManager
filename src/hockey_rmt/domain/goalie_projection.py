from __future__ import annotations

from dataclasses import dataclass


QUALITY_HISTORICAL_RATE = (
    "historical_rate"
)

QUALITY_POPULATION_PRIOR = (
    "population_prior"
)

WORKLOAD_EXTERNAL_PROJECTED = (
    "external_projected"
)

WORKLOAD_EXTERNAL_IMPLIED_ZERO = (
    "external_implied_zero"
)

WORKLOAD_NO_CURRENT_NHL_ROSTER = (
    "no_current_nhl_roster"
)

WORKLOAD_INTERNAL_FALLBACK = (
    "internal_fallback"
)

WORKLOAD_IDENTITY_UNRESOLVED = (
    "identity_unresolved"
)


@dataclass(frozen=True)
class PreseasonGoalieProjection:
    provider_player_key: str
    full_name: str

    projection_season_id: int

    nhl_player_id: int | None
    nhl_team_abbr: str | None

    quality_state: str | None
    projected_fantasy_points_per_game: (
        float | None
    )

    historical_games_played: int
    historical_seasons_used: int

    workload_state: str
    workload_source: str | None
    projected_games_started: float | None

    projected_start_based_fantasy_points: (
        float | None
    )
