from __future__ import annotations

import math
import unittest

from hockey_rmt.domain.current_production import (
    CURRENT_PRODUCTION_AVAILABLE,
    CURRENT_PRODUCTION_SOURCE_OFFICIAL_NHL,
    CurrentSeasonProduction,
)
from hockey_rmt.domain.deployment import (
    CATEGORY_EVEN_STRENGTH,
    CATEGORY_POWER_PLAY,
    DEPLOYMENT_SOURCE_DAILY_FACEOFF,
    DeploymentAssignment,
    SourcePlayerDeployment,
)
from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    PlayerStrengthProjection,
)
from hockey_rmt.domain.projection_adjustment import (
    ADJUSTMENT_APPLIED,
    ADJUSTMENT_BASELINE_ONLY,
    ADJUSTMENT_NOT_APPLICABLE,
    ADJUSTMENT_STRENGTH_UNAVAILABLE,
)
from hockey_rmt.domain.trend_signal import (
    FINISHING_COLD,
    FINISHING_HOT,
    FINISHING_NEUTRAL,
    ROLE_EXPANDING,
    ROLE_STABLE,
    ROLE_SHRINKING,
    SAMPLE_AVAILABLE,
    TREND_DECLINING,
    TREND_IMPROVING,
    TREND_STABLE,
    MetricTrendEvidence,
    SkaterTrendInterpretation,
)
from hockey_rmt.services.projection_adjustment import (
    ProjectionAdjustmentError,
    build_player_projection_adjustments,
)


SEASON = 20262027


def _strength(
    *,
    key: str = "477.p.1",
    name: str = "Player One",
    player_type: str = "P",
    nhl_player_id: int | None = 1,
    fppg: float | None = 4.0,
    strength_state: str = STRENGTH_AVAILABLE,
):
    return PlayerStrengthProjection(
        provider_player_key=key,
        full_name=name,
        projection_season_id=SEASON,
        player_type=player_type,
        nhl_player_id=nhl_player_id,
        strength_state=strength_state,
        projection_source="test",
        source_state="test",
        projected_fantasy_points_per_game=fppg,
    )


def _production(
    *,
    key: str = "477.p.1",
    name: str = "Player One",
    nhl_player_id: int = 1,
    games: int = 20,
    fppg: float = 5.0,
):
    return CurrentSeasonProduction(
        provider_player_key=key,
        full_name=name,
        season_id=SEASON,
        player_type="skater",
        nhl_player_id=nhl_player_id,
        production_state=(
            CURRENT_PRODUCTION_AVAILABLE
        ),
        production_source=(
            CURRENT_PRODUCTION_SOURCE_OFFICIAL_NHL
        ),
        games_played=games,
        fantasy_points=(
            fppg
            * games
        ),
        fantasy_points_per_game=fppg,
        components=None,
    )


def _evidence(
    name: str,
    state: str = TREND_STABLE,
):
    return MetricTrendEvidence(
        metric_name=name,
        season_value=1.0,
        last_20_value=1.0,
        last_10_value=1.0,
        last_20_change=0.0,
        last_10_change=0.0,
        state=state,
    )


def _trend(
    *,
    player_id: int = 1,
    role_state: str = ROLE_STABLE,
    process_state: str = TREND_STABLE,
    finishing_state: str = FINISHING_NEUTRAL,
):
    return SkaterTrendInterpretation(
        source="moneypuck",
        season_id=SEASON,
        nhl_player_id=player_id,
        full_name="Player One",
        nhl_team_abbr="TBL",
        position="C",
        season_games_played=30,
        last_20_games_played=20,
        last_10_games_played=10,
        role_sample_state=(
            SAMPLE_AVAILABLE
        ),
        process_sample_state=(
            SAMPLE_AVAILABLE
        ),
        toi_usage=_evidence(
            "toi_per_game_minutes"
        ),
        power_play_toi_usage=_evidence(
            "power_play_toi_per_game_minutes"
        ),
        role_state=role_state,
        process_metrics=(
            _evidence(
                "expected_goals_per_60"
            ),
            _evidence(
                "shots_on_goal_per_60"
            ),
            _evidence(
                "shot_attempts_per_60"
            ),
            _evidence(
                "high_danger_shots_per_60"
            ),
            _evidence(
                "primary_assists_per_60"
            ),
        ),
        process_state=process_state,
        process_improving_metrics=0,
        process_stable_metrics=5,
        process_declining_metrics=0,
        process_mixed_metrics=0,
        finishing_state=finishing_state,
        season_goals_minus_expected_per_60=0.0,
        last_20_goals_minus_expected_per_60=0.0,
        last_10_goals_minus_expected_per_60=0.0,
    )


def _assignment(
    *,
    category: str,
    group: str,
):
    return DeploymentAssignment(
        category_identifier=category,
        category_name=category,
        group_identifier=group,
        group_name=group,
        position_identifier="x",
        position_name="x",
    )


def _deployment(
    *,
    player_id: int = 1,
    ev_group: str = "f1",
    pp_group: str | None = "pp1",
):
    assignments = [
        _assignment(
            category=(
                CATEGORY_EVEN_STRENGTH
            ),
            group=ev_group,
        )
    ]

    if pp_group is not None:
        assignments.append(
            _assignment(
                category=(
                    CATEGORY_POWER_PLAY
                ),
                group=pp_group,
            )
        )

    return SourcePlayerDeployment(
        source=(
            DEPLOYMENT_SOURCE_DAILY_FACEOFF
        ),
        source_player_id=str(
            player_id
        ),
        full_name="Player One",
        team_abbreviation="TBL",
        injury_status=None,
        game_time_decision=False,
        assignments=tuple(
            assignments
        ),
    )


