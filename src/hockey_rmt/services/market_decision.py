from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from dataclasses import replace
import math

from hockey_rmt.domain.lineup_decision import (
    ACTION_START,
)
from hockey_rmt.domain.market_decision import (
    MARKET_ACTION_ADD,
    MARKET_ACTION_DROP,
    MARKET_ACTION_HOLD,
    MARKET_ACTION_STREAM,
    MarketDecisionResult,
    MarketRecommendation,
)
from hockey_rmt.services.lineup_optimizer import (
    build_daily_lineup_decisions,
)


class MarketDecisionError(
    RuntimeError
):
    """Market transaction evaluation failed."""


DAY_KEYS = (
    "today",
    "tomorrow",
    "day_plus_2",
)

MINIMUM_USABLE_GAIN = 0.50
ADD_PER_GAME_ADVANTAGE = 0.05

OVERALL_CANDIDATE_LIMIT = 200
PER_POSITION_CANDIDATE_LIMIT = 50


def _player_key(
    row: Mapping,
) -> str:
    return str(
        row.get(
            "provider_player_key",
            "",
        )
    ).strip()


def _player_name(
    row: Mapping,
) -> str:
    return str(
        row.get(
            "full_name",
            "",
        )
    ).strip()


def _player_type(
    row: Mapping,
) -> str:
    value = str(
        row.get(
            "player_type",
            "",
        )
    ).strip().casefold()

    if value in {
        "g",
        "goalie",
    }:
        return "G"

    return "P"


def _finite_float(
    value,
    *,
    default: float = 0.0,
) -> float:
    if (
        value is None
        or isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):
        return default

    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        return default

    return result


def _scheduled_games(
    row: Mapping,
) -> int:
    value = row.get(
        "scheduled_games"
    )

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
    ):
        return 0

    return value


def _three_day_value(
    row: Mapping,
) -> float:
    return _finite_float(
        row.get(
            "three_day_expected_points"
        )
    )


def _per_game_value(
    row: Mapping,
) -> float | None:
    games = _scheduled_games(
        row
    )

    if games <= 0:
        return None

    return (
        _three_day_value(
            row
        )
        / games
    )


def _percent_rostered(
    row: Mapping,
) -> int | None:
    value = row.get(
        "percent_rostered"
    )

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
        or value > 100
    ):
        return None

    return value


def _eligible_positions(
    row: Mapping,
) -> tuple[
    str,
    ...,
]:
    values = row.get(
        "eligible_positions"
    )

    if not isinstance(
        values,
        (list, tuple),
    ):
        return ()

    return tuple(
        str(value).strip()
        for value in values
        if str(value).strip()
    )


def _usable_three_day_points(
    *,
    managed_rows: Sequence[
        Mapping
    ],
    roster_positions,
) -> float:
    total = 0.0

    for day_key in DAY_KEYS:
        decisions = (
            build_daily_lineup_decisions(
                rows=managed_rows,
                roster_positions=(
                    roster_positions
                ),
                day_key=day_key,
            )
        )

        for decision in decisions:
            if (
                decision.action
                == ACTION_START
                and decision.expected_points
                is not None
            ):
                total += float(
                    decision.expected_points
                )

    return total


def _starting_skater_positions(
    roster_positions,
) -> tuple[
    str,
    ...,
]:
    result = []

    for row in roster_positions:
        if isinstance(
            row,
            Mapping,
        ):
            position = str(
                row.get(
                    "position",
                    "",
                )
            ).strip()

            starting = (
                row.get(
                    "is_starting"
                )
                is True
            )

            position_type = str(
                row.get(
                    "position_type",
                    "",
                )
                or ""
            ).strip().casefold()

        else:
            position = str(
                getattr(
                    row,
                    "position",
                    "",
                )
            ).strip()

            starting = (
                getattr(
                    row,
                    "is_starting",
                    False,
                )
                is True
            )

            position_type = str(
                getattr(
                    row,
                    "position_type",
                    "",
                )
                or ""
            ).strip().casefold()

        if (
            starting
            and position
            not in {
                "",
                "G",
                "BN",
                "IR",
                "IR+",
                "NA",
            }
            and position_type != "g"
        ):
            result.append(
                position
            )

    return tuple(
        sorted(
            set(result)
        )
    )


def _candidate_sort_key(
    row: Mapping,
):
    rank = row.get(
        "three_day_rank"
    )

    if (
        isinstance(
            rank,
            bool,
        )
        or not isinstance(
            rank,
            int,
        )
    ):
        rank = 10**9

    return (
        -_three_day_value(
            row
        ),
        rank,
        _player_name(
            row
        ).casefold(),
        _player_key(
            row
        ),
    )


