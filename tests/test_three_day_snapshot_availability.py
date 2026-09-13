from __future__ import annotations

from copy import deepcopy
import json
import tempfile
import unittest

from pathlib import Path
from types import SimpleNamespace

from hockey_rmt.ui.three_day_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    ThreeDaySnapshotError,
    enrich_three_day_snapshot_availability,
    load_three_day_snapshot,
)


def _players():
    return (
        SimpleNamespace(
            provider="yahoo",
            provider_player_key="477.p.1",
            status="NA",
            status_full="Not Active",
        ),
        SimpleNamespace(
            provider="yahoo",
            provider_player_key="477.p.2",
            status="DTD",
            status_full="Day-to-Day",
        ),
    )


def _minimal_enrichment_payload():
    return {
        "rows": [
            {
                "provider_player_key": (
                    "477.p.1"
                ),
            },
            {
                "provider_player_key": (
                    "477.p.2"
                ),
            },
        ],
    }


def _day(
    value_date: str,
):
    return {
        "date": value_date,
        "team": "TBL",
        "schedule_state": "off",
        "value_state": "off",
        "expected_points": 0.0,
        "rank": None,
        "opponent": None,
        "home_away": None,
    }


def _row(
    key: str,
):
    return {
        "provider_player_key": key,
        "full_name": "Test Player",
        "player_type": "P",
        "scheduled_games": 0,
        "three_day_expected_points": 0.0,
        "three_day_rank": None,
        "today": _day(
            "2026-09-29"
        ),
        "tomorrow": _day(
            "2026-09-30"
        ),
        "day_plus_2": _day(
            "2026-10-01"
        ),
    }


def _payload(
    rows,
):
    return {
        "schema_version": (
            SNAPSHOT_SCHEMA_VERSION
        ),
        "league_name": "NFHL",
        "team_name": "Drop The Gloves",
        "model_label": "test",
        "base_date": "2026-09-29",
        "season_id": 20262027,
        "rows": rows,
    }


def _load_payload(
    payload,
):
    with tempfile.TemporaryDirectory() as tmp:
        path = (
            Path(tmp)
            / "snapshot.json"
        )

        path.write_text(
            json.dumps(
                payload
            ),
            encoding="utf-8",
        )

        return load_three_day_snapshot(
            path
        )


class ThreeDayAvailabilitySnapshotTests(
    unittest.TestCase
):
    def test_enrichment_preserves_original(
        self,
    ):
        payload = (
            _minimal_enrichment_payload()
        )

        original = deepcopy(
            payload
        )

        enriched = (
            enrich_three_day_snapshot_availability(
                payload,
                players=_players(),
            )
        )

        self.assertEqual(
            payload,
            original,
        )

        self.assertEqual(
            enriched[
                "rows"
            ][0][
                "availability_state"
            ],
            "unavailable",
        )

        self.assertEqual(
            enriched[
                "rows"
            ][0][
                "provider_status"
            ],
            "NA",
        )

        self.assertEqual(
            enriched[
                "rows"
            ][1][
                "availability_state"
            ],
            "uncertain",
        )


    def test_universe_mismatch_rejected(
        self,
    ):
        with self.assertRaises(
            ThreeDaySnapshotError
        ):
            enrich_three_day_snapshot_availability(
                _minimal_enrichment_payload(),
                players=(
                    _players()[0],
                ),
            )


    def test_duplicate_player_key_rejected(
        self,
    ):
        player = _players()[0]

        with self.assertRaises(
            ThreeDaySnapshotError
        ):
            enrich_three_day_snapshot_availability(
                {
                    "rows": [
                        {
                            "provider_player_key": (
                                "477.p.1"
                            ),
                        },
                    ],
                },
                players=(
                    player,
                    player,
                ),
            )


    def test_complete_group_loads(
        self,
    ):
        row = _row(
            "477.p.1"
        )

        row.update(
            {
                "availability_state": (
                    "unavailable"
                ),
                "provider_status": "O",
                "provider_status_full": "Out",
            }
        )

        loaded = _load_payload(
            _payload(
                [
                    row,
                ]
            )
        )

        self.assertEqual(
            loaded[
                "rows"
            ][0][
                "availability_state"
            ],
            "unavailable",
        )


    def test_partial_group_rejected(
        self,
    ):
        row = _row(
            "477.p.1"
        )

        row[
            "availability_state"
        ] = "unavailable"

        with self.assertRaises(
            ThreeDaySnapshotError
        ):
            _load_payload(
                _payload(
                    [
                        row,
                    ]
                )
            )


    def test_mixed_coverage_rejected(
        self,
    ):
        first = _row(
            "477.p.1"
        )

        second = _row(
            "477.p.2"
        )

        first.update(
            {
                "availability_state": (
                    "uncertain"
                ),
                "provider_status": "DTD",
                "provider_status_full": (
                    "Day-to-Day"
                ),
            }
        )

        with self.assertRaises(
            ThreeDaySnapshotError
        ):
            _load_payload(
                _payload(
                    [
                        first,
                        second,
                    ]
                )
            )


    def test_invalid_state_rejected(
        self,
    ):
        row = _row(
            "477.p.1"
        )

        row.update(
            {
                "availability_state": "mystery",
                "provider_status": "X",
                "provider_status_full": None,
            }
        )

        with self.assertRaises(
            ThreeDaySnapshotError
        ):
            _load_payload(
                _payload(
                    [
                        row,
                    ]
                )
            )


if __name__ == "__main__":
    unittest.main()
