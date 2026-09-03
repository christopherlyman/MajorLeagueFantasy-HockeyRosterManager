from __future__ import annotations

from collections.abc import Sequence

from hockey_rmt.domain.player_profile import (
    NhlPlayerProfile,
)
from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.returner_projection import (
    LONG_ABSENCE_POPULATION_PRIOR,
    LongAbsenceSkaterProjection,
)


class ReturnerProjectionError(
    RuntimeError
):
    """Long-absence skater projection failed."""


def _season_start_year(
    season_id: int,
) -> int:
    value = int(
        season_id
    )

    start_year = (
        value // 10000
    )

    end_year = (
        value % 10000
    )

    if end_year != start_year + 1:
        raise ReturnerProjectionError(
            "Invalid NHL season id "
            f"{season_id!r}."
        )

    return start_year


def skater_population_mean(
    *,
    historical_values: Sequence[
        HistoricalFantasyValue
    ],
    season_id: int,
) -> float:
    rates = []

    seen_player_ids = set()

    for value in historical_values:
        if (
            value.season_id
            != season_id
        ):
            raise ReturnerProjectionError(
                "Historical population value "
                "season mismatch."
            )

        if value.player_type != "skater":
            continue

        if (
            value.nhl_player_id
            in seen_player_ids
        ):
            raise ReturnerProjectionError(
                "Duplicate skater NHL playerId "
                f"{value.nhl_player_id}."
            )

        seen_player_ids.add(
            value.nhl_player_id
        )

        if (
            value.fantasy_points_per_game
            is None
        ):
            continue

        rates.append(
            float(
                value.fantasy_points_per_game
            )
        )

    if not rates:
        raise ReturnerProjectionError(
            "No skater population values "
            f"were available for {season_id}."
        )

    return (
        sum(rates)
        / len(rates)
    )


def project_long_absence_skater(
    *,
    nhl_player_id: int,
    full_name: str,
    profile: NhlPlayerProfile,
    projection_season_id: int,
    population_source_season_id: int,
    population_mean_fppg: float,
    minimum_absent_seasons: int = 3,
) -> LongAbsenceSkaterProjection:
    if (
        profile.nhl_player_id
        != int(nhl_player_id)
    ):
        raise ReturnerProjectionError(
            "Player profile NHL playerId "
            "did not match projection playerId."
        )

    if not (
        profile
        .has_nhl_regular_season_history
    ):
        raise ReturnerProjectionError(
            "Long-absence returner must have "
            "prior NHL regular-season history."
        )

    last_nhl_season_id = max(
        profile.nhl_regular_season_ids
    )

    projection_start = (
        _season_start_year(
            projection_season_id
        )
    )

    last_nhl_start = (
        _season_start_year(
            last_nhl_season_id
        )
    )

    absent_season_count = (
        projection_start
        - last_nhl_start
        - 1
    )

    if (
        absent_season_count
        < minimum_absent_seasons
    ):
        raise ReturnerProjectionError(
            "Player did not meet the "
            "long-absence threshold."
        )

    population_source_start = (
        _season_start_year(
            population_source_season_id
        )
    )

    if (
        population_source_start
        != projection_start - 1
    ):
        raise ReturnerProjectionError(
            "Population source season must "
            "be the immediately completed "
            "season before projection."
        )

    rate = float(
        population_mean_fppg
    )

    if rate <= 0:
        raise ReturnerProjectionError(
            "Population mean FPPG "
            "must be positive."
        )

    return LongAbsenceSkaterProjection(
        nhl_player_id=int(
            nhl_player_id
        ),
        full_name=str(
            full_name
        ),
        projection_state=(
            LONG_ABSENCE_POPULATION_PRIOR
        ),
        projection_season_id=int(
            projection_season_id
        ),
        population_source_season_id=int(
            population_source_season_id
        ),
        last_nhl_season_id=(
            last_nhl_season_id
        ),
        absent_season_count=(
            absent_season_count
        ),
        population_mean_fantasy_points_per_game=(
            rate
        ),
        projected_fantasy_points_per_game=(
            rate
        ),
    )
