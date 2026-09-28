from __future__ import annotations

import unittest

from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    PlayerIdentityResolution,
)
from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    STRENGTH_IDENTITY_UNRESOLVED,
    STRENGTH_NO_PROJECTION,
    PlayerStrengthProjection,
)
from hockey_rmt.services.player_strength import (
    PlayerStrengthError,
    rebind_player_strengths_to_current_provider,
)


SEASON = 20262027


def _player(
    key: str,
    *,
    name: str = "Test Skater",
    player_type: str = "P",
) -> Player:
    return Player(
        provider="fleaflicker",
        provider_player_key=key,
        provider_player_id=key,
        full_name=name,
        nhl_team_key=None,
        nhl_team_name="Test Team",
        nhl_team_abbr="TST",
        position_type=player_type,
        primary_position=(
            "G"
            if player_type == "G"
            else "C"
        ),
        eligible_positions=(
            ("G",)
            if player_type == "G"
            else ("C", "F")
        ),
        status=None,
        status_full=None,
        is_undroppable=False,
    )


def _identity(
    key: str,
    *,
    nhl_player_id: int | None = 12345,
    state: str = "resolved",
) -> PlayerIdentityResolution:
    return PlayerIdentityResolution(
        provider_player_key=key,
        resolution_state=state,
        resolution_method=(
            "unique_name"
            if state == "resolved"
            else None
        ),
        nhl_player_id=nhl_player_id,
        nhl_full_name=(
            "Test Skater"
            if nhl_player_id is not None
            else None
        ),
        nhl_position=(
            "C"
            if nhl_player_id is not None
            else None
        ),
        nhl_team_abbr=(
            "TST"
            if nhl_player_id is not None
            else None
        ),
    )


def _canonical(
    key: str = "477.p.1",
    *,
    nhl_player_id: int | None = 12345,
    player_type: str = "P",
) -> PlayerStrengthProjection:
    return PlayerStrengthProjection(
        provider_player_key=key,
        full_name="Test Skater",
        projection_season_id=SEASON,
        player_type=player_type,
        nhl_player_id=nhl_player_id,
        strength_state=STRENGTH_AVAILABLE,
        projection_source="established_skater",
        source_state="projected",
        projected_fantasy_points_per_game=4.25,
    )


class PlayerStrengthRebindingTests(
    unittest.TestCase
):
    def test_rebinds_strength_by_nhl_id(self):
        result = (
            rebind_player_strengths_to_current_provider(
                players=(
                    _player("3085"),
                ),
                canonical_strengths=(
                    _canonical("477.p.999"),
                ),
                identity_resolutions=(
                    _identity("3085"),
                ),
                projection_season_id=SEASON,
            )
        )

        self.assertEqual(
            len(result),
            1,
        )
        self.assertEqual(
            result[0].provider_player_key,
            "3085",
        )
        self.assertEqual(
            result[0].nhl_player_id,
            12345,
        )
        self.assertEqual(
            result[0].strength_state,
            STRENGTH_AVAILABLE,
        )
        self.assertEqual(
            result[0].projected_fantasy_points_per_game,
            4.25,
        )
        self.assertEqual(
            result[0].projection_source,
            "established_skater",
        )

    def test_unresolved_identity_stays_unprojected(self):
        result = (
            rebind_player_strengths_to_current_provider(
                players=(
                    _player("3085"),
                ),
                canonical_strengths=(
                    _canonical(),
                ),
                identity_resolutions=(
                    _identity(
                        "3085",
                        nhl_player_id=None,
                        state="unresolved",
                    ),
                ),
                projection_season_id=SEASON,
            )
        )

        self.assertEqual(
            result[0].provider_player_key,
            "3085",
        )
        self.assertEqual(
            result[0].strength_state,
            STRENGTH_IDENTITY_UNRESOLVED,
        )
        self.assertIsNone(
            result[0].nhl_player_id
        )
        self.assertIsNone(
            result[0].projected_fantasy_points_per_game
        )

    def test_resolved_player_missing_from_artifact_has_no_projection(self):
        result = (
            rebind_player_strengths_to_current_provider(
                players=(
                    _player("3085"),
                ),
                canonical_strengths=(
                    _canonical(
                        nhl_player_id=99999
                    ),
                ),
                identity_resolutions=(
                    _identity(
                        "3085",
                        nhl_player_id=12345,
                    ),
                ),
                projection_season_id=SEASON,
            )
        )

        self.assertEqual(
            result[0].strength_state,
            STRENGTH_NO_PROJECTION,
        )
        self.assertEqual(
            result[0].nhl_player_id,
            12345,
        )
        self.assertIsNone(
            result[0].projected_fantasy_points_per_game
        )

    def test_duplicate_canonical_nhl_id_fails(self):
        with self.assertRaisesRegex(
            PlayerStrengthError,
            "duplicate NHL playerId",
        ):
            rebind_player_strengths_to_current_provider(
                players=(
                    _player("3085"),
                ),
                canonical_strengths=(
                    _canonical("477.p.1"),
                    _canonical("477.p.2"),
                ),
                identity_resolutions=(
                    _identity("3085"),
                ),
                projection_season_id=SEASON,
            )

    def test_player_type_mismatch_fails(self):
        with self.assertRaisesRegex(
            PlayerStrengthError,
            "player type did not match",
        ):
            rebind_player_strengths_to_current_provider(
                players=(
                    _player(
                        "3085",
                        player_type="G",
                    ),
                ),
                canonical_strengths=(
                    _canonical(
                        player_type="P"
                    ),
                ),
                identity_resolutions=(
                    _identity("3085"),
                ),
                projection_season_id=SEASON,
            )


if __name__ == "__main__":
    unittest.main()
