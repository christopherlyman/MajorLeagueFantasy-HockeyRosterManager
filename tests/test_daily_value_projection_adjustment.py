from __future__ import annotations

from datetime import (
    date,
    datetime,
    timezone,
)
import unittest

from hockey_rmt.domain.game_context import (
    PlayerGameContext,
)
from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    PlayerStrengthProjection,
)
from hockey_rmt.domain.projection_adjustment import (
    ADJUSTMENT_APPLIED,
    ADJUSTMENT_BASELINE_ONLY,
    PlayerProjectionAdjustment,
)
from hockey_rmt.services.daily_value import (
    DailyValueError,
    build_baseline_daily_expected_values,
)


SEASON = 20262027
GAME_DATE = date(2026, 9, 29)


def _strength(
    *,
    key: str = "477.p.1",
    nhl_player_id: int = 1,
    player_type: str = "P",
    fppg: float = 4.0,
):
    return PlayerStrengthProjection(
        provider_player_key=key,
        full_name="Player One",
        projection_season_id=SEASON,
        player_type=player_type,
        nhl_player_id=nhl_player_id,
        strength_state=STRENGTH_AVAILABLE,
        projection_source="test",
        source_state="test",
        projected_fantasy_points_per_game=fppg,
    )


def _context(
    *,
    key: str = "477.p.1",
    availability_state: str = "available",
    schedule_state: str = "scheduled",
):
    return PlayerGameContext(
        provider_player_key=key,
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
        start_time_utc=(
            datetime(
                2026,
                9,
                29,
                23,
                0,
                tzinfo=timezone.utc,
            )
            if schedule_state == "scheduled"
            else None
        ),
        availability_state=availability_state,
        provider_status=None,
        provider_status_full=None,
    )


def _adjustment(
    *,
    key: str = "477.p.1",
    nhl_player_id: int = 1,
    player_type: str = "P",
    baseline: float = 4.0,
    adjusted: float | None = 4.4,
    factor: float = 1.10,
    state: str = ADJUSTMENT_APPLIED,
):
    return PlayerProjectionAdjustment(
        provider_player_key=key,
        full_name="Player One",
        projection_season_id=SEASON,
        player_type=player_type,
        nhl_player_id=nhl_player_id,
        adjustment_state=state,
        baseline_fantasy_points_per_game=baseline,
        adjusted_fantasy_points_per_game=adjusted,
        deployment_factor=1.04,
        trend_role_factor=1.03,
        process_factor=1.015,
        production_factor=1.0,
        combined_factor=factor,
        deployment_even_strength_group="f1",
        deployment_power_play_group="pp1",
        current_production_games=None,
        current_production_fantasy_points_per_game=None,
        role_state="expanding",
        process_state="improving",
        finishing_state="neutral",
        reasons=(),
    )


