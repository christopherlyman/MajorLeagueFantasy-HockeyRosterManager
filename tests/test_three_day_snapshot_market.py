from __future__ import annotations

import json
import tempfile
import unittest

from pathlib import Path

from hockey_rmt.domain.market import (
    PlayerMarketState,
)
from hockey_rmt.domain.player import Player
from hockey_rmt.ui.three_day_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    ThreeDaySnapshotError,
    enrich_three_day_snapshot_market,
    load_three_day_snapshot,
)


def _day():
    return {
        "date": "2026-09-29",
        "team": "EDM",
        "schedule_state": "scheduled",
        "value_state": "available",
        "expected_points": 6.5,
        "rank": 1,
        "opponent": "VAN",
        "home_away": "home",
        "provider_game_id": "game-1",
        "start_time_utc": (
            "2026-09-30T02:00:00+00:00"
        ),
    }


def _payload():
    return {
        "schema_version": (
            SNAPSHOT_SCHEMA_VERSION
        ),
        "league_name": "NFHL",
        "team_name": "Drop The Gloves",
        "model_label": "test",
        "base_date": "2026-09-29",
        "season_id": 20262027,
        "rows": [
            {
                "provider_player_key": "477.p.1",
                "full_name": "Test Player",
                "player_type": "skater",
                "scheduled_games": 3,
                "three_day_expected_points": 19.5,
                "three_day_rank": 1,
                "today": _day(),
                "tomorrow": _day(),
                "day_plus_2": _day(),
            }
        ],
    }


def _player():
    return Player(
        provider="yahoo",
        provider_player_key="477.p.1",
        provider_player_id="1",
        full_name="Test Player",
        nhl_team_key="nhl.t.1",
        nhl_team_name="Edmonton Oilers",
        nhl_team_abbr="EDM",
        position_type="P",
        primary_position="C",
        eligible_positions=(
            "C",
            "F",
            "Util",
        ),
        status=None,
        status_full=None,
        is_undroppable=False,
    )


def _market():
    return PlayerMarketState(
        provider="yahoo",
        provider_league_key="477.l.10961",
        provider_player_key="477.p.1",
        market_state="rostered",
        provider_ownership_type="team",
        owner_team_key="477.l.10961.t.1",
        owner_team_name="Drop The Gloves",
    )


class MarketSnapshotTests(
    unittest.TestCase
):
    def _round_trip(
        self,
        payload,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"

            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            return load_three_day_snapshot(
                path
            )


    def test_enrichment_preserves_original(
        self,
    ):
        original = _payload()

        enriched = (
            enrich_three_day_snapshot_market(
                original,
                players=(_player(),),
                market_states=(_market(),),
                managed_team_key=(
                    "477.l.10961.t.1"
                ),
            )
        )

        row = enriched["rows"][0]

        self.assertEqual(
            row["eligible_positions"],
            ["C", "F", "Util"],
        )

        self.assertEqual(
            row["market_state"],
            "rostered",
        )

        self.assertTrue(
            row["is_on_managed_team"]
        )

        self.assertNotIn(
            "market_state",
            original["rows"][0],
        )


    def test_legacy_snapshot_is_valid(
        self,
    ):
        loaded = self._round_trip(
            _payload()
        )

        self.assertNotIn(
            "market_state",
            loaded["rows"][0],
        )


    def test_complete_market_group_is_valid(
        self,
    ):
        enriched = (
            enrich_three_day_snapshot_market(
                _payload(),
                players=(_player(),),
                market_states=(_market(),),
                managed_team_key=(
                    "477.l.10961.t.1"
                ),
            )
        )

        loaded = self._round_trip(
            enriched
        )

        self.assertEqual(
            loaded["rows"][0][
                "eligible_positions"
            ],
            ["C", "F", "Util"],
        )


    def test_partial_market_group_is_rejected(
        self,
    ):
        payload = _payload()
        payload["rows"][0][
            "market_state"
        ] = "free_agent"

        with self.assertRaises(
            ThreeDaySnapshotError
        ):
            self._round_trip(
                payload
            )


    def test_universe_mismatch_is_rejected(
        self,
    ):
        with self.assertRaises(
            ThreeDaySnapshotError
        ):
            enrich_three_day_snapshot_market(
                _payload(),
                players=(),
                market_states=(),
                managed_team_key=(
                    "477.l.10961.t.1"
                ),
            )


if __name__ == "__main__":
    unittest.main()