class ProjectionAdjustmentTests(
    unittest.TestCase
):
    def test_no_evidence_preserves_baseline(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
            )[0]
        )

        self.assertEqual(
            row.adjustment_state,
            ADJUSTMENT_BASELINE_ONLY,
        )

        self.assertEqual(
            row.combined_factor,
            1.0,
        )

        self.assertEqual(
            row.adjusted_fantasy_points_per_game,
            4.0,
        )


    def test_dfo_f1_pp1_is_four_percent(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                deployments_by_nhl_id={
                    1: _deployment(),
                },
            )[0]
        )

        self.assertEqual(
            row.adjustment_state,
            ADJUSTMENT_APPLIED,
        )

        self.assertTrue(
            math.isclose(
                row.deployment_factor,
                1.04,
            )
        )

        self.assertTrue(
            math.isclose(
                row.adjusted_fantasy_points_per_game,
                4.16,
            )
        )


    def test_bottom_line_without_pp_is_reduced(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                deployments_by_nhl_id={
                    1: _deployment(
                        ev_group="f4",
                        pp_group=None,
                    ),
                },
            )[0]
        )

        self.assertTrue(
            math.isclose(
                row.deployment_factor,
                0.975,
            )
        )


    def test_expanding_role_and_process_improving(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                trend_interpretations=(
                    _trend(
                        role_state=(
                            ROLE_EXPANDING
                        ),
                        process_state=(
                            TREND_IMPROVING
                        ),
                    ),
                ),
            )[0]
        )

        self.assertTrue(
            math.isclose(
                row.trend_role_factor,
                1.03,
            )
        )

        self.assertTrue(
            math.isclose(
                row.process_factor,
                1.015,
            )
        )


    def test_shrinking_role_and_process_declining(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                trend_interpretations=(
                    _trend(
                        role_state=(
                            ROLE_SHRINKING
                        ),
                        process_state=(
                            TREND_DECLINING
                        ),
                    ),
                ),
            )[0]
        )

        self.assertTrue(
            math.isclose(
                row.trend_role_factor,
                0.97,
            )
        )

        self.assertTrue(
            math.isclose(
                row.process_factor,
                0.985,
            )
        )


    def test_production_weight_grows_progressively(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                current_production=(
                    _production(
                        games=20,
                        fppg=5.0,
                    ),
                ),
            )[0]
        )

        self.assertTrue(
            math.isclose(
                row.production_factor,
                1.025,
            )
        )


    def test_hot_finishing_brakes_positive_production(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                current_production=(
                    _production(
                        games=60,
                        fppg=5.0,
                    ),
                ),
                trend_interpretations=(
                    _trend(
                        finishing_state=(
                            FINISHING_HOT
                        ),
                    ),
                ),
            )[0]
        )

        self.assertTrue(
            math.isclose(
                row.production_factor,
                1.0375,
            )
        )


    def test_cold_finishing_brakes_negative_production(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                current_production=(
                    _production(
                        games=60,
                        fppg=3.0,
                    ),
                ),
                trend_interpretations=(
                    _trend(
                        finishing_state=(
                            FINISHING_COLD
                        ),
                    ),
                ),
            )[0]
        )

        self.assertTrue(
            math.isclose(
                row.production_factor,
                0.9625,
            )
        )


    def test_combined_positive_adjustment_is_capped(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                current_production=(
                    _production(
                        games=60,
                        fppg=8.0,
                    ),
                ),
                trend_interpretations=(
                    _trend(
                        role_state=(
                            ROLE_EXPANDING
                        ),
                        process_state=(
                            TREND_IMPROVING
                        ),
                    ),
                ),
                deployments_by_nhl_id={
                    1: _deployment(),
                },
            )[0]
        )

        self.assertLessEqual(
            row.combined_factor,
            1.12,
        )

        self.assertGreater(
            row.combined_factor,
            1.0,
        )


    def test_goalie_is_not_adjusted(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(
                        player_type="G",
                    ),
                ),
                projection_season_id=SEASON,
            )[0]
        )

        self.assertEqual(
            row.adjustment_state,
            ADJUSTMENT_NOT_APPLICABLE,
        )

        self.assertEqual(
            row.combined_factor,
            1.0,
        )

        self.assertEqual(
            row.adjusted_fantasy_points_per_game,
            4.0,
        )


    def test_unavailable_strength_stays_unavailable(
        self,
    ):
        row = (
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(
                        fppg=None,
                        strength_state=(
                            "identity_unresolved"
                        ),
                    ),
                ),
                projection_season_id=SEASON,
            )[0]
        )

        self.assertEqual(
            row.adjustment_state,
            ADJUSTMENT_STRENGTH_UNAVAILABLE,
        )

        self.assertIsNone(
            row.adjusted_fantasy_points_per_game
        )


    def test_duplicate_strength_key_rejected(
        self,
    ):
        player = _strength()

        with self.assertRaises(
            ProjectionAdjustmentError
        ):
            build_player_projection_adjustments(
                player_strengths=(
                    player,
                    player,
                ),
                projection_season_id=SEASON,
            )


    def test_production_identity_mismatch_rejected(
        self,
    ):
        with self.assertRaises(
            ProjectionAdjustmentError
        ):
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                current_production=(
                    _production(
                        nhl_player_id=2,
                    ),
                ),
            )


    def test_unknown_canonical_type_rejected(
        self,
    ):
        with self.assertRaises(
            ProjectionAdjustmentError
        ):
            build_player_projection_adjustments(
                player_strengths=(
                    _strength(
                        player_type="X",
                    ),
                ),
                projection_season_id=SEASON,
            )



if __name__ == "__main__":
    unittest.main()
