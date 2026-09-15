from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from functools import lru_cache
import math

from hockey_rmt.domain.league import (
    RosterPosition,
)
from hockey_rmt.domain.lineup_decision import (
    ACTION_BENCH,
    ACTION_HOLD,
    ACTION_START,
    DailyLineupDecision,
)


class LineupOptimizerError(
    RuntimeError
):
    """Daily lineup optimization failed."""


_VALID_DAY_KEYS = {
    "today",
    "tomorrow",
    "day_plus_2",
}

_NON_STARTING_POSITION_NAMES = {
    "BN",
    "IR",
    "IR+",
    "NA",
}

_EPSILON = 1e-12


def _read_roster_position(
    row,
) -> tuple[
    str,
    int,
    bool,
    str | None,
]:
    if isinstance(
        row,
        Mapping,
    ):
        position = row.get(
            "position"
        )

        count = row.get(
            "count"
        )

        is_starting = row.get(
            "is_starting"
        )

        position_type = row.get(
            "position_type"
        )

    else:
        position = getattr(
            row,
            "position",
            None,
        )

        count = getattr(
            row,
            "count",
            None,
        )

        is_starting = getattr(
            row,
            "is_starting",
            None,
        )

        position_type = getattr(
            row,
            "position_type",
            None,
        )

    normalized_position = str(
        position
        or ""
    ).strip()

    if not normalized_position:
        raise LineupOptimizerError(
            "Roster position was blank."
        )

    if (
        isinstance(
            count,
            bool,
        )
        or not isinstance(
            count,
            int,
        )
        or count <= 0
    ):
        raise LineupOptimizerError(
            "Roster position count must be "
            "a positive integer for "
            f"{normalized_position!r}."
        )

    if not isinstance(
        is_starting,
        bool,
    ):
        raise LineupOptimizerError(
            "Roster position is_starting "
            "must be boolean for "
            f"{normalized_position!r}."
        )

    if position_type is None:
        normalized_type = None

    else:
        normalized_type = str(
            position_type
        ).strip() or None

    return (
        normalized_position,
        count,
        is_starting,
        normalized_type,
    )


def _normalize_roster_positions(
    roster_positions: Sequence[
        RosterPosition | Mapping
    ],
) -> tuple[
    tuple[
        str,
        int,
        bool,
        str | None,
    ],
    ...,
]:
    result = []

    seen = set()

    for row in roster_positions:
        normalized = (
            _read_roster_position(
                row
            )
        )

        position = normalized[0]

        if position in seen:
            raise LineupOptimizerError(
                "Roster position definition "
                "contained duplicate position "
                f"{position!r}."
            )

        seen.add(
            position
        )

        result.append(
            normalized
        )

    if not result:
        raise LineupOptimizerError(
            "Roster position definition was empty."
        )

    return tuple(
        result
    )


def build_roster_position_snapshot(
    roster_positions: Sequence[
        RosterPosition
    ],
) -> tuple[
    dict,
    ...,
]:
    normalized = (
        _normalize_roster_positions(
            roster_positions
        )
    )

    return tuple(
        {
            "position": position,
            "count": count,
            "is_starting": is_starting,
            "position_type": position_type,
        }
        for (
            position,
            count,
            is_starting,
            position_type,
        )
        in normalized
    )


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


def _day_expected_points(
    day: Mapping,
) -> float | None:
    value = day.get(
        "expected_fantasy_points"
    )

    if value is None:
        value = day.get(
            "expected_points"
        )

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
        return None

    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        return None

    return result


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

    cleaned = tuple(
        str(
            value
        ).strip()
        for value in values
        if str(
            value
        ).strip()
    )

    if len(
        cleaned
    ) != len(
        set(
            cleaned
        )
    ):
        raise LineupOptimizerError(
            "Player eligibility contained "
            "duplicate positions for "
            f"{row.get('provider_player_key')!r}."
        )

    return cleaned


def _better_solution(
    candidate: tuple[
        float,
        tuple[
            tuple[
                str,
                str,
            ],
            ...,
        ],
    ],
    current: tuple[
        float,
        tuple[
            tuple[
                str,
                str,
            ],
            ...,
        ],
    ],
):
    candidate_score = candidate[0]
    current_score = current[0]

    if (
        candidate_score
        > current_score
        + _EPSILON
    ):
        return candidate

    if (
        current_score
        > candidate_score
        + _EPSILON
    ):
        return current

    candidate_assignments = (
        candidate[1]
    )

    current_assignments = (
        current[1]
    )

    if (
        len(
            candidate_assignments
        )
        > len(
            current_assignments
        )
    ):
        return candidate

    if (
        len(
            current_assignments
        )
        > len(
            candidate_assignments
        )
    ):
        return current

    if (
        candidate_assignments
        < current_assignments
    ):
        return candidate

    return current


