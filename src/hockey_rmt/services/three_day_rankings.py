from __future__ import annotations

import math

from collections.abc import (
    Mapping,
    Sequence,
)
from datetime import (
    date,
    timedelta,
)

from hockey_rmt.domain.daily_value import (
    DAILY_VALUE_AVAILABLE,
    DailyExpectedValue,
)
from hockey_rmt.domain.three_day_ranking import (
    RankedDayValue,
    ThreeDayPlayerRanking,
)


class ThreeDayRankingError(
    RuntimeError
):
    """Three-day ranking construction failed."""


def _finite_number(
    value: float,
    *,
    label: str,
) -> float:
    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        raise ThreeDayRankingError(
            f"{label} must be finite: "
            f"{value!r}."
        )

    return result


def _index_daily_values(
    rows: Sequence[
        DailyExpectedValue
    ],
    *,
    expected_date: date,
) -> tuple[
    dict[
        str,
        DailyExpectedValue,
    ],
    tuple[
        str,
        ...,
    ],
]:
    result = {}
    order = []

    for row in rows:
        key = str(
            row.provider_player_key
        )

        if key in result:
            raise ThreeDayRankingError(
                "Daily-value input contained "
                "duplicate provider player key "
                f"{key!r} for "
                f"{expected_date.isoformat()}."
            )

        if row.game_date != expected_date:
            raise ThreeDayRankingError(
                "Daily-value date mismatch for "
                f"{key!r}: "
                f"{row.game_date.isoformat()} "
                f"!= {expected_date.isoformat()}."
            )

        if (
            row.expected_fantasy_points
            is not None
        ):
            _finite_number(
                row.expected_fantasy_points,
                label=(
                    "Daily expected fantasy "
                    f"points for {key!r}"
                ),
            )

        result[
            key
        ] = row

        order.append(
            key
        )

    return (
        result,
        tuple(
            order
        ),
    )


def _daily_ranks(
    rows: Mapping[
        str,
        DailyExpectedValue,
    ],
) -> dict[
    str,
    int,
]:
    rankable = []

    for key, row in rows.items():
        if (
            row.value_state
            != DAILY_VALUE_AVAILABLE
        ):
            continue

        if (
            row.expected_fantasy_points
            is None
        ):
            raise ThreeDayRankingError(
                "Available daily value had null "
                "expected fantasy points for "
                f"{key!r}."
            )

        expected = (
            _finite_number(
                row.expected_fantasy_points,
                label=(
                    "Available daily expected "
                    f"fantasy points for {key!r}"
                ),
            )
        )

        baseline = (
            float(
                row
                .baseline_fantasy_points_per_game
            )
            if (
                row
                .baseline_fantasy_points_per_game
                is not None
            )
            else -1.0
        )

        rankable.append(
            (
                key,
                expected,
                baseline,
                row.full_name,
            )
        )

    rankable.sort(
        key=lambda item: (
            -item[1],
            -item[2],
            item[3].casefold(),
            item[0],
        )
    )

    return {
        key: rank
        for rank, (
            key,
            _,
            _,
            _,
        )
        in enumerate(
            rankable,
            start=1,
        )
    }


def _ranked_day(
    row: DailyExpectedValue,
    rank: int | None,
) -> RankedDayValue:
    return RankedDayValue(
        game_date=(
            row.game_date
        ),
        nhl_team_abbr=(
            row.nhl_team_abbr
        ),
        schedule_state=(
            row.schedule_state
        ),
        value_state=(
            row.value_state
        ),
        expected_fantasy_points=(
            float(
                row.expected_fantasy_points
            )
            if (
                row.expected_fantasy_points
                is not None
            )
            else None
        ),
        daily_rank=(
            rank
        ),
        opponent_team_abbr=(
            row.opponent_team_abbr
        ),
        home_away=(
            row.home_away
        ),
        provider_game_id=(
            row.provider_game_id
        ),
    )


