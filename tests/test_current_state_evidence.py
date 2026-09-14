from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
import unittest

from hockey_rmt.domain.deployment import (
    CATEGORY_EVEN_STRENGTH,
    CATEGORY_POWER_PLAY,
    DEPLOYMENT_SOURCE_DAILY_FACEOFF,
    DeploymentAssignment,
    SourcePlayerDeployment,
    SourceTeamDeploymentSnapshot,
)
from hockey_rmt.domain.player_identity import (
    NhlPlayerIdentity,
)
from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    PlayerStrengthProjection,
)
from hockey_rmt.domain.projection_adjustment import (
    ADJUSTMENT_APPLIED,
)
from hockey_rmt.providers.daily_faceoff.deployment import (
    DailyFaceoffDeploymentError,
    team_slug_for_nhl_abbr,
)
from hockey_rmt.services.current_state_evidence import (
    CurrentStateEvidenceError,
    build_current_state_projection_adjustments,
    build_deployments_by_nhl_id,
)


SEASON = 20262027


def _strength():
    return PlayerStrengthProjection(
        provider_player_key="477.p.1",
        full_name="Test Skater",
        projection_season_id=SEASON,
        player_type="P",
        nhl_player_id=1,
        strength_state=STRENGTH_AVAILABLE,
        projection_source="test",
        source_state="test",
        projected_fantasy_points_per_game=4.0,
    )


def _identity():
    return NhlPlayerIdentity(
        nhl_player_id=1,
        full_name="Test Skater",
        position="C",
        team_abbr="TBL",
        active=True,
        last_season_id=20252026,
    )


def _deployment():
    return SourcePlayerDeployment(
        source=DEPLOYMENT_SOURCE_DAILY_FACEOFF,
        source_player_id="dfo-1",
        full_name="Test Skater",
        team_abbreviation="TBL",
        injury_status=None,
        game_time_decision=False,
        assignments=(
            DeploymentAssignment(
                category_identifier=(
                    CATEGORY_EVEN_STRENGTH
                ),
                category_name="Even Strength",
                group_identifier="f1",
                group_name="Forwards 1",
                position_identifier="c",
                position_name="Center",
            ),
            DeploymentAssignment(
                category_identifier=(
                    CATEGORY_POWER_PLAY
                ),
                category_name="Power Play",
                group_identifier="pp1",
                group_name="Power Play 1",
                position_identifier="c",
                position_name="Center",
            ),
        ),
    )


def _snapshot():
    return SourceTeamDeploymentSnapshot(
        source=DEPLOYMENT_SOURCE_DAILY_FACEOFF,
        team_abbreviation="TBL",
        team_name="Tampa Bay Lightning",
        team_slug="tampa-bay-lightning",
        source_name="Test",
        source_updated_at=datetime(
            2026,
            9,
            13,
            tzinfo=timezone.utc,
        ),
        source_url="https://example.invalid/test",
        players=(
            _deployment(),
        ),
    )


class CurrentStateEvidenceTests(
    unittest.TestCase
):
    def test_daily_faceoff_slug_controls(self):
        self.assertEqual(
            team_slug_for_nhl_abbr("EDM"),
            "edmonton-oilers",
        )

        self.assertEqual(
            team_slug_for_nhl_abbr("UTA"),
            "utah-mammoth",
        )

        with self.assertRaises(
            DailyFaceoffDeploymentError
        ):
            team_slug_for_nhl_abbr(
                "XXX"
            )


    def test_no_evidence_preserves_baseline(self):
        row = (
            build_current_state_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
            )[0]
        )

        self.assertEqual(
            row.adjustment_state,
            "baseline_only",
        )

        self.assertEqual(
            row.adjusted_fantasy_points_per_game,
            4.0,
        )


    def test_deployment_identity_builds_nhl_map(self):
        mapping = build_deployments_by_nhl_id(
            deployment_snapshots=(
                _snapshot(),
            ),
            nhl_players=(
                _identity(),
            ),
        )

        self.assertEqual(
            set(mapping),
            {1},
        )


    def test_dfo_f1_pp1_adjusts_baseline(self):
        row = (
            build_current_state_projection_adjustments(
                player_strengths=(
                    _strength(),
                ),
                projection_season_id=SEASON,
                deployment_snapshots=(
                    _snapshot(),
                ),
                nhl_players=(
                    _identity(),
                ),
            )[0]
        )

        self.assertEqual(
            row.adjustment_state,
            ADJUSTMENT_APPLIED,
        )

        self.assertAlmostEqual(
            row.deployment_factor,
            1.04,
            places=12,
        )

        self.assertAlmostEqual(
            row.adjusted_fantasy_points_per_game,
            4.16,
            places=12,
        )


    def test_snapshots_require_registry(self):
        with self.assertRaises(
            CurrentStateEvidenceError
        ):
            build_deployments_by_nhl_id(
                deployment_snapshots=(
                    _snapshot(),
                ),
                nhl_players=(),
            )


if __name__ == "__main__":
    unittest.main()
