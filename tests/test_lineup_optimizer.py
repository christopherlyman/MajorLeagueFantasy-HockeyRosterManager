from __future__ import annotations

import unittest

from hockey_rmt.domain.league import (
    RosterPosition,
)
from hockey_rmt.domain.lineup_decision import (
    ACTION_BENCH,
    ACTION_HOLD,
    ACTION_START,
)
from hockey_rmt.services.lineup_optimizer import (
    LineupOptimizerError,
    build_daily_lineup_decisions,
    build_roster_position_snapshot,
)


def _row(
    key: str,
    name: str,
    points: float,
    positions,
    *,
    schedule_state: str = "scheduled",
    availability_state: str = "available",
    player_type: str = "P",
    managed: bool = True,
):
    return {
        "provider_player_key": key,
        "full_name": name,
        "player_type": player_type,
        "eligible_positions": list(
            positions
        ),
        "is_on_managed_team": managed,
        "availability_state": (
            availability_state
        ),
        "today": {
            "schedule_state": (
                schedule_state
            ),
            "expected_points": points,
        },
        "tomorrow": {
            "schedule_state": (
                schedule_state
            ),
            "expected_points": points,
        },
        "day_plus_2": {
            "schedule_state": (
                schedule_state
            ),
            "expected_points": points,
        },
    }


def _positions(
    *rows,
):
    return tuple(
        RosterPosition(
            position=position,
            count=count,
            is_starting=is_starting,
            position_type=position_type,
        )
        for (
            position,
            count,
            is_starting,
            position_type,
        )
        in rows
    )


