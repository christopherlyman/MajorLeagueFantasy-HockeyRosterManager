from __future__ import annotations

import unittest

from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    PlayerStrengthProjection,
)
from hockey_rmt.services.current_production import (
    CurrentProductionError,
    build_current_season_production,
)


SEASON = 20262027


def _strength(
    *,
    key: str,
    player_type: str,
    nhl_player_id: int | None,
):
    return PlayerStrengthProjection(
        provider_player_key=key,
        full_name=f"Player {key}",
        projection_season_id=SEASON,
        player_type=player_type,
        nhl_player_id=nhl_player_id,
        strength_state=STRENGTH_AVAILABLE,
        projection_source="test",
        source_state="test",
        projected_fantasy_points_per_game=4.0,
    )


class CurrentProductionPlayerTypeTests(
    unittest.TestCase
):
    def test_canonical_p_maps_to_skater(
        self,
    ):
        row = build_current_season_production(
            player_strengths=(
                _strength(
                    key="477.p.1",
                    player_type="P",
                    nhl_player_id=1,
                ),
            ),
            season_values=(),
            season_id=SEASON,
        )[0]

        self.assertEqual(
            row.player_type,
            "skater",
        )

        self.assertEqual(
            row.production_state,
            "no_sample",
        )


    def test_canonical_g_maps_to_goalie(
        self,
    ):
        row = build_current_season_production(
            player_strengths=(
                _strength(
                    key="477.p.2",
                    player_type="G",
                    nhl_player_id=2,
                ),
            ),
            season_values=(),
            season_id=SEASON,
        )[0]

        self.assertEqual(
            row.player_type,
            "goalie",
        )

        self.assertEqual(
            row.production_state,
            "no_sample",
        )


    def test_legacy_analytical_types_remain_accepted(
        self,
    ):
        rows = build_current_season_production(
            player_strengths=(
                _strength(
                    key="477.p.1",
                    player_type="skater",
                    nhl_player_id=1,
                ),
                _strength(
                    key="477.p.2",
                    player_type="goalie",
                    nhl_player_id=2,
                ),
            ),
            season_values=(),
            season_id=SEASON,
        )

        self.assertEqual(
            [
                row.player_type
                for row in rows
            ],
            [
                "skater",
                "goalie",
            ],
        )


    def test_unknown_type_rejected(
        self,
    ):
        with self.assertRaises(
            CurrentProductionError
        ):
            build_current_season_production(
                player_strengths=(
                    _strength(
                        key="477.p.1",
                        player_type="X",
                        nhl_player_id=1,
                    ),
                ),
                season_values=(),
                season_id=SEASON,
            )


if __name__ == "__main__":
    unittest.main()