class DailyValueProjectionAdjustmentTests(
    unittest.TestCase
):
    def test_legacy_path_uses_baseline(self):
        row = build_baseline_daily_expected_values(
            player_strengths=(_strength(),),
            game_contexts=(_context(),),
            season_id=SEASON,
            game_date=GAME_DATE,
        )[0]

        self.assertEqual(
            row.expected_fantasy_points,
            4.0,
        )

        self.assertEqual(
            row.adjusted_fantasy_points_per_game,
            4.0,
        )

        self.assertEqual(
            row.adjustment_factor,
            1.0,
        )

        self.assertIsNone(
            row.adjustment_state
        )


    def test_adjusted_fppg_drives_available_value(self):
        row = build_baseline_daily_expected_values(
            player_strengths=(_strength(),),
            game_contexts=(_context(),),
            season_id=SEASON,
            game_date=GAME_DATE,
            projection_adjustments=(
                _adjustment(),
            ),
        )[0]

        self.assertEqual(
            row.baseline_fantasy_points_per_game,
            4.0,
        )

        self.assertEqual(
            row.adjusted_fantasy_points_per_game,
            4.4,
        )

        self.assertEqual(
            row.expected_fantasy_points,
            4.4,
        )

        self.assertEqual(
            row.adjustment_state,
            ADJUSTMENT_APPLIED,
        )

        self.assertEqual(
            row.adjustment_factor,
            1.10,
        )


    def test_hard_unavailable_still_zero(self):
        row = build_baseline_daily_expected_values(
            player_strengths=(_strength(),),
            game_contexts=(
                _context(
                    availability_state="unavailable",
                ),
            ),
            season_id=SEASON,
            game_date=GAME_DATE,
            projection_adjustments=(
                _adjustment(),
            ),
        )[0]

        self.assertEqual(
            row.value_state,
            "player_unavailable",
        )

        self.assertEqual(
            row.expected_fantasy_points,
            0.0,
        )

        self.assertEqual(
            row.adjusted_fantasy_points_per_game,
            4.4,
        )


    def test_off_day_still_zero(self):
        row = build_baseline_daily_expected_values(
            player_strengths=(_strength(),),
            game_contexts=(
                _context(
                    schedule_state="off",
                ),
            ),
            season_id=SEASON,
            game_date=GAME_DATE,
            projection_adjustments=(
                _adjustment(),
            ),
        )[0]

        self.assertEqual(
            row.value_state,
            "off",
        )

        self.assertEqual(
            row.expected_fantasy_points,
            0.0,
        )


    def test_universe_mismatch_rejected(self):
        with self.assertRaises(
            DailyValueError
        ):
            build_baseline_daily_expected_values(
                player_strengths=(_strength(),),
                game_contexts=(_context(),),
                season_id=SEASON,
                game_date=GAME_DATE,
                projection_adjustments=(
                    _adjustment(
                        key="477.p.2",
                    ),
                ),
            )


    def test_identity_mismatch_rejected(self):
        with self.assertRaises(
            DailyValueError
        ):
            build_baseline_daily_expected_values(
                player_strengths=(_strength(),),
                game_contexts=(_context(),),
                season_id=SEASON,
                game_date=GAME_DATE,
                projection_adjustments=(
                    _adjustment(
                        nhl_player_id=2,
                    ),
                ),
            )


    def test_type_mismatch_rejected(self):
        with self.assertRaises(
            DailyValueError
        ):
            build_baseline_daily_expected_values(
                player_strengths=(_strength(),),
                game_contexts=(_context(),),
                season_id=SEASON,
                game_date=GAME_DATE,
                projection_adjustments=(
                    _adjustment(
                        player_type="G",
                    ),
                ),
            )


    def test_baseline_mismatch_rejected(self):
        with self.assertRaises(
            DailyValueError
        ):
            build_baseline_daily_expected_values(
                player_strengths=(_strength(),),
                game_contexts=(_context(),),
                season_id=SEASON,
                game_date=GAME_DATE,
                projection_adjustments=(
                    _adjustment(
                        baseline=4.1,
                    ),
                ),
            )


    def test_available_adjustment_requires_fppg(self):
        with self.assertRaises(
            DailyValueError
        ):
            build_baseline_daily_expected_values(
                player_strengths=(_strength(),),
                game_contexts=(_context(),),
                season_id=SEASON,
                game_date=GAME_DATE,
                projection_adjustments=(
                    _adjustment(
                        adjusted=None,
                    ),
                ),
            )


    def test_baseline_only_adjustment_round_trip(self):
        row = build_baseline_daily_expected_values(
            player_strengths=(_strength(),),
            game_contexts=(_context(),),
            season_id=SEASON,
            game_date=GAME_DATE,
            projection_adjustments=(
                _adjustment(
                    adjusted=4.0,
                    factor=1.0,
                    state=ADJUSTMENT_BASELINE_ONLY,
                ),
            ),
        )[0]

        self.assertEqual(
            row.expected_fantasy_points,
            4.0,
        )

        self.assertEqual(
            row.adjustment_state,
            ADJUSTMENT_BASELINE_ONLY,
        )


if __name__ == "__main__":
    unittest.main()
