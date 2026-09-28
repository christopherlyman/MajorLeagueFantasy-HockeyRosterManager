from __future__ import annotations

import unittest

from hockey_rmt.providers.fleaflicker.roster import (
    FleaflickerRosterError,
    fetch_team_roster,
    parse_roster,
)


def _payload():
    return {
        "groups": [
            {
                "group": "START",
                "slots": [
                    {
                        "position": {
                            "label": "F",
                        },
                        "leaguePlayer": {
                            "proPlayer": {
                                "id": 3085,
                                "nameFull": (
                                    "Elias Lindholm"
                                ),
                                "proTeamAbbreviation": (
                                    "BOS"
                                ),
                                "position": "C",
                                "positionEligibility": [
                                    "C",
                                ],
                                "proTeam": {
                                    "name": "Bruins",
                                },
                            }
                        },
                    },
                    {
                        "position": {
                            "label": "LW",
                        },
                        "leaguePlayer": {
                            "proPlayer": {
                                "id": 8159,
                                "nameFull": (
                                    "Cole Caufield"
                                ),
                                "proTeamAbbreviation": (
                                    "MTL"
                                ),
                                "position": "W",
                                "positionEligibility": [
                                    "LW",
                                    "RW",
                                ],
                                "proTeam": {
                                    "name": (
                                        "Canadiens"
                                    ),
                                },
                            }
                        },
                    },
                ],
            },
            {
                "group": "INJURED",
                "slots": [
                    {
                        "position": {
                            "label": "IR",
                        },
                        "leaguePlayer": {
                            "proPlayer": {
                                "id": 9270,
                                "nameFull": (
                                    "Connor Bedard"
                                ),
                                "proTeamAbbreviation": (
                                    "CHI"
                                ),
                                "position": "C",
                                "positionEligibility": [
                                    "C",
                                ],
                                "proTeam": {
                                    "name": (
                                        "Blackhawks"
                                    ),
                                },
                                "injury": {
                                    "severity": "OUT",
                                    "typeFull": "Out",
                                    "description": (
                                        "Shoulder"
                                    ),
                                },
                            }
                        },
                    },
                    {
                        "position": {
                            "label": "IR",
                        }
                    },
                ],
            },
        ]
    }


class _Client:
    def __init__(self):
        self.calls = []

    def get_json(
        self,
        endpoint,
        *,
        params=None,
    ):
        self.calls.append(
            {
                "endpoint": endpoint,
                "params": params,
            }
        )

        return _payload()


class FleaflickerRosterTests(unittest.TestCase):
    def test_parse_live_shape(
        self,
    ):
        rows = parse_roster(
            _payload()
        )

        self.assertEqual(
            len(rows),
            3,
        )

        lindholm = rows[0]

        self.assertEqual(
            lindholm.provider_player_id,
            "3085",
        )
        self.assertEqual(
            lindholm.full_name,
            "Elias Lindholm",
        )
        self.assertEqual(
            lindholm.roster_slot,
            "F",
        )
        self.assertEqual(
            lindholm.eligible_positions,
            ("C",),
        )

        caufield = rows[1]

        self.assertEqual(
            caufield.primary_position,
            "W",
        )
        self.assertEqual(
            caufield.eligible_positions,
            (
                "LW",
                "RW",
            ),
        )

        bedard = rows[2]

        self.assertEqual(
            bedard.roster_slot,
            "IR",
        )
        self.assertEqual(
            bedard.status,
            "OUT",
        )
        self.assertEqual(
            bedard.status_full,
            "Out - Shoulder",
        )

    def test_duplicate_player_fails(
        self,
    ):
        payload = _payload()

        payload["groups"][0]["slots"].append(
            payload["groups"][0]["slots"][0]
        )

        with self.assertRaisesRegex(
            FleaflickerRosterError,
            "duplicate",
        ):
            parse_roster(payload)

    def test_fetch_roster_uses_official_endpoint(
        self,
    ):
        client = _Client()

        rows = fetch_team_roster(
            client,
            "12090",
            "63197",
            season=2026,
        )

        self.assertEqual(
            len(rows),
            3,
        )

        self.assertEqual(
            client.calls,
            [
                {
                    "endpoint": "FetchRoster",
                    "params": {
                        "sport": "NHL",
                        "league_id": "12090",
                        "team_id": "63197",
                        "season": 2026,
                    },
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