def _candidate_pool(
    *,
    rows: Sequence[
        Mapping
    ],
    roster_positions,
) -> tuple[
    Mapping,
    ...,
]:
    starting_positions = (
        _starting_skater_positions(
            roster_positions
        )
    )

    eligible = []

    for row in rows:
        if (
            str(
                row.get(
                    "market_state",
                    "",
                )
            ).strip().casefold()
            != "free_agent"
        ):
            continue

        if _player_type(
            row
        ) == "G":
            continue

        if (
            str(
                row.get(
                    "availability_state",
                    "available",
                )
            ).strip().casefold()
            == "unavailable"
        ):
            continue

        if _three_day_value(
            row
        ) <= 0.0:
            continue

        positions = set(
            _eligible_positions(
                row
            )
        )

        if not positions.intersection(
            starting_positions
        ):
            continue

        eligible.append(
            row
        )

    ordered = sorted(
        eligible,
        key=_candidate_sort_key,
    )

    selected = {}

    for row in ordered[
        :OVERALL_CANDIDATE_LIMIT
    ]:
        selected[
            _player_key(
                row
            )
        ] = row

    for position in starting_positions:
        position_rows = [
            row
            for row in ordered
            if position
            in _eligible_positions(
                row
            )
        ]

        for row in position_rows[
            :PER_POSITION_CANDIDATE_LIMIT
        ]:
            selected[
                _player_key(
                    row
                )
            ] = row

    return tuple(
        sorted(
            selected.values(),
            key=_candidate_sort_key,
        )
    )


def _validate_weekly_adds(
    *,
    max_weekly_adds: int | None,
    weekly_adds_used: int | None,
) -> tuple[
    str | None,
    int | None,
]:
    if max_weekly_adds is None:
        if (
            weekly_adds_used is not None
            and (
                isinstance(
                    weekly_adds_used,
                    bool,
                )
                or not isinstance(
                    weekly_adds_used,
                    int,
                )
                or weekly_adds_used < 0
            )
        ):
            raise MarketDecisionError(
                "weekly_adds_used must be "
                "a nonnegative integer or null."
            )

        return (
            None,
            None,
        )

    if (
        isinstance(
            max_weekly_adds,
            bool,
        )
        or not isinstance(
            max_weekly_adds,
            int,
        )
        or max_weekly_adds < 0
    ):
        raise MarketDecisionError(
            "max_weekly_adds must be "
            "a nonnegative integer or null."
        )

    if weekly_adds_used is None:
        return (
            "weekly_add_usage_unknown",
            None,
        )

    if (
        isinstance(
            weekly_adds_used,
            bool,
        )
        or not isinstance(
            weekly_adds_used,
            int,
        )
        or weekly_adds_used < 0
    ):
        raise MarketDecisionError(
            "weekly_adds_used must be "
            "a nonnegative integer or null."
        )

    remaining = max(
        0,
        max_weekly_adds
        - weekly_adds_used,
    )

    if remaining <= 0:
        return (
            "weekly_add_limit_reached",
            0,
        )

    return (
        None,
        remaining,
    )


