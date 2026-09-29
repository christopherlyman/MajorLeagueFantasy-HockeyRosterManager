from __future__ import annotations

import unittest

from hockey_rmt.domain.player import Player
from hockey_rmt.services.market_decision import (
    MarketDecisionError,
    _known_undroppable_state,
)


class PlayerUndroppableStateTests(
    unittest.TestCase
):
    def test_player_can_represent_unknown_state(
        self,
    ):
        player = Player(
            provider="fleaflicker",
            provider_player_key="3085",
            provider_player_id="3085",
            full_name="Elias Lindholm",
            nhl_team_key=None,
            nhl_team_name="Bruins",
            nhl_team_abbr="BOS",
            position_type="P",
            primary_position="C",
            eligible_positions=("C",),
            status=None,
            status_full=None,
            is_undroppable=None,
        )

        self.assertIsNone(
            player.is_undroppable
        )

    def test_known_false_is_droppable(
        self,
    ):
        result = _known_undroppable_state(
            is_undroppable_by_player_key={
                "player-1": False,
            },
            player_key="player-1",
        )

        self.assertFalse(result)

    def test_known_true_is_undroppable(
        self,
    ):
        result = _known_undroppable_state(
            is_undroppable_by_player_key={
                "player-1": True,
            },
            player_key="player-1",
        )

        self.assertTrue(result)

    def test_unknown_state_fails_closed(
        self,
    ):
        with self.assertRaisesRegex(
            MarketDecisionError,
            "Unknown is_undroppable state",
        ):
            _known_undroppable_state(
                is_undroppable_by_player_key={
                    "player-1": None,
                },
                player_key="player-1",
            )

    def test_missing_state_fails_closed(
        self,
    ):
        with self.assertRaisesRegex(
            MarketDecisionError,
            "Missing is_undroppable state",
        ):
            _known_undroppable_state(
                is_undroppable_by_player_key={},
                player_key="player-1",
            )

    def test_invalid_state_fails_closed(
        self,
    ):
        with self.assertRaisesRegex(
            MarketDecisionError,
            "Invalid is_undroppable state",
        ):
            _known_undroppable_state(
                is_undroppable_by_player_key={
                    "player-1": 1,
                },
                player_key="player-1",
            )


if __name__ == "__main__":
    unittest.main()
