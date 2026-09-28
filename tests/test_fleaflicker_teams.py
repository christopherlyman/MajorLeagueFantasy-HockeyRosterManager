from __future__ import annotations

import unittest

from hockey_rmt.providers.fleaflicker.teams import (
    FleaflickerTeamsError,
    fetch_league_teams,
    parse_teams,
)


def _payload():
    return {
        "divisions": [
            {
                "teams": [
                    {
                        "id": 63184,
                        "name": "Tbd",
                        "waiverPosition": 14,
                    },
                    {
                        "id": 63197,
                        "name": "Drop The Gloves",
                        "waiverPosition": 7,
                    },
                ]
            }
        ],
        "season": 2026,
        "league": {
            "id": 12090,
            "name": "Yzerman - D3",
        },
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


class FleaflickerTeamTests(unittest.TestCase):
    def test_parse_teams_marks_managed_team(
        self,
    ):
        teams = parse_teams(
            _payload(),
            managed_team_id="63197",
        )

        self.assertEqual(
            len(teams),
            2,
        )

        managed = next(
            team
            for team in teams
            if team.is_owned_by_current_user
        )

        self.assertEqual(
            managed.provider,
            "fleaflicker",
        )
        self.assertEqual(
            managed.provider_team_key,
            "63197",
        )
        self.assertEqual(
            managed.provider_team_id,
            "63197",
        )
        self.assertEqual(
            managed.name,
            "Drop The Gloves",
        )
        self.assertEqual(
            managed.waiver_priority,
            7,
        )
        self.assertIsNone(
            managed.weekly_adds_used
        )

    def test_missing_managed_team_fails(
        self,
    ):
        with self.assertRaisesRegex(
            FleaflickerTeamsError,
            "exactly one managed",
        ):
            parse_teams(
                _payload(),
                managed_team_id="99999",
            )

    def test_duplicate_team_id_fails(
        self,
    ):
        payload = _payload()

        payload["divisions"][0]["teams"].append(
            {
                "id": 63197,
                "name": "Duplicate",
                "waiverPosition": 1,
            }
        )

        with self.assertRaisesRegex(
            FleaflickerTeamsError,
            "duplicate team",
        ):
            parse_teams(
                payload,
                managed_team_id="63197",
            )

    def test_fetch_uses_official_standings_endpoint(
        self,
    ):
        client = _Client()

        teams = fetch_league_teams(
            client,
            "12090",
            managed_team_id="63197",
        )

        self.assertEqual(
            len(teams),
            2,
        )

        self.assertEqual(
            client.calls,
            [
                {
                    "endpoint": (
                        "FetchLeagueStandings"
                    ),
                    "params": {
                        "sport": "NHL",
                        "league_id": "12090",
                    },
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