class LineupOptimizerTests(
    unittest.TestCase
):
    def test_empty_managed_roster_returns_empty(
        self,
    ):
        rows = (
            _row(
                "p1",
                "Free Agent",
                5.0,
                ("C", "F", "Util"),
                managed=False,
            ),
        )

        result = build_daily_lineup_decisions(
            rows=rows,
            roster_positions=_positions(
                (
                    "C",
                    1,
                    True,
                    "P",
                ),
            ),
            day_key="today",
        )

        self.assertEqual(
            result,
            (),
        )


    def test_global_optimizer_preserves_scarce_slot(
        self,
    ):
        rows = (
            _row(
                "p1",
                "Flexible Star",
                5.0,
                ("C", "LW"),
            ),
            _row(
                "p2",
                "Center Only",
                4.0,
                ("C",),
            ),
        )

        decisions = (
            build_daily_lineup_decisions(
                rows=rows,
                roster_positions=_positions(
                    (
                        "C",
                        1,
                        True,
                        "P",
                    ),
                    (
                        "LW",
                        1,
                        True,
                        "P",
                    ),
                ),
                day_key="today",
            )
        )

        by_key = {
            row.provider_player_key: row
            for row in decisions
        }

        self.assertEqual(
            by_key[
                "p1"
            ].action,
            ACTION_START,
        )

        self.assertEqual(
            by_key[
                "p1"
            ].assigned_position,
            "LW",
        )

        self.assertEqual(
            by_key[
                "p2"
            ].assigned_position,
            "C",
        )


    def test_lower_value_playable_skater_is_benched(
        self,
    ):
        decisions = (
            build_daily_lineup_decisions(
                rows=(
                    _row(
                        "p1",
                        "Higher",
                        5.0,
                        ("C",),
                    ),
                    _row(
                        "p2",
                        "Lower",
                        4.0,
                        ("C",),
                    ),
                ),
                roster_positions=_positions(
                    (
                        "C",
                        1,
                        True,
                        "P",
                    ),
                ),
                day_key="today",
            )
        )

        by_key = {
            row.provider_player_key: row
            for row in decisions
        }

        self.assertEqual(
            by_key[
                "p1"
            ].action,
            ACTION_START,
        )

        self.assertEqual(
            by_key[
                "p2"
            ].action,
            ACTION_BENCH,
        )

        self.assertEqual(
            by_key[
                "p2"
            ].reason,
            "slot_congestion",
        )


    def test_off_day_is_hold(
        self,
    ):
        decision = (
            build_daily_lineup_decisions(
                rows=(
                    _row(
                        "p1",
                        "Off Player",
                        0.0,
                        ("C",),
                        schedule_state="off",
                    ),
                ),
                roster_positions=_positions(
                    (
                        "C",
                        1,
                        True,
                        "P",
                    ),
                ),
                day_key="today",
            )[0]
        )

        self.assertEqual(
            decision.action,
            ACTION_HOLD,
        )

        self.assertEqual(
            decision.reason,
            "off_day",
        )


    def test_unavailable_player_is_hold(
        self,
    ):
        decision = (
            build_daily_lineup_decisions(
                rows=(
                    _row(
                        "p1",
                        "Unavailable",
                        5.0,
                        ("C",),
                        availability_state=(
                            "unavailable"
                        ),
                    ),
                ),
                roster_positions=_positions(
                    (
                        "C",
                        1,
                        True,
                        "P",
                    ),
                ),
                day_key="today",
            )[0]
        )

        self.assertEqual(
            decision.action,
            ACTION_HOLD,
        )

        self.assertEqual(
            decision.reason,
            "player_unavailable",
        )


    def test_uncertain_player_can_still_start(
        self,
    ):
        decision = (
            build_daily_lineup_decisions(
                rows=(
                    _row(
                        "p1",
                        "DTD Player",
                        5.0,
                        ("C",),
                        availability_state=(
                            "uncertain"
                        ),
                    ),
                ),
                roster_positions=_positions(
                    (
                        "C",
                        1,
                        True,
                        "P",
                    ),
                ),
                day_key="today",
            )[0]
        )

        self.assertEqual(
            decision.action,
            ACTION_START,
        )

        self.assertEqual(
            decision.reason,
            (
                "optimal_daily_lineup_"
                "availability_uncertain"
            ),
        )


    def test_goalie_is_hold_until_start_model(
        self,
    ):
        decision = (
            build_daily_lineup_decisions(
                rows=(
                    _row(
                        "g1",
                        "Goalie",
                        6.0,
                        ("G",),
                        player_type="G",
                    ),
                ),
                roster_positions=_positions(
                    (
                        "G",
                        2,
                        True,
                        "G",
                    ),
                ),
                day_key="today",
            )[0]
        )

        self.assertEqual(
            decision.action,
            ACTION_HOLD,
        )

        self.assertIsNone(
            decision.assigned_position
        )

        self.assertEqual(
            decision.reason,
            "goalie_start_model_pending",
        )


    def test_roster_position_snapshot_preserves_yahoo_configuration(
        self,
    ):
        source = _positions(
            (
                "C",
                2,
                True,
                "P",
            ),
            (
                "BN",
                4,
                False,
                None,
            ),
            (
                "IR+",
                2,
                False,
                None,
            ),
        )

        snapshot = (
            build_roster_position_snapshot(
                source
            )
        )

        self.assertEqual(
            snapshot[
                0
            ],
            {
                "position": "C",
                "count": 2,
                "is_starting": True,
                "position_type": "P",
            },
        )

        self.assertEqual(
            snapshot[
                1
            ][
                "is_starting"
            ],
            False,
        )


    def test_duplicate_roster_position_rejected(
        self,
    ):
        with self.assertRaises(
            LineupOptimizerError
        ):
            build_roster_position_snapshot(
                _positions(
                    (
                        "C",
                        1,
                        True,
                        "P",
                    ),
                    (
                        "C",
                        1,
                        True,
                        "P",
                    ),
                )
            )


