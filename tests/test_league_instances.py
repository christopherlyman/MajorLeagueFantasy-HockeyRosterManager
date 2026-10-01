from __future__ import annotations

import unittest

from hockey_rmt.league_instances import (
    get_league_instance,
    league_instance_keys,
)


class LeagueInstanceTests(unittest.TestCase):
    def test_nfhl_redraft_binding(self):
        instance = get_league_instance("nfhl_redraft")

        self.assertEqual(instance.provider, "yahoo")
        self.assertEqual(
            instance.provider_league_key,
            "477.l.10961",
        )
        self.assertEqual(
            instance.managed_team_key,
            "477.l.10961.t.1",
        )
        self.assertEqual(instance.season_year, 2026)
        self.assertIsNone(instance.competition_level)

    def test_oth_redraft_binding(self):
        instance = get_league_instance("oth_redraft")

        self.assertEqual(
            instance.logical_key,
            "oth_redraft",
        )
        self.assertEqual(
            instance.display_name,
            "OTH Redraft",
        )
        self.assertEqual(
            instance.provider,
            "fleaflicker",
        )
        self.assertEqual(
            instance.provider_league_key,
            "12090",
        )
        self.assertEqual(
            instance.managed_team_key,
            "63197",
        )
        self.assertEqual(instance.season_year, 2026)
        self.assertEqual(
            instance.competition_level,
            "D3",
        )

    def test_configured_keys(self):
        self.assertEqual(
            league_instance_keys(),
            (
                "nfhl_redraft",
                "oth_redraft",
                "oth_keeper",
            ),
        )

    def test_oth_keeper_binding(self):
        instance = get_league_instance(
            "oth_keeper"
        )

        self.assertEqual(
            instance.logical_key,
            "oth_keeper",
        )
        self.assertEqual(
            instance.display_name,
            "OTH Keeper",
        )
        self.assertEqual(
            instance.provider,
            "fleaflicker",
        )
        self.assertEqual(
            instance.provider_league_key,
            "9899",
        )
        self.assertEqual(
            instance.managed_team_key,
            "55165",
        )
        self.assertEqual(
            instance.season_year,
            2026,
        )
        self.assertIsNotNone(
            instance.operational
        )

    def test_blank_key_fails(self):
        with self.assertRaisesRegex(
            ValueError,
            "must not be empty",
        ):
            get_league_instance(" ")
    def test_unknown_logical_key_still_fails(self):
        with self.assertRaisesRegex(
            ValueError,
            "Unknown logical league key",
        ):
            get_league_instance(
                "missing_league"
            )


if __name__ == "__main__":
    unittest.main()