def build_daily_lineup_decisions(
    *,
    rows: Sequence[
        Mapping
    ],
    roster_positions: Sequence[
        RosterPosition | Mapping
    ],
    day_key: str,
) -> tuple[
    DailyLineupDecision,
    ...,
]:
    if day_key not in _VALID_DAY_KEYS:
        raise LineupOptimizerError(
            "day_key must be today, tomorrow, "
            "or day_plus_2."
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

    if not managed_rows:
        return ()

    normalized_positions = (
        _normalize_roster_positions(
            roster_positions
        )
    )

    starting_skater_slots = tuple(
        (
            position,
            count,
        )
        for (
            position,
            count,
            is_starting,
            position_type,
        )
        in normalized_positions
        if (
            is_starting
            and position
            not in _NON_STARTING_POSITION_NAMES
            and position != "G"
            and str(
                position_type
                or ""
            ).strip().casefold()
            != "g"
        )
    )

    seen_keys = set()

    player_context = {}
    candidates = []

    for row in managed_rows:
        key = str(
            row.get(
                "provider_player_key",
                "",
            )
        ).strip()

        if not key:
            raise LineupOptimizerError(
                "Managed roster contained a player "
                "without provider_player_key."
            )

        if key in seen_keys:
            raise LineupOptimizerError(
                "Managed roster contained duplicate "
                f"player key {key!r}."
            )

        seen_keys.add(
            key
        )

        name = str(
            row.get(
                "full_name",
                "",
            )
        ).strip() or key

        day = row.get(
            day_key
        )

        if not isinstance(
            day,
            Mapping,
        ):
            day = {}

        schedule_state = str(
            day.get(
                "schedule_state",
                "",
            )
        ).strip()

        availability_state = str(
            row.get(
                "availability_state",
                "available",
            )
        ).strip().casefold()

        expected_points = (
            _day_expected_points(
                day
            )
        )

        player_kind = (
            _player_type(
                row
            )
        )

        eligible_positions = (
            _eligible_positions(
                row
            )
        )

        hold_reason = None

        if (
            availability_state
            == "unavailable"
        ):
            hold_reason = (
                "player_unavailable"
            )

        elif schedule_state == "off":
            hold_reason = "off_day"

        elif schedule_state != "scheduled":
            hold_reason = (
                "schedule_unresolved"
            )

        elif player_kind == "G":
            hold_reason = (
                "goalie_start_model_pending"
            )

        elif (
            expected_points is None
            or expected_points <= 0.0
        ):
            hold_reason = (
                "no_positive_projection"
            )

        else:
            candidates.append(
                (
                    key,
                    name,
                    expected_points,
                    eligible_positions,
                    availability_state,
                )
            )

        player_context[
            key
        ] = (
            name,
            expected_points,
            hold_reason,
            availability_state,
        )

    slot_names = tuple(
        position
        for position, _
        in starting_skater_slots
    )

    capacities = tuple(
        count
        for _, count
        in starting_skater_slots
    )

    candidates = tuple(
        sorted(
            candidates,
            key=lambda row: row[0],
        )
    )

    @lru_cache(
        maxsize=None
    )
    def solve(
        player_index: int,
        used: tuple[int, ...],
    ):
        if (
            player_index
            >= len(
                candidates
            )
        ):
            return (
                0.0,
                (),
            )

        (
            player_key,
            _,
            expected_points,
            eligible_positions,
            _,
        ) = candidates[
            player_index
        ]

        best = solve(
            player_index + 1,
            used,
        )

        for slot_index, slot_name in enumerate(
            slot_names
        ):
            if (
                used[
                    slot_index
                ]
                >= capacities[
                    slot_index
                ]
            ):
                continue

            if (
                slot_name
                not in eligible_positions
            ):
                continue

            new_used = list(
                used
            )

            new_used[
                slot_index
            ] += 1

            (
                tail_score,
                tail_assignments,
            ) = solve(
                player_index + 1,
                tuple(
                    new_used
                ),
            )

            candidate_solution = (
                expected_points
                + tail_score,
                (
                    (
                        player_key,
                        slot_name,
                    ),
                )
                + tail_assignments,
            )

            best = _better_solution(
                candidate_solution,
                best,
            )

        return best

    initial_used = tuple(
        0
        for _ in slot_names
    )

    _, assignments = solve(
        0,
        initial_used,
    )

    assigned_by_key = {
        player_key: slot_name
        for (
            player_key,
            slot_name,
        )
        in assignments
    }

    candidate_keys = {
        row[0]
        for row in candidates
    }

    decisions = []

    for key in seen_keys:
        (
            name,
            expected_points,
            hold_reason,
            availability_state,
        ) = player_context[
            key
        ]

        assigned_position = (
            assigned_by_key.get(
                key
            )
        )

        if assigned_position is not None:
            action = ACTION_START

            if (
                availability_state
                == "uncertain"
            ):
                reason = (
                    "optimal_daily_lineup_"
                    "availability_uncertain"
                )

            else:
                reason = (
                    "optimal_daily_lineup"
                )

        elif key in candidate_keys:
            action = ACTION_BENCH
            reason = (
                "slot_congestion"
            )

        else:
            action = ACTION_HOLD
            reason = (
                hold_reason
                or "no_same_day_action"
            )

        decisions.append(
            DailyLineupDecision(
                provider_player_key=key,
                full_name=name,
                day_key=day_key,
                action=action,
                assigned_position=(
                    assigned_position
                ),
                expected_points=(
                    expected_points
                ),
                reason=reason,
            )
        )

    action_order = {
        ACTION_START: 0,
        ACTION_BENCH: 1,
        ACTION_HOLD: 2,
    }

    return tuple(
        sorted(
            decisions,
            key=lambda row: (
                action_order[
                    row.action
                ],
                -(
                    row.expected_points
                    if row.expected_points
                    is not None
                    else -1.0
                ),
                row.full_name.casefold(),
                row.provider_player_key,
            ),
        )
    )