class GoalieLineupOptimizerTests(
    unittest.TestCase
):
    @staticmethod
    def _goalie(
        key: str,
        name: str,
        expected_points,
        value_state: str,
    ) -> dict:
        return {
            "provider_player_key": key,
            "full_name": name,
            "is_on_managed_team": True,
            "availability_state": "available",
            "player_type": "G",
            "eligible_positions": [
                "G",
            ],
            "today": {
                "schedule_state": "scheduled",
                "expected_points": expected_points,
                "value_state": value_state,
            },
        }

    @staticmethod
    def _goalie_positions(
        count: int = 2,
    ) -> tuple[dict, ...]:
        return (
            {
                "position": "G",
                "count": count,
                "is_starting": True,
                "position_type": "G",
            },
        )

    def test_legacy_snapshot_keeps_goalie_hold(
        self,
    ):
        decision = (
            build_daily_lineup_decisions(
                rows=(
                    self._goalie(
                        "g1",
                        "Legacy Goalie",
                        6.0,
                        "available",
                    ),
                ),
                roster_positions=(
                    self._goalie_positions()
                ),
                day_key="today",
            )[0]
        )

        self.assertEqual(
            decision.action,
            ACTION_HOLD,
        )

        self.assertIsNone(
            decision.assigned_position
        )

        self.assertEqual(
            decision.reason,
            "goalie_start_model_pending",
        )

    def test_confirmed_goalie_can_start_when_model_active(
        self,
    ):
        decision = (
            build_daily_lineup_decisions(
                rows=(
                    self._goalie(
                        "g1",
                        "Confirmed Goalie",
                        6.0,
                        "available",
                    ),
                ),
                roster_positions=(
                    self._goalie_positions()
                ),
                day_key="today",
                goalie_start_model_active=True,
            )[0]
        )

        self.assertEqual(
            decision.action,
            ACTION_START,
        )

        self.assertEqual(
            decision.assigned_position,
            "G",
        )

        self.assertEqual(
            decision.expected_points,
            6.0,
        )

    def test_confirmed_goalies_compete_for_g_slots(
        self,
    ):
        decisions = (
            build_daily_lineup_decisions(
                rows=(
                    self._goalie(
                        "g1",
                        "Goalie One",
                        6.0,
                        "available",
                    ),
                    self._goalie(
                        "g2",
                        "Goalie Two",
                        5.0,
                        "available",
                    ),
                    self._goalie(
                        "g3",
                        "Goalie Three",
                        4.0,
                        "available",
                    ),
                ),
                roster_positions=(
                    self._goalie_positions(
                        count=2
                    )
                ),
                day_key="today",
                goalie_start_model_active=True,
            )
        )

        by_key = {
            row.provider_player_key: row
            for row in decisions
        }

        self.assertEqual(
            by_key[
                "g1"
            ].action,
            ACTION_START,
        )

        self.assertEqual(
            by_key[
                "g2"
            ].action,
            ACTION_START,
        )

        self.assertEqual(
            by_key[
                "g3"
            ].action,
            ACTION_BENCH,
        )

        self.assertEqual(
            by_key[
                "g3"
            ].reason,
            "slot_congestion",
        )

    def test_nonconfirmed_goalie_states_remain_hold(
        self,
    ):
        for value_state in (
            "goalie_start_likely",
            "goalie_start_unconfirmed",
            "goalie_start_unknown",
        ):
            with self.subTest(
                value_state=value_state
            ):
                decision = (
                    build_daily_lineup_decisions(
                        rows=(
                            self._goalie(
                                "g1",
                                "Waiting Goalie",
                                None,
                                value_state,
                            ),
                        ),
                        roster_positions=(
                            self._goalie_positions()
                        ),
                        day_key="today",
                        goalie_start_model_active=True,
                    )[0]
                )

                self.assertEqual(
                    decision.action,
                    ACTION_HOLD,
                )

                self.assertIsNone(
                    decision.assigned_position
                )

                self.assertEqual(
                    decision.reason,
                    value_state,
                )

    def test_unrecognized_active_goalie_state_fails_closed(
        self,
    ):
        decision = (
            build_daily_lineup_decisions(
                rows=(
                    self._goalie(
                        "g1",
                        "Unresolved Goalie",
                        6.0,
                        "strength_unavailable",
                    ),
                ),
                roster_positions=(
                    self._goalie_positions()
                ),
                day_key="today",
                goalie_start_model_active=True,
            )[0]
        )

        self.assertEqual(
            decision.action,
            ACTION_HOLD,
        )

        self.assertEqual(
            decision.reason,
            "goalie_start_state_unresolved",
        )

    def test_goalie_activation_flag_must_be_boolean(
        self,
    ):
        with self.assertRaises(
            LineupOptimizerError
        ):
            build_daily_lineup_decisions(
                rows=(
                    self._goalie(
                        "g1",
                        "Goalie",
                        6.0,
                        "available",
                    ),
                ),
                roster_positions=(
                    self._goalie_positions()
                ),
                day_key="today",
                goalie_start_model_active="yes",
            )



if __name__ == "__main__":
    unittest.main()
