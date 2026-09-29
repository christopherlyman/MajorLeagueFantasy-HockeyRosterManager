from __future__ import annotations

import unittest

from hockey_rmt.providers.fleaflicker.player_pool import (
    PLAYER_LISTING_SORT,
    FleaflickerPlayerPoolError,
    fetch_all_players,
    parse_player_listing,
)


def _row(
    player_id: int,
    name: str,
    *,
    position: str = "C",
    eligibility: tuple[str, ...] = ("C",),
    display_group: str = "SKATER",
    team_abbr: str = "BOS",
    team_name: str = "Bruins",
    injury=None,
):
    pro_player = {
        "id": player_id,
        "nameFull": name,
        "position": position,
        "positionEligibility": list(
            eligibility
        ),
        "proTeamAbbreviation": team_abbr,
        "proTeam": {
            "abbreviation": team_abbr,
            "name": team_name,
        },
        "sport": "NHL",
    }

    if injury is not None:
        pro_player["injury"] = injury

    return {
        "proPlayer": pro_player,
        "displayGroup": display_group,
    }


class _FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_json(
        self,
        endpoint,
        *,
        params=None,
    ):
        params = dict(params or {})

        self.calls.append(
            (
                endpoint,
                params,
            )
        )

        offset = params[
            "result_offset"
        ]

        return self.pages[offset]


class FleaflickerPlayerPoolTests(
    unittest.TestCase
):
    def test_parse_skater_preserves_generic_w(
        self,
    ):
        result = parse_player_listing(
            {
                "players": [
                    _row(
                        4462,
                        "Jason Robertson",
                        position="W",
                        eligibility=(
                            "LW",
                            "RW",
                        ),
                        team_abbr="DAL",
                        team_name="Stars",
                        injury={
                            "severity": "OUT",
                            "typeFull": "Out",
                            "description": (
                                "Upper-body"
                            ),
                        },
                    )
                ]
            }
        )

        self.assertEqual(
            len(result),
            1,
        )

        player = result[0]

        self.assertEqual(
            player.provider,
            "fleaflicker",
        )
        self.assertEqual(
            player.provider_player_key,
            "4462",
        )
        self.assertEqual(
            player.provider_player_id,
            "4462",
        )
        self.assertEqual(
            player.position_type,
            "P",
        )
        self.assertEqual(
            player.primary_position,
            "W",
        )
        self.assertEqual(
            player.eligible_positions,
            ("LW", "RW"),
        )
        self.assertEqual(
            player.nhl_team_abbr,
            "DAL",
        )
        self.assertEqual(
            player.nhl_team_name,
            "Stars",
        )
        self.assertEqual(
            player.status,
            "OUT",
        )
        self.assertEqual(
            player.status_full,
            "Out - Upper-body",
        )
        self.assertIsNone(
            player.is_undroppable
        )

    def test_parse_goalie_maps_player_type(
        self,
    ):
        player = parse_player_listing(
            {
                "players": [
                    _row(
                        5022,
                        "Lukas Dostal",
                        position="G",
                        eligibility=("G",),
                        display_group="GOALIE",
                        team_abbr="ANA",
                        team_name="Ducks",
                    )
                ]
            }
        )[0]

        self.assertEqual(
            player.position_type,
            "G",
        )
        self.assertEqual(
            player.primary_position,
            "G",
        )
        self.assertEqual(
            player.eligible_positions,
            ("G",),
        )
        self.assertIsNone(player.status)

    def test_missing_eligibility_fails(
        self,
    ):
        row = _row(
            1,
            "Test Player",
        )

        row["proPlayer"][
            "positionEligibility"
        ] = []

        with self.assertRaisesRegex(
            FleaflickerPlayerPoolError,
            "eligible positions",
        ):
            parse_player_listing(
                {
                    "players": [row],
                }
            )

    def test_unknown_display_group_fails(
        self,
    ):
        with self.assertRaisesRegex(
            FleaflickerPlayerPoolError,
            "Unexpected Fleaflicker display group",
        ):
            parse_player_listing(
                {
                    "players": [
                        _row(
                            1,
                            "Test Player",
                            display_group="OTHER",
                        )
                    ]
                }
            )

    def test_fetch_trims_final_page_overflow(
        self,
    ):
        client = _FakeClient(
            {
                0: {
                    "resultTotal": 4,
                    "resultOffsetNext": 3,
                    "players": [
                        _row(1, "Player One"),
                        _row(2, "Player Two"),
                        _row(3, "Player Three"),
                    ],
                },
                3: {
                    "resultTotal": 4,
                    "resultOffsetNext": 6,
                    "players": [
                        _row(4, "Player Four"),
                        _row(1, "Overflow One"),
                        _row(2, "Overflow Two"),
                    ],
                },
            }
        )

        players = fetch_all_players(
            client,
            "12090",
            season=2026,
        )

        self.assertEqual(
            tuple(
                player.provider_player_key
                for player in players
            ),
            ("1", "2", "3", "4"),
        )

        self.assertEqual(
            len(client.calls),
            2,
        )

        first_endpoint, first_params = (
            client.calls[0]
        )

        self.assertEqual(
            first_endpoint,
            "FetchPlayerListing",
        )
        self.assertEqual(
            first_params,
            {
                "sport": "NHL",
                "league_id": "12090",
                "sort": PLAYER_LISTING_SORT,
                "sort_season": 2026,
                "result_offset": 0,
            },
        )

        self.assertEqual(
            client.calls[1][1][
                "result_offset"
            ],
            3,
        )

    def test_duplicate_inside_valid_window_fails(
        self,
    ):
        client = _FakeClient(
            {
                0: {
                    "resultTotal": 4,
                    "resultOffsetNext": 3,
                    "players": [
                        _row(1, "Player One"),
                        _row(2, "Player Two"),
                        _row(3, "Player Three"),
                    ],
                },
                3: {
                    "resultTotal": 4,
                    "resultOffsetNext": 6,
                    "players": [
                        _row(3, "Player Three"),
                        _row(4, "Player Four"),
                    ],
                },
            }
        )

        with self.assertRaisesRegex(
            FleaflickerPlayerPoolError,
            "inside the valid result window",
        ):
            fetch_all_players(
                client,
                "12090",
                season=2026,
            )

    def test_result_total_change_fails(
        self,
    ):
        client = _FakeClient(
            {
                0: {
                    "resultTotal": 4,
                    "resultOffsetNext": 3,
                    "players": [
                        _row(1, "Player One"),
                        _row(2, "Player Two"),
                        _row(3, "Player Three"),
                    ],
                },
                3: {
                    "resultTotal": 5,
                    "resultOffsetNext": 6,
                    "players": [
                        _row(4, "Player Four"),
                    ],
                },
            }
        )

        with self.assertRaisesRegex(
            FleaflickerPlayerPoolError,
            "resultTotal changed",
        ):
            fetch_all_players(
                client,
                "12090",
                season=2026,
            )

    def test_missing_next_offset_before_total_fails(
        self,
    ):
        client = _FakeClient(
            {
                0: {
                    "resultTotal": 4,
                    "players": [
                        _row(1, "Player One"),
                        _row(2, "Player Two"),
                    ],
                },
            }
        )

        with self.assertRaisesRegex(
            FleaflickerPlayerPoolError,
            "ended before resultTotal",
        ):
            fetch_all_players(
                client,
                "12090",
                season=2026,
            )


if __name__ == "__main__":
    unittest.main()
