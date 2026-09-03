from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date

from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.rookie_projection import (
    RookieSkaterProjection,
    RookieSkaterProjectionModel,
)
from hockey_rmt.domain.skater_bio import (
    SkaterBio,
)


AGE_CENTER = 22.0
UNDRAFTED_EFFECTIVE_PICK = 250


class RookieProjectionError(
    RuntimeError
):
    """Rookie-skater projection failed."""


def season_reference_date(
    season_id: int,
) -> date:
    start_year = (
        int(season_id)
        // 10000
    )

    return date(
        start_year,
        10,
        1,
    )


def age_on(
    birth_date: date,
    reference_date: date,
) -> float:
    if reference_date <= birth_date:
        raise RookieProjectionError(
            "Projection reference date "
            "must be after birth date."
        )

    return (
        reference_date
        - birth_date
    ).days / 365.2425


def effective_draft_pick(
    draft_overall: int | None,
) -> int:
    if draft_overall is None:
        return (
            UNDRAFTED_EFFECTIVE_PICK
        )

    pick = int(
        draft_overall
    )

    if pick <= 0:
        raise RookieProjectionError(
            "Draft overall pick must "
            "be positive."
        )

    return pick


def _features(
    *,
    player_age: float,
    draft_overall: int | None,
) -> tuple[
    float,
    float,
    float,
]:
    pick = effective_draft_pick(
        draft_overall
    )

    return (
        1.0,
        player_age - AGE_CENTER,
        1.0 / math.sqrt(
            float(pick)
        ),
    )


def _solve_linear_system(
    matrix: Sequence[
        Sequence[float]
    ],
    vector: Sequence[float],
) -> tuple[float, ...]:
    n = len(vector)

    if (
        n == 0
        or len(matrix) != n
        or any(
            len(row) != n
            for row in matrix
        )
    ):
        raise RookieProjectionError(
            "Regression matrix dimensions "
            "were invalid."
        )

    augmented = [
        [
            float(value)
            for value in matrix[row]
        ]
        + [
            float(vector[row])
        ]
        for row in range(n)
    ]

    for column in range(n):
        pivot = max(
            range(
                column,
                n,
            ),
            key=lambda row: abs(
                augmented[row][
                    column
                ]
            ),
        )

        if abs(
            augmented[pivot][
                column
            ]
        ) < 1e-10:
            raise RookieProjectionError(
                "Regression matrix "
                "was singular."
            )

        (
            augmented[column],
            augmented[pivot],
        ) = (
            augmented[pivot],
            augmented[column],
        )

        divisor = augmented[
            column
        ][column]

        augmented[column] = [
            value / divisor
            for value in augmented[
                column
            ]
        ]

        for row in range(n):
            if row == column:
                continue

            factor = augmented[
                row
            ][column]

            augmented[row] = [
                current
                - factor
                * pivot_value
                for (
                    current,
                    pivot_value,
                ) in zip(
                    augmented[row],
                    augmented[column],
                )
            ]

    return tuple(
        augmented[row][-1]
        for row in range(n)
    )


def _fit_ols(
    *,
    feature_rows: Sequence[
        tuple[
            float,
            float,
            float,
        ]
    ],
    targets: Sequence[float],
) -> tuple[
    float,
    float,
    float,
]:
    if not feature_rows:
        raise RookieProjectionError(
            "No rookie training rows "
            "were supplied."
        )

    if (
        len(feature_rows)
        != len(targets)
    ):
        raise RookieProjectionError(
            "Rookie training feature "
            "and target counts differed."
        )

    width = 3

    matrix = [
        [
            sum(
                row[i] * row[j]
                for row in feature_rows
            )
            for j in range(width)
        ]
        for i in range(width)
    ]

    vector = [
        sum(
            row[i] * target
            for row, target
            in zip(
                feature_rows,
                targets,
            )
        )
        for i in range(width)
    ]

    result = _solve_linear_system(
        matrix,
        vector,
    )

    if len(result) != 3:
        raise RookieProjectionError(
            "Unexpected rookie regression "
            "coefficient count."
        )

    return (
        result[0],
        result[1],
        result[2],
    )


