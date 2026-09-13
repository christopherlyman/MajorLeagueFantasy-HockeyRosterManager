from __future__ import annotations

from datetime import date
from types import SimpleNamespace
import unittest

from hockey_rmt.domain.daily_value import (
    DAILY_VALUE_PLAYER_UNAVAILABLE,
)
from hockey_rmt.domain.game_context import (
    PlayerGameContext,
)
from hockey_rmt.domain.player_availability import (
    PLAYER_AVAILABILITY_AVAILABLE,
    PLAYER_AVAILABILITY_UNAVAILABLE,
    PLAYER_AVAILABILITY_UNCERTAIN,
    classify_player_availability,
)
from hockey_rmt.services import daily_value as daily_value_service
from hockey_rmt.services.daily_value import (
    build_baseline_daily_expected_values,
)


GAME_DATE = date(
    2026,
    9,
    29,
)

SEASON_ID = 20262027


def _strength():
    return SimpleNamespace(
        provider_player_key="477.p.1",
        projection_season_id=SEASON_ID,
        projected_fantasy_points_per_game=4.75,
        strength_state=(
            daily_value_service.STRENGTH_AVAILABLE
        ),
        full_name="Test Player",
        player_type="P",
        nhl_player_id=1,
    )


def _context(
    *,
    schedule_state="scheduled",
    availability_state=(
        PLAYER_AVAILABILITY_AVAILABLE
    ),
    status=None,
    status_full=None,
):
    return PlayerGameContext(
        provider_player_key="477.p.1",
        game_date=GAME_DATE,
        nhl_team_abbr="TBL",
        schedule_state=schedule_state,
        provider_game_id=(
            "game-1"
            if schedule_state == "scheduled"
            else None
        ),
        opponent_team_abbr=(
            "FLA"
            if schedule_state == "scheduled"
            else None
        ),
        home_away=(
            "home"
            if schedule_state == "scheduled"
            else None
        ),
        availability_state=availability_state,
        provider_status=status,
        provider_status_full=status_full,
    )


def _daily(
    context,
):
    rows = (
        build_baseline_daily_expected_values(
            player_strengths=(
                _strength(),
            ),
            game_contexts=(
                context,
            ),
            season_id=SEASON_ID,
            game_date=GAME_DATE,
        )
    )

    if len(rows) != 1:
        raise AssertionError(
            "Expected one daily-value row."
        )

    return rows[0]


class PlayerAvailabilityTests(
    unittest.TestCase
):
    def test_blank_yahoo_status_is_available(
        self,
    ):
        self.assertEqual(
            classify_player_availability(
                provider="yahoo",
                status=None,
            ),
            PLAYER_AVAILABILITY_AVAILABLE,
        )


    def test_yahoo_hard_unavailable_statuses(
        self,
    ):
        for status in (
            "NA",
            "O",
            "IR",
            "IR-LT",
            "IR-NR",
        ):
            with self.subTest(
                status=status
            ):
                self.assertEqual(
                    classify_player_availability(
                        provider="yahoo",
                        status=status,
                    ),
                    PLAYER_AVAILABILITY_UNAVAILABLE,
                )


    def test_yahoo_dtd_is_uncertain(
        self,
    ):
        self.assertEqual(
            classify_player_availability(
                provider="yahoo",
                status="DTD",
            ),
            PLAYER_AVAILABILITY_UNCERTAIN,
        )


    def test_unknown_nonblank_status_is_uncertain(
        self,
    ):
        self.assertEqual(
            classify_player_availability(
                provider="yahoo",
                status="NEW-STATUS",
            ),
            PLAYER_AVAILABILITY_UNCERTAIN,
        )


    def test_scheduled_unavailable_player_is_zero(
        self,
    ):
        row = _daily(
            _context(
                availability_state=(
                    PLAYER_AVAILABILITY_UNAVAILABLE
                ),
                status="O",
                status_full="Out",
            )
        )

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_PLAYER_UNAVAILABLE,
        )

        self.assertEqual(
            row.expected_fantasy_points,
            0.0,
        )

        self.assertEqual(
            row.availability_state,
            PLAYER_AVAILABILITY_UNAVAILABLE,
        )

        self.assertEqual(
            row.provider_status,
            "O",
        )

        self.assertEqual(
            row.provider_status_full,
            "Out",
        )


    def test_dtd_player_remains_projected(
        self,
    ):
        row = _daily(
            _context(
                availability_state=(
                    PLAYER_AVAILABILITY_UNCERTAIN
                ),
                status="DTD",
                status_full="Day-to-Day",
            )
        )

        self.assertEqual(
            row.value_state,
            daily_value_service.DAILY_VALUE_AVAILABLE,
        )

        self.assertEqual(
            row.expected_fantasy_points,
            4.75,
        )

        self.assertEqual(
            row.availability_state,
            PLAYER_AVAILABILITY_UNCERTAIN,
        )


    def test_off_day_retains_schedule_precedence(
        self,
    ):
        row = _daily(
            _context(
                schedule_state="off",
                availability_state=(
                    PLAYER_AVAILABILITY_UNAVAILABLE
                ),
                status="IR",
                status_full="Injured Reserve",
            )
        )

        self.assertEqual(
            row.value_state,
            daily_value_service.DAILY_VALUE_OFF,
        )

        self.assertEqual(
            row.expected_fantasy_points,
            0.0,
        )

        self.assertEqual(
            row.availability_state,
            PLAYER_AVAILABILITY_UNAVAILABLE,
        )


if __name__ == "__main__":
    unittest.main()