def build_market_decisions(
    *,
    rows: Sequence[
        Mapping
    ],
    roster_positions,
    is_undroppable_by_player_key: Mapping[
        str,
        bool,
    ],
    max_weekly_adds: int | None,
    weekly_adds_used: int | None,
    recommendation_limit: int = 20,
) -> MarketDecisionResult:
    if recommendation_limit <= 0:
        raise MarketDecisionError(
            "recommendation_limit must be positive."
        )

    row_keys = [
        _player_key(
            row
        )
        for row in rows
    ]

    if any(
        not key
        for key in row_keys
    ):
        raise MarketDecisionError(
            "Market rows contained blank player keys."
        )

    if len(row_keys) != len(
        set(row_keys)
    ):
        raise MarketDecisionError(
            "Market rows contained duplicate player keys."
        )

    limit_state, remaining = (
        _validate_weekly_adds(
            max_weekly_adds=(
                max_weekly_adds
            ),
            weekly_adds_used=(
                weekly_adds_used
            ),
        )
    )

    managed_rows = tuple(
        row
        for row in rows
        if (
            row.get(
                "is_on_managed_team"
            )
            is True
        )
    )

    baseline = (
        _usable_three_day_points(
            managed_rows=managed_rows,
            roster_positions=(
                roster_positions
            ),
        )
        if managed_rows
        else 0.0
    )

    waiver_candidates_skipped = sum(
        1
        for row in rows
        if (
            str(
                row.get(
                    "market_state",
                    "",
                )
            ).strip().casefold()
            == "waiver"
            and _player_type(
                row
            )
            != "G"
        )
    )

    if not managed_rows:
        return MarketDecisionResult(
            state="waiting_for_managed_roster",
            overall_action=MARKET_ACTION_HOLD,
            baseline_usable_points=baseline,
            weekly_adds_remaining=remaining,
            candidate_pool_count=0,
            waiver_candidates_skipped=(
                waiver_candidates_skipped
            ),
            droppable_skater_count=0,
            recommendations=(),
        )

    if limit_state is not None:
        return MarketDecisionResult(
            state=limit_state,
            overall_action=MARKET_ACTION_HOLD,
            baseline_usable_points=baseline,
            weekly_adds_remaining=remaining,
            candidate_pool_count=0,
            waiver_candidates_skipped=(
                waiver_candidates_skipped
            ),
            droppable_skater_count=0,
            recommendations=(),
        )

    droppable_rows = []

    for row in managed_rows:
        if _player_type(
            row
        ) == "G":
            continue

        key = _player_key(
            row
        )

        if key not in (
            is_undroppable_by_player_key
        ):
            raise MarketDecisionError(
                "Missing is_undroppable state for "
                f"managed player {key!r}."
            )

        if (
            is_undroppable_by_player_key[
                key
            ]
            is True
        ):
            continue

        droppable_rows.append(
            row
        )

    if not droppable_rows:
        return MarketDecisionResult(
            state="no_droppable_skaters",
            overall_action=MARKET_ACTION_HOLD,
            baseline_usable_points=baseline,
            weekly_adds_remaining=remaining,
            candidate_pool_count=0,
            waiver_candidates_skipped=(
                waiver_candidates_skipped
            ),
            droppable_skater_count=0,
            recommendations=(),
        )

    candidate_rows = (
        _candidate_pool(
            rows=rows,
            roster_positions=(
                roster_positions
            ),
        )
    )

    if not candidate_rows:
        return MarketDecisionResult(
            state="no_actionable_free_agents",
            overall_action=MARKET_ACTION_HOLD,
            baseline_usable_points=baseline,
            weekly_adds_remaining=remaining,
            candidate_pool_count=0,
            waiver_candidates_skipped=(
                waiver_candidates_skipped
            ),
            droppable_skater_count=len(
                droppable_rows
            ),
            recommendations=(),
        )

    best_by_add_key = {}

    managed_without_by_drop = {
        _player_key(
            drop_row
        ): tuple(
            row
            for row in managed_rows
            if _player_key(
                row
            )
            != _player_key(
                drop_row
            )
        )
        for drop_row in droppable_rows
    }

    for add_row in candidate_rows:
        add_key = _player_key(
            add_row
        )

        add_name = _player_name(
            add_row
        )

        add_per_game = (
            _per_game_value(
                add_row
            )
        )

        add_value = (
            _three_day_value(
                add_row
            )
        )

        add_games = (
            _scheduled_games(
                add_row
            )
        )

        add_managed = dict(
            add_row
        )

        add_managed[
            "is_on_managed_team"
        ] = True

        best = None

        for drop_row in droppable_rows:
            drop_key = _player_key(
                drop_row
            )

            swapped = (
                managed_without_by_drop[
                    drop_key
                ]
                + (
                    add_managed,
                )
            )

            projected = (
                _usable_three_day_points(
                    managed_rows=swapped,
                    roster_positions=(
                        roster_positions
                    ),
                )
            )

            gain = (
                projected
                - baseline
            )

            if (
                gain
                + 1e-12
                < MINIMUM_USABLE_GAIN
            ):
                continue

            drop_per_game = (
                _per_game_value(
                    drop_row
                )
            )

            if (
                add_per_game is not None
                and drop_per_game is not None
                and (
                    add_per_game
                    >= (
                        drop_per_game
                        + ADD_PER_GAME_ADVANTAGE
                    )
                )
            ):
                action = (
                    MARKET_ACTION_ADD
                )

                reason = (
                    "per_game_upgrade_and_"
                    "usable_lineup_gain"
                )

            else:
                action = (
                    MARKET_ACTION_STREAM
                )

                reason = (
                    "near_term_schedule_or_"
                    "positional_fit_gain"
                )

            recommendation = (
                MarketRecommendation(
                    action=action,
                    add_player_key=add_key,
                    add_player_name=add_name,
                    drop_player_key=drop_key,
                    drop_player_name=(
                        _player_name(
                            drop_row
                        )
                    ),
                    usable_three_day_gain=(
                        gain
                    ),
                    baseline_usable_points=(
                        baseline
                    ),
                    projected_usable_points=(
                        projected
                    ),
                    add_three_day_expected_points=(
                        add_value
                    ),
                    drop_three_day_expected_points=(
                        _three_day_value(
                            drop_row
                        )
                    ),
                    add_scheduled_games=(
                        add_games
                    ),
                    drop_scheduled_games=(
                        _scheduled_games(
                            drop_row
                        )
                    ),
                    add_per_game_value=(
                        add_per_game
                    ),
                    drop_per_game_value=(
                        drop_per_game
                    ),
                    add_percent_rostered=(
                        _percent_rostered(
                            add_row
                        )
                    ),
                    reason=reason,
                )
            )

            if best is None:
                best = recommendation

            elif (
                recommendation
                .usable_three_day_gain
                > (
                    best
                    .usable_three_day_gain
                    + 1e-12
                )
            ):
                best = recommendation

            elif math.isclose(
                recommendation.usable_three_day_gain,
                best.usable_three_day_gain,
                rel_tol=0.0,
                abs_tol=1e-12,
            ) and (
                recommendation.drop_player_name.casefold(),
                recommendation.drop_player_key,
            ) < (
                best.drop_player_name.casefold(),
                best.drop_player_key,
            ):
                best = recommendation

        if best is not None:
            best_by_add_key[
                add_key
            ] = best

    recommendations = tuple(
        sorted(
            best_by_add_key.values(),
            key=lambda row: (
                -row.usable_three_day_gain,
                0
                if row.action
                == MARKET_ACTION_ADD
                else 1,
                row.add_player_name.casefold(),
                row.drop_player_name.casefold(),
                row.add_player_key,
                row.drop_player_key,
            ),
        )[
            :recommendation_limit
        ]
    )

    if not recommendations:
        state = (
            "hold_no_meaningful_upgrade"
        )

        overall_action = (
            MARKET_ACTION_HOLD
        )

    else:
        state = (
            "recommendations_available"
        )

        overall_action = (
            recommendations[
                0
            ].action
        )

    return MarketDecisionResult(
        state=state,
        overall_action=overall_action,
        baseline_usable_points=baseline,
        weekly_adds_remaining=remaining,
        candidate_pool_count=len(
            candidate_rows
        ),
        waiver_candidates_skipped=(
            waiver_candidates_skipped
        ),
        droppable_skater_count=len(
            droppable_rows
        ),
        recommendations=(
            recommendations
        ),
    )


