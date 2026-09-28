from __future__ import annotations

import unittest

from hockey_rmt.domain.player import (
    Player,
)
from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    STRENGTH_LATE_ADDITION_UNPROJECTED,
    PlayerStrengthProjection,
)
from hockey_rmt.services.player_strength import (
    PlayerStrengthError,
    reconcile_player_strengths_for_current_universe,
)


SEASON = 20262027


def _player(
    key: str,
    *,
    name: str = "Test Skater",
    player_type: str = "P",
) -> Player:
    is_goalie = (
        player_type.strip().upper()
        == "G"
    )

    return Player(
        provider="yahoo",
        provider_player_key=key,
        provider_player_id=(
            key.rsplit(
                ".",
                1,
            )[-1]
        ),
        full_name=name,
        nhl_team_key="nhl.t.1",
        nhl_team_name="Test Team",
        nhl_team_abbr="TST",
        position_type=player_type,
        primary_position=(
            "G"
            if is_goalie
            else "C"
        ),
        eligible_positions=(
            ("G",)
            if is_goalie
            else (
                "C",
                "F",
                "Util",
            )
        ),
        status=None,
        status_full=None,
        is_undroppable=False,
    )


def _strength(
    key: str,
    *,
    name: str = "Test Skater",
    player_type: str = "P",
    season: int = SEASON,
) -> PlayerStrengthProjection:
    return PlayerStrengthProjection(
        provider_player_key=key,
        full_name=name,
        projection_season_id=season,
        player_type=player_type,
        nhl_player_id=12345,
        strength_state=(
            STRENGTH_AVAILABLE
        ),
        projection_source=(
            "established_skater"
        ),
        source_state="projected",
        projected_fantasy_points_per_game=(
            4.25
        ),
    )


class PlayerStrengthReconciliationTests(
    unittest.TestCase
):
    def test_exact_universe_preserves_canonical_row(
        self,
    ):
        canonical = _strength(
            "477.p.1"
        )

        result = (
            reconcile_player_strengths_for_current_universe(
                players=(
                    _player(
                        "477.p.1"
                    ),
                ),
                canonical_strengths=(
                    canonical,
                ),
                projection_season_id=(
                    SEASON
                ),
            )
        )

        self.assertEqual(
            result,
            (
                canonical,
            ),
        )

        self.assertIs(
            result[0],
            canonical,
        )

    def test_late_addition_gets_transient_unprojected_strength(
        self,
    ):
        canonical = _strength(
            "477.p.1"
        )

        result = (
            reconcile_player_strengths_for_current_universe(
                players=(
                    _player(
                        "477.p.1"
                    ),
                    _player(
                        "477.p.2",
                        name=(
                            "Benjamin Rautiainen"
                        ),
                    ),
                ),
                canonical_strengths=(
                    canonical,
                ),
                projection_season_id=(
                    SEASON
                ),
            )
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertIs(
            result[0],
            canonical,
        )

        late = result[1]

        self.assertEqual(
            late.provider_player_key,
            "477.p.2",
        )

        self.assertEqual(
            late.full_name,
            "Benjamin Rautiainen",
        )

        self.assertEqual(
            late.strength_state,
            STRENGTH_LATE_ADDITION_UNPROJECTED,
        )

        self.assertIsNone(
            late.nhl_player_id
        )

        self.assertIsNone(
            late.projection_source
        )

        self.assertIsNone(
            late.source_state
        )

        self.assertIsNone(
            late.projected_fantasy_points_per_game
        )

    def test_missing_canonical_player_fails_closed(
        self,
    ):
        with self.assertRaises(
            PlayerStrengthError
        ):
            reconcile_player_strengths_for_current_universe(
                players=(
                    _player(
                        "477.p.2"
                    ),
                ),
                canonical_strengths=(
                    _strength(
                        "477.p.1"
                    ),
                ),
                projection_season_id=(
                    SEASON
                ),
            )

    def test_duplicate_current_player_key_fails(
        self,
    ):
        with self.assertRaises(
            PlayerStrengthError
        ):
            reconcile_player_strengths_for_current_universe(
                players=(
                    _player(
                        "477.p.1"
                    ),
                    _player(
                        "477.p.1"
                    ),
                ),
                canonical_strengths=(
                    _strength(
                        "477.p.1"
                    ),
                ),
                projection_season_id=(
                    SEASON
                ),
            )

    def test_canonical_season_mismatch_fails(
        self,
    ):
        with self.assertRaises(
            PlayerStrengthError
        ):
            reconcile_player_strengths_for_current_universe(
                players=(
                    _player(
                        "477.p.1"
                    ),
                ),
                canonical_strengths=(
                    _strength(
                        "477.p.1",
                        season=20252026,
                    ),
                ),
                projection_season_id=(
                    SEASON
                ),
            )

    def test_existing_player_type_mismatch_fails(
        self,
    ):
        with self.assertRaises(
            PlayerStrengthError
        ):
            reconcile_player_strengths_for_current_universe(
                players=(
                    _player(
                        "477.p.1",
                        player_type="G",
                    ),
                ),
                canonical_strengths=(
                    _strength(
                        "477.p.1",
                        player_type="P",
                    ),
                ),
                projection_season_id=(
                    SEASON
                ),
            )


if __name__ == "__main__":
    unittest.main()
