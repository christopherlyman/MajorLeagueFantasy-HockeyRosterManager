from __future__ import annotations

import unittest

from hockey_rmt.domain.league import (
    RosterPosition,
)
from hockey_rmt.domain.market_decision import (
    MARKET_ACTION_ADD,
    MARKET_ACTION_HOLD,
    MARKET_ACTION_STREAM,
)
from hockey_rmt.services.market_decision import (
    build_market_decisions,
    market_decision_result_payload,
)


def _positions():
    return (
        RosterPosition(
            position="C",
            count=1,
            is_starting=True,
            position_type="P",
        ),
        RosterPosition(
            position="D",
            count=1,
            is_starting=True,
            position_type="P",
        ),
        RosterPosition(
            position="BN",
            count=2,
            is_starting=False,
            position_type=None,
        ),
    )


def _row(
    key,
    name,
    *,
    position="C",
    managed=False,
    market_state="free_agent",
    values=(0.0, 0.0, 0.0),
    availability="available",
    percent_rostered=0,
):
    day_rows = []

    for index, value in enumerate(
        values
    ):
        day_rows.append(
            {
                "date": (
                    f"2026-09-{29 + index:02d}"
                ),
                "schedule_state": (
                    "scheduled"
                    if value is not None
                    else "off"
                ),
                "expected_points": (
                    float(value)
                    if value is not None
                    else 0.0
                ),
            }
        )

    scheduled_games = sum(
        value is not None
        for value in values
    )

    three_day = sum(
        float(value)
        for value in values
        if value is not None
    )

    return {
        "provider_player_key": key,
        "full_name": name,
        "player_type": "P",
        "eligible_positions": [
            position,
            "Util",
        ],
        "is_on_managed_team": managed,
        "market_state": market_state,
        "availability_state": availability,
        "percent_rostered": (
            percent_rostered
        ),
        "scheduled_games": (
            scheduled_games
        ),
        "three_day_expected_points": (
            three_day
        ),
        "three_day_rank": 1,
        "today": day_rows[0],
        "tomorrow": day_rows[1],
        "day_plus_2": day_rows[2],
    }