def market_decision_result_payload(
    result: MarketDecisionResult,
) -> tuple[
    dict,
    list[
        dict,
    ],
]:
    context = {
        "state": result.state,
        "overall_action": (
            result.overall_action
        ),
        "baseline_usable_points": (
            result.baseline_usable_points
        ),
        "weekly_adds_remaining": (
            result.weekly_adds_remaining
        ),
        "candidate_pool_count": (
            result.candidate_pool_count
        ),
        "waiver_candidates_skipped": (
            result.waiver_candidates_skipped
        ),
        "droppable_skater_count": (
            result.droppable_skater_count
        ),
    }

    recommendations = [
        {
            "action": row.action,
            "drop_action": (
                MARKET_ACTION_DROP
            ),
            "add_player_key": (
                row.add_player_key
            ),
            "add_player_name": (
                row.add_player_name
            ),
            "drop_player_key": (
                row.drop_player_key
            ),
            "drop_player_name": (
                row.drop_player_name
            ),
            "usable_three_day_gain": (
                row.usable_three_day_gain
            ),
            "baseline_usable_points": (
                row.baseline_usable_points
            ),
            "projected_usable_points": (
                row.projected_usable_points
            ),
            "add_three_day_expected_points": (
                row.add_three_day_expected_points
            ),
            "drop_three_day_expected_points": (
                row.drop_three_day_expected_points
            ),
            "add_scheduled_games": (
                row.add_scheduled_games
            ),
            "drop_scheduled_games": (
                row.drop_scheduled_games
            ),
            "add_per_game_value": (
                row.add_per_game_value
            ),
            "drop_per_game_value": (
                row.drop_per_game_value
            ),
            "add_percent_rostered": (
                row.add_percent_rostered
            ),
            "reason": row.reason,
        }
        for row in result.recommendations
    ]

    return (
        context,
        recommendations,
    )
