from __future__ import annotations

from dataclasses import dataclass


LONG_ABSENCE_POPULATION_PRIOR = (
    "long_absence_population_prior"
)


@dataclass(frozen=True)
class LongAbsenceSkaterProjection:
    nhl_player_id: int
    full_name: str

    projection_state: str

    projection_season_id: int
    population_source_season_id: int

    last_nhl_season_id: int
    absent_season_count: int

    population_mean_fantasy_points_per_game: float
    projected_fantasy_points_per_game: float
