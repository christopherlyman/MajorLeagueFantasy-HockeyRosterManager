from __future__ import annotations

import json
import math
import tempfile
import unittest

from dataclasses import replace
from pathlib import Path

from hockey_rmt.domain.player_strength import (
    PlayerStrengthProjection,
)
from hockey_rmt.services.player_strength_snapshot import (
    PlayerStrengthSnapshotError,
    build_player_strength_snapshot_payload,
    load_player_strength_snapshot,
    write_player_strength_snapshot,
)


SEASON_ID = 20262027


def _rows():
    return (
        PlayerStrengthProjection(
            provider_player_key="477.p.1",
            full_name="Available Player",
            projection_season_id=SEASON_ID,
            player_type="P",
            nhl_player_id=8470001,
            strength_state="available",
            projection_source=(
                "established_skater"
            ),
            source_state="projected",
            projected_fantasy_points_per_game=(
                5.125
            ),
        ),
        PlayerStrengthProjection(
            provider_player_key="477.p.2",
            full_name="Unresolved Player",
            projection_season_id=SEASON_ID,
            player_type="P",
            nhl_player_id=None,
            strength_state=(
                "identity_unresolved"
            ),
            projection_source=None,
            source_state=None,
            projected_fantasy_points_per_game=(
                None
            ),
        ),
    )


class PlayerStrengthSnapshotTests(
    unittest.TestCase
):
    def test_round_trip(
        self,
    ):
        rows = _rows()

        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "strengths.json"
            )

            written = (
                write_player_strength_snapshot(
                    rows=rows,
                    projection_season_id=(
                        SEASON_ID
                    ),
                    path=path,
                )
            )

            self.assertEqual(
                written,
                path,
            )

            loaded = (
                load_player_strength_snapshot(
                    path,
                    expected_projection_season_id=(
                        SEASON_ID
                    ),
                )
            )

        self.assertEqual(
            loaded,
            rows,
        )


    def test_negative_projection_is_preserved(
        self,
    ):
        first = replace(
            _rows()[0],
            projected_fantasy_points_per_game=(
                -1.25
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "strengths.json"
            )

            write_player_strength_snapshot(
                rows=(
                    first,
                ),
                projection_season_id=(
                    SEASON_ID
                ),
                path=path,
            )

            loaded = (
                load_player_strength_snapshot(
                    path,
                    expected_projection_season_id=(
                        SEASON_ID
                    ),
                )
            )

        self.assertEqual(
            loaded[
                0
            ].projected_fantasy_points_per_game,
            -1.25,
        )


    def test_duplicate_player_key_rejected(
        self,
    ):
        first = _rows()[0]

        with self.assertRaises(
            PlayerStrengthSnapshotError
        ):
            build_player_strength_snapshot_payload(
                rows=(
                    first,
                    replace(
                        first,
                        full_name="Duplicate",
                    ),
                ),
                projection_season_id=(
                    SEASON_ID
                ),
            )


    def test_row_season_mismatch_rejected(
        self,
    ):
        first = _rows()[0]

        with self.assertRaises(
            PlayerStrengthSnapshotError
        ):
            build_player_strength_snapshot_payload(
                rows=(
                    replace(
                        first,
                        projection_season_id=(
                            20252026
                        ),
                    ),
                ),
                projection_season_id=(
                    SEASON_ID
                ),
            )


    def test_nonfinite_projection_rejected(
        self,
    ):
        first = _rows()[0]

        for value in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    PlayerStrengthSnapshotError
                ):
                    build_player_strength_snapshot_payload(
                        rows=(
                            replace(
                                first,
                                projected_fantasy_points_per_game=(
                                    value
                                ),
                            ),
                        ),
                        projection_season_id=(
                            SEASON_ID
                        ),
                    )


    def test_loader_rejects_wrong_expected_season(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "strengths.json"
            )

            write_player_strength_snapshot(
                rows=_rows(),
                projection_season_id=(
                    SEASON_ID
                ),
                path=path,
            )

            with self.assertRaises(
                PlayerStrengthSnapshotError
            ):
                load_player_strength_snapshot(
                    path,
                    expected_projection_season_id=(
                        20252026
                    ),
                )


    def test_loader_rejects_duplicate_keys(
        self,
    ):
        payload = (
            build_player_strength_snapshot_payload(
                rows=_rows(),
                projection_season_id=(
                    SEASON_ID
                ),
            )
        )

        payload[
            "rows"
        ].append(
            dict(
                payload[
                    "rows"
                ][0]
            )
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "strengths.json"
            )

            path.write_text(
                json.dumps(
                    payload
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                PlayerStrengthSnapshotError
            ):
                load_player_strength_snapshot(
                    path
                )


if __name__ == "__main__":
    unittest.main()
