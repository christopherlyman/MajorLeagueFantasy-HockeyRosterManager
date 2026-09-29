from __future__ import annotations

import unittest
from types import SimpleNamespace

from hockey_rmt.domain.player import Player
from hockey_rmt.providers.fleaflicker.ownership import (
    MARKET_STATE_OWNERSHIP_UNKNOWN,
    build_managed_roster_market_states,
)


def _player(player_id):
    return Player(
        provider="fleaflicker",
        provider_player_key=str(player_id),
        provider_player_id=str(player_id),
        full_name=f"Player {player_id}",
        nhl_team_key=None,
        nhl_team_name="Test",
        nhl_team_abbr="TST",
        position_type="P",
        primary_position="C",
        eligible_positions=("C",),
        status=None,
        status_full=None,
        is_undroppable=None,
    )


class FleaflickerOwnershipTests(
    unittest.TestCase
):
    def test_only_managed_roster_is_claimed(self):
        states = (
            build_managed_roster_market_states(
                players=(
                    _player(1),
                    _player(2),
                    _player(3),
                ),
                roster=(
                    SimpleNamespace(
                        provider_player_id="2"
                    ),
                ),
                league_id="12090",
                managed_team_id="63197",
                managed_team_name=(
                    "Drop The Gloves"
                ),
            )
        )

        by_key = {
            row.provider_player_key: row
            for row in states
        }

        self.assertEqual(
            by_key["2"].market_state,
            "rostered",
        )
        self.assertEqual(
            by_key["2"].owner_team_key,
            "63197",
        )

        self.assertEqual(
            by_key["1"].market_state,
            MARKET_STATE_OWNERSHIP_UNKNOWN,
        )
        self.assertIsNone(
            by_key["1"].owner_team_key
        )

    def test_missing_roster_player_fails(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "absent",
        ):
            build_managed_roster_market_states(
                players=(_player(1),),
                roster=(
                    SimpleNamespace(
                        provider_player_id="2"
                    ),
                ),
                league_id="12090",
                managed_team_id="63197",
                managed_team_name=(
                    "Drop The Gloves"
                ),
            )


if __name__ == "__main__":
    unittest.main()