def fit_rookie_skater_projection_model(
    *,
    training_season_ids: Sequence[int],
    actual_values_by_season: Mapping[
        int,
        Sequence[
            HistoricalFantasyValue
        ],
    ],
    bios_by_season: Mapping[
        int,
        Sequence[
            SkaterBio
        ],
    ],
    minimum_games: int = 20,
) -> RookieSkaterProjectionModel:
    seasons = tuple(
        int(season_id)
        for season_id
        in training_season_ids
    )

    if not seasons:
        raise RookieProjectionError(
            "At least one rookie training "
            "season is required."
        )

    if minimum_games <= 0:
        raise RookieProjectionError(
            "minimum_games must "
            "be positive."
        )

    feature_rows = []
    targets = []

    for season_id in seasons:
        actual_values = (
            actual_values_by_season.get(
                season_id
            )
        )

        bios = (
            bios_by_season.get(
                season_id
            )
        )

        if actual_values is None:
            raise RookieProjectionError(
                "Missing rookie actual values "
                f"for season {season_id}."
            )

        if bios is None:
            raise RookieProjectionError(
                "Missing rookie bios "
                f"for season {season_id}."
            )

        actual_by_id = {}

        for actual in actual_values:
            if (
                actual.player_type
                != "skater"
            ):
                continue

            if (
                actual.season_id
                != season_id
            ):
                raise RookieProjectionError(
                    "Historical rookie actual "
                    "season mismatch."
                )

            if (
                actual.nhl_player_id
                in actual_by_id
            ):
                raise RookieProjectionError(
                    "Duplicate rookie actual "
                    "NHL playerId "
                    f"{actual.nhl_player_id}."
                )

            actual_by_id[
                actual.nhl_player_id
            ] = actual

        reference_date = (
            season_reference_date(
                season_id
            )
        )

        seen_bio_ids = set()

        for bio in bios:
            if (
                bio.nhl_player_id
                in seen_bio_ids
            ):
                raise RookieProjectionError(
                    "Duplicate rookie bio "
                    "NHL playerId "
                    f"{bio.nhl_player_id}."
                )

            seen_bio_ids.add(
                bio.nhl_player_id
            )

            if (
                bio.first_season_for_game_type
                != season_id
            ):
                continue

            actual = actual_by_id.get(
                bio.nhl_player_id
            )

            if actual is None:
                continue

            if (
                actual.games_played
                < minimum_games
            ):
                continue

            if (
                actual.fantasy_points_per_game
                is None
            ):
                continue

            player_age = age_on(
                bio.birth_date,
                reference_date,
            )

            feature_rows.append(
                _features(
                    player_age=player_age,
                    draft_overall=(
                        bio.draft_overall
                    ),
                )
            )

            targets.append(
                actual
                .fantasy_points_per_game
            )

    (
        intercept,
        age_coefficient,
        draft_coefficient,
    ) = _fit_ols(
        feature_rows=feature_rows,
        targets=targets,
    )

    return RookieSkaterProjectionModel(
        training_season_ids=seasons,
        training_player_count=(
            len(feature_rows)
        ),
        minimum_training_games=(
            minimum_games
        ),
        intercept=intercept,
        age_coefficient=(
            age_coefficient
        ),
        inverse_sqrt_draft_coefficient=(
            draft_coefficient
        ),
        age_center=AGE_CENTER,
        undrafted_effective_pick=(
            UNDRAFTED_EFFECTIVE_PICK
        ),
    )


def project_rookie_skater(
    *,
    nhl_player_id: int,
    full_name: str,
    birth_date: date,
    draft_overall: int | None,
    projection_season_id: int,
    model: RookieSkaterProjectionModel,
) -> RookieSkaterProjection:
    reference_date = (
        season_reference_date(
            projection_season_id
        )
    )

    player_age = age_on(
        birth_date,
        reference_date,
    )

    pick = effective_draft_pick(
        draft_overall
    )

    age_adjustment = (
        model.age_coefficient
        * (
            player_age
            - model.age_center
        )
    )

    draft_adjustment = (
        model
        .inverse_sqrt_draft_coefficient
        * (
            1.0
            / math.sqrt(
                float(pick)
            )
        )
    )

    projected_rate = (
        model.intercept
        + age_adjustment
        + draft_adjustment
    )

    return RookieSkaterProjection(
        nhl_player_id=int(
            nhl_player_id
        ),
        full_name=str(
            full_name
        ),
        player_age=player_age,
        draft_overall=(
            None
            if draft_overall is None
            else int(
                draft_overall
            )
        ),
        effective_draft_pick=pick,
        intercept_component=(
            model.intercept
        ),
        age_adjustment=(
            age_adjustment
        ),
        draft_adjustment=(
            draft_adjustment
        ),
        projected_fantasy_points_per_game=(
            projected_rate
        ),
    )
