from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.projection import (
    HistoricalRateProjection,
)
from hockey_rmt.domain.skater_bio import (
    SkaterBio,
)
from hockey_rmt.domain.skater_projection import (
    CalibratedSkaterProjection,
    SkaterProjectionCalibration,
)


class SkaterProjectionError(RuntimeError):
    """Skater projection calibration failed."""


def age_on(
    birth_date: date,
    reference_date: date,
) -> float:
    if reference_date <= birth_date:
        raise SkaterProjectionError(
            "Projection reference date must be "
            "after player birth date."
        )

    return (
        reference_date - birth_date
    ).days / 365.2425


def season_reference_date(
    season_id: int,
) -> date:
    start_year = int(
        season_id
    ) // 10000

    return date(
        start_year,
        10,
        1,
    )


def fit_skater_projection_calibration(
    *,
    training_target_season_id: int,
    actual_values: Sequence[
        HistoricalFantasyValue
    ],
    baseline_projections: Sequence[
        HistoricalRateProjection
    ],
    bios: Sequence[
        SkaterBio
    ],
    minimum_games: int = 20,
) -> SkaterProjectionCalibration:
    if minimum_games <= 0:
        raise SkaterProjectionError(
            "minimum_games must be positive."
        )

    projection_by_id = {}

    for projection in baseline_projections:
        if projection.player_type != "skater":
            raise SkaterProjectionError(
                "Training baseline contained "
                "non-skater projection."
            )

        if (
            projection.nhl_player_id
            in projection_by_id
        ):
            raise SkaterProjectionError(
                "Duplicate training baseline NHL "
                f"playerId {projection.nhl_player_id}."
            )

        projection_by_id[
            projection.nhl_player_id
        ] = projection

    bio_by_id = {}

    for bio in bios:
        if bio.nhl_player_id in bio_by_id:
            raise SkaterProjectionError(
                "Duplicate skater bio NHL playerId "
                f"{bio.nhl_player_id}."
            )

        bio_by_id[
            bio.nhl_player_id
        ] = bio

    reference_date = season_reference_date(
        training_target_season_id
    )

    rows = []
    seen_actual_ids = set()

    for actual in actual_values:
        if actual.player_type != "skater":
            raise SkaterProjectionError(
                "Training actuals contained "
                "non-skater value."
            )

        if (
            actual.season_id
            != training_target_season_id
        ):
            raise SkaterProjectionError(
                "Training actual season did not "
                "match requested target season."
            )

        if actual.nhl_player_id in seen_actual_ids:
            raise SkaterProjectionError(
                "Duplicate training actual NHL "
                f"playerId {actual.nhl_player_id}."
            )

        seen_actual_ids.add(
            actual.nhl_player_id
        )

        if actual.games_played < minimum_games:
            continue

        if (
            actual.fantasy_points_per_game
            is None
        ):
            continue

        projection = projection_by_id.get(
            actual.nhl_player_id
        )

        bio = bio_by_id.get(
            actual.nhl_player_id
        )

        if projection is None or bio is None:
            continue

        baseline = (
            projection
            .projected_fantasy_points_per_game
        )

        if baseline is None:
            continue

        player_age = age_on(
            bio.birth_date,
            reference_date,
        )

        rows.append(
            (
                player_age,
                (
                    actual.fantasy_points_per_game
                    - baseline
                ),
            )
        )

    if len(rows) < 2:
        raise SkaterProjectionError(
            "Insufficient training rows for "
            "skater calibration."
        )

    mean_age = (
        sum(age for age, _ in rows)
        / len(rows)
    )

    mean_residual = (
        sum(
            residual
            for _, residual in rows
        )
        / len(rows)
    )

    numerator = sum(
        (
            age - mean_age
        )
        * (
            residual - mean_residual
        )
        for age, residual in rows
    )

    denominator = sum(
        (
            age - mean_age
        ) ** 2
        for age, _ in rows
    )

    if denominator <= 0:
        raise SkaterProjectionError(
            "Training age variance was zero."
        )

    return SkaterProjectionCalibration(
        training_target_season_id=(
            training_target_season_id
        ),
        training_player_count=len(rows),
        minimum_training_games=minimum_games,
        training_mean_age=mean_age,
        bias_adjustment=mean_residual,
        age_slope_per_year=(
            numerator / denominator
        ),
    )


def calibrate_skater_projection(
    *,
    baseline: HistoricalRateProjection,
    bio: SkaterBio,
    calibration: SkaterProjectionCalibration,
    projection_season_id: int,
) -> CalibratedSkaterProjection:
    if baseline.player_type != "skater":
        raise SkaterProjectionError(
            "Cannot apply skater calibration to "
            "non-skater baseline."
        )

    if (
        baseline.nhl_player_id
        != bio.nhl_player_id
    ):
        raise SkaterProjectionError(
            "Baseline and bio NHL playerId "
            "did not match."
        )

    baseline_rate = (
        baseline
        .projected_fantasy_points_per_game
    )

    if baseline_rate is None:
        raise SkaterProjectionError(
            "Historical baseline did not contain "
            "a projected FPPG."
        )

    reference_date = season_reference_date(
        projection_season_id
    )

    player_age = age_on(
        bio.birth_date,
        reference_date,
    )

    age_adjustment = (
        calibration.age_slope_per_year
        * (
            player_age
            - calibration.training_mean_age
        )
    )

    projected_rate = (
        baseline_rate
        + calibration.bias_adjustment
        + age_adjustment
    )

    return CalibratedSkaterProjection(
        nhl_player_id=baseline.nhl_player_id,
        full_name=baseline.full_name,
        historical_baseline_fppg=(
            baseline_rate
        ),
        player_age=player_age,
        calibration_bias_adjustment=(
            calibration.bias_adjustment
        ),
        age_adjustment=(
            age_adjustment
        ),
        projected_fantasy_points_per_game=(
            projected_rate
        ),
        historical_seasons_used=(
            baseline.historical_seasons_used
        ),
        historical_games_played=(
            baseline.historical_games_played
        ),
        effective_games_played=(
            baseline.effective_games_played
        ),
    )