class MarketDecisionTests(
    unittest.TestCase
):
    def test_empty_roster_holds(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "fa",
                    "Free Agent",
                    values=(
                        5.0,
                        5.0,
                        5.0,
                    ),
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={},
            max_weekly_adds=7,
            weekly_adds_used=0,
        )

        self.assertEqual(
            result.state,
            "waiting_for_managed_roster",
        )

        self.assertEqual(
            result.overall_action,
            MARKET_ACTION_HOLD,
        )

        self.assertEqual(
            result.recommendations,
            (),
        )


    def test_weekly_add_limit_is_hard_block(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "mine",
                    "Mine",
                    managed=True,
                    market_state="rostered",
                    values=(
                        2.0,
                        2.0,
                        2.0,
                    ),
                ),
                _row(
                    "fa",
                    "Free Agent",
                    values=(
                        5.0,
                        5.0,
                        5.0,
                    ),
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={
                "mine": False,
            },
            max_weekly_adds=7,
            weekly_adds_used=7,
        )

        self.assertEqual(
            result.state,
            "weekly_add_limit_reached",
        )

        self.assertEqual(
            result.recommendations,
            (),
        )


    def test_undroppable_player_is_never_drop(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "mine",
                    "Protected",
                    managed=True,
                    market_state="rostered",
                    values=(
                        1.0,
                        1.0,
                        1.0,
                    ),
                ),
                _row(
                    "fa",
                    "Free Agent",
                    values=(
                        5.0,
                        5.0,
                        5.0,
                    ),
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={
                "mine": True,
            },
            max_weekly_adds=7,
            weekly_adds_used=0,
        )

        self.assertEqual(
            result.state,
            "no_droppable_skaters",
        )

        self.assertEqual(
            result.recommendations,
            (),
        )


    def test_true_per_game_upgrade_is_add(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "mine",
                    "Current Center",
                    managed=True,
                    market_state="rostered",
                    values=(
                        4.0,
                        4.0,
                        4.0,
                    ),
                ),
                _row(
                    "fa",
                    "Better Center",
                    values=(
                        5.0,
                        5.0,
                        5.0,
                    ),
                    percent_rostered=75,
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={
                "mine": False,
            },
            max_weekly_adds=7,
            weekly_adds_used=0,
        )

        self.assertEqual(
            result.state,
            "recommendations_available",
        )

        recommendation = (
            result.recommendations[
                0
            ]
        )

        self.assertEqual(
            recommendation.action,
            MARKET_ACTION_ADD,
        )

        self.assertEqual(
            recommendation.drop_player_key,
            "mine",
        )

        self.assertAlmostEqual(
            recommendation.usable_three_day_gain,
            3.0,
            places=12,
        )


    def test_schedule_gain_is_stream(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "mine",
                    "Strong One Game",
                    managed=True,
                    market_state="rostered",
                    values=(
                        5.0,
                        None,
                        None,
                    ),
                ),
                _row(
                    "fa",
                    "Three Game Stream",
                    values=(
                        4.0,
                        4.0,
                        4.0,
                    ),
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={
                "mine": False,
            },
            max_weekly_adds=7,
            weekly_adds_used=0,
        )

        recommendation = (
            result.recommendations[
                0
            ]
        )

        self.assertEqual(
            recommendation.action,
            MARKET_ACTION_STREAM,
        )

        self.assertAlmostEqual(
            recommendation.usable_three_day_gain,
            7.0,
            places=12,
        )


    def test_waiver_player_is_not_immediate_add(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "mine",
                    "Current Center",
                    managed=True,
                    market_state="rostered",
                    values=(
                        1.0,
                        1.0,
                        1.0,
                    ),
                ),
                _row(
                    "waiver",
                    "Waiver Star",
                    market_state="waiver",
                    values=(
                        8.0,
                        8.0,
                        8.0,
                    ),
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={
                "mine": False,
            },
            max_weekly_adds=7,
            weekly_adds_used=0,
        )

        self.assertEqual(
            result.state,
            "no_actionable_free_agents",
        )

        self.assertEqual(
            result.waiver_candidates_skipped,
            1,
        )


    def test_sub_floor_gain_holds(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "mine",
                    "Current Center",
                    managed=True,
                    market_state="rostered",
                    values=(
                        4.0,
                        4.0,
                        4.0,
                    ),
                ),
                _row(
                    "fa",
                    "Tiny Upgrade",
                    values=(
                        4.1,
                        4.1,
                        4.1,
                    ),
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={
                "mine": False,
            },
            max_weekly_adds=7,
            weekly_adds_used=0,
        )

        self.assertEqual(
            result.state,
            "hold_no_meaningful_upgrade",
        )

        self.assertEqual(
            result.overall_action,
            MARKET_ACTION_HOLD,
        )


    def test_payload_contains_drop_action(self):
        result = build_market_decisions(
            rows=(
                _row(
                    "mine",
                    "Current Center",
                    managed=True,
                    market_state="rostered",
                    values=(
                        1.0,
                        1.0,
                        1.0,
                    ),
                ),
                _row(
                    "fa",
                    "Better Center",
                    values=(
                        5.0,
                        5.0,
                        5.0,
                    ),
                ),
            ),
            roster_positions=_positions(),
            is_undroppable_by_player_key={
                "mine": False,
            },
            max_weekly_adds=7,
            weekly_adds_used=0,
        )

        _, recommendations = (
            market_decision_result_payload(
                result
            )
        )

        self.assertEqual(
            recommendations[
                0
            ][
                "drop_action"
            ],
            "DROP",
        )


if __name__ == "__main__":
    unittest.main()