def build_three_day_player_rankings(
    *,
    daily_values_by_date: Mapping[
        date,
        Sequence[
            DailyExpectedValue
        ],
    ],
    base_date: date,
) -> tuple[
    ThreeDayPlayerRanking,
    ...,
]:
    dates = (
        base_date,
        base_date
        + timedelta(
            days=1
        ),
        base_date
        + timedelta(
            days=2
        ),
    )

    supplied_dates = set(
        daily_values_by_date
    )

    required_dates = set(
        dates
    )

    if supplied_dates != required_dates:
        raise ThreeDayRankingError(
            "Three-day ranking requires exactly "
            "Today, Tomorrow, and Day+2: "
            f"missing="
            f"{sorted(required_dates - supplied_dates)!r}, "
            f"extra="
            f"{sorted(supplied_dates - required_dates)!r}."
        )

    indexed = {}
    first_order = None
    expected_keys = None

    for game_date in dates:
        rows, order = (
            _index_daily_values(
                daily_values_by_date[
                    game_date
                ],
                expected_date=(
                    game_date
                ),
            )
        )

        keys = set(
            rows
        )

        if expected_keys is None:
            expected_keys = keys
            first_order = order

        elif keys != expected_keys:
            raise ThreeDayRankingError(
                "Provider-player coverage differed "
                "between three-day dates for "
                f"{game_date.isoformat()}."
            )

        indexed[
            game_date
        ] = rows

    if first_order is None:
        return ()

    ranks_by_date = {
        game_date: _daily_ranks(
            indexed[
                game_date
            ]
        )
        for game_date
        in dates
    }

    provisional = []

    for key in first_order:
        day_rows = tuple(
            indexed[
                game_date
            ][
                key
            ]
            for game_date
            in dates
        )

        reference = (
            day_rows[0]
        )

        for row in day_rows[1:]:
            if (
                row.full_name
                != reference.full_name
            ):
                raise ThreeDayRankingError(
                    "Player name changed within "
                    "three-day window for "
                    f"{key!r}."
                )

            if (
                row.season_id
                != reference.season_id
            ):
                raise ThreeDayRankingError(
                    "Season changed within "
                    "three-day window for "
                    f"{key!r}."
                )

            if (
                row.player_type
                != reference.player_type
            ):
                raise ThreeDayRankingError(
                    "Player type changed within "
                    "three-day window for "
                    f"{key!r}."
                )

            if (
                row.nhl_player_id
                != reference.nhl_player_id
            ):
                raise ThreeDayRankingError(
                    "NHL player identity changed "
                    "within three-day window for "
                    f"{key!r}."
                )

        daily_cells = tuple(
            _ranked_day(
                row,
                ranks_by_date[
                    row.game_date
                ].get(
                    key
                ),
            )
            for row
            in day_rows
        )

        expected_values = [
            row.expected_fantasy_points
            for row
            in day_rows
        ]

        if all(
            value is not None
            for value
            in expected_values
        ):
            three_day_expected = sum(
                float(
                    value
                )
                for value
                in expected_values
            )
        else:
            three_day_expected = None

        scheduled_games = sum(
            1
            for row
            in day_rows
            if (
                row.schedule_state
                == "scheduled"
            )
        )

        provisional.append(
            {
                "key": key,
                "reference": reference,
                "cells": daily_cells,
                "scheduled_games": (
                    scheduled_games
                ),
                "three_day_expected": (
                    three_day_expected
                ),
            }
        )

    rankable_totals = [
        row
        for row
        in provisional
        if (
            row[
                "three_day_expected"
            ]
            is not None
        )
    ]

    rankable_totals.sort(
        key=lambda row: (
            -float(
                row[
                    "three_day_expected"
                ]
            ),
            -row[
                "scheduled_games"
            ],
            row[
                "reference"
            ].full_name.casefold(),
            row[
                "key"
            ],
        )
    )

    three_day_rank_by_key = {
        row[
            "key"
        ]: rank
        for rank, row
        in enumerate(
            rankable_totals,
            start=1,
        )
    }

    result = []

    for row in provisional:
        reference = row[
            "reference"
        ]

        today, tomorrow, day_plus_2 = (
            row[
                "cells"
            ]
        )

        result.append(
            ThreeDayPlayerRanking(
                provider_player_key=(
                    row[
                        "key"
                    ]
                ),
                full_name=(
                    reference.full_name
                ),
                season_id=(
                    reference.season_id
                ),
                player_type=(
                    reference.player_type
                ),
                nhl_player_id=(
                    reference.nhl_player_id
                ),
                base_date=(
                    base_date
                ),
                today=(
                    today
                ),
                tomorrow=(
                    tomorrow
                ),
                day_plus_2=(
                    day_plus_2
                ),
                scheduled_games=(
                    row[
                        "scheduled_games"
                    ]
                ),
                three_day_expected_fantasy_points=(
                    row[
                        "three_day_expected"
                    ]
                ),
                three_day_rank=(
                    three_day_rank_by_key.get(
                        row[
                            "key"
                        ]
                    )
                ),
            )
        )

    if (
        len(result)
        != len(
            first_order
        )
    ):
        raise ThreeDayRankingError(
            "Three-day result count changed "
            "during ranking."
        )

    return tuple(
        result
    )
