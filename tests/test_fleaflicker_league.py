from __future__ import annotations

import unittest
from datetime import date

from hockey_rmt.league_instances import (
    LeagueOperationalConfig,
    get_league_instance,
)
from hockey_rmt.providers.fleaflicker.league import (
    parse_league_definition,
)


def _operational():
    return LeagueOperationalConfig(
        scoring_format="head_to_head_points",
        roster_period="daily",
        lineup_deadline="game_start",
        start_date=date(2026, 9, 29),
        end_date=date(2027, 4, 10),
        max_weekly_adds=7,
        waiver_type="rolling_priority",
        waiver_rule=(
            "all_players_after_game_start"
        ),
        waiver_days=1,
        uses_faab=False,
        playoff_teams=6,
        playoff_start_week=24,
    )


def _standings():
    return {
        "season": 2026,
        "league": {
            "id": 12090,
            "name": "Yzerman - D3",
            "sport": "NHL",
            "size": 14,
            "rosterRequirements": {
                "starterCount": 14,
                "benchCount": 4,
                "positions": [
                    {
                        "label": "C",
                        "group": "START",
                        "eligibility": ["C"],
                        "start": 2,
                    },
                    {
                        "label": "LW",
                        "group": "START",
                        "eligibility": ["LW"],
                        "start": 2,
                    },
                    {
                        "label": "RW",
                        "group": "START",
                        "eligibility": ["RW"],
                        "start": 2,
                    },
                    {
                        "label": "F",
                        "group": "START",
                        "eligibility": [
                            "C", "LW", "RW"
                        ],
                        "start": 1,
                    },
                    {
                        "label": "D",
                        "group": "START",
                        "eligibility": ["D"],
                        "start": 4,
                    },
                    {
                        "label": "F/D",
                        "group": "START",
                        "eligibility": [
                            "C", "LW", "RW", "D"
                        ],
                        "start": 1,
                    },
                    {
                        "label": "G",
                        "group": "START",
                        "eligibility": ["G"],
                        "start": 2,
                    },
                    {
                        "label": "IR",
                        "group": "INJURED",
                        "eligibility": [
                            "C", "LW", "RW", "D", "G"
                        ],
                        "start": 2,
                    },
                    {
                        "label": "BN",
                        "max": 4,
                    },
                ],
            },
        },
    }


def _rule(
    stat_id,
    abbreviation,
    name,
    points,
    *,
    for_every=1,
):
    return {
        "category": {
            "id": stat_id,
            "abbreviation": abbreviation,
            "nameSingular": name,
        },
        "points": {
            "value": points,
        },
        "forEvery": for_every,
    }


def _rules():
    return {
        "numStarters": 14,
        "numBench": 4,
        "groups": [
            {
                "label": "Offense",
                "scoringRules": [
                    _rule(1, "G", "Goal", 4),
                    _rule(2, "Ast", "Assist", 2.5),
                    _rule(3, "PIM", "Penalty Minute", .2),
                    _rule(36, "PPP", "Power Play Point", 1),
                    _rule(37, "SHP", "Short Handed Point", 1.25),
                    _rule(4, "SOG", "Shot on Goal", .25),
                ],
            },
            {
                "label": "Defense",
                "scoringRules": [
                    _rule(13, "Hit", "Hit", .4),
                    _rule(14, "Blk", "Block", .4),
                ],
            },
            {
                "label": "Goaltending",
                "scoringRules": [
                    _rule(19, "W", "Win", 3),
                    _rule(20, "L", "Loss", -3, for_every=2),
                    _rule(22, "OTL", "OT Loss", 1),
                    _rule(23, "SO", "Shutout", 5, for_every=2),
                    _rule(26, "SV", "Save", 5, for_every=20),
                    _rule(27, "GA", "Goal Against", -1),
                ],
            },
        ],
    }


class FleaflickerLeagueTests(unittest.TestCase):
    def test_oth_instance_has_operational_config(self):
        instance = get_league_instance(
            "oth_redraft"
        )

        self.assertIsNotNone(
            instance.operational
        )

        self.assertEqual(
            instance.operational.max_weekly_adds,
            7,
        )

    def test_normalizes_roster_and_scoring(self):
        league = parse_league_definition(
            _rules(),
            _standings(),
            operational=_operational(),
        )

        self.assertEqual(
            league.provider,
            "fleaflicker",
        )
        self.assertEqual(
            league.provider_league_key,
            "12090",
        )

        starters = {
            row.position: row.count
            for row in league.roster_positions
            if row.is_starting
        }

        self.assertEqual(
            starters,
            {
                "C": 2,
                "LW": 2,
                "RW": 2,
                "F": 1,
                "D": 4,
                "F/D": 1,
                "G": 2,
            },
        )

        scoring = {
            (
                row.position_type,
                row.abbreviation,
            ): row.points
            for row in league.scoring_rules
        }

        expected = {
            ("P", "G"): 4.0,
            ("P", "A"): 2.5,
            ("P", "PIM"): 0.2,
            ("P", "PPP"): 1.0,
            ("P", "SHP"): 1.25,
            ("P", "SOG"): 0.25,
            ("P", "HIT"): 0.4,
            ("P", "BLK"): 0.4,
            ("G", "W"): 3.0,
            ("G", "L"): -1.5,
            ("G", "OTL"): 1.0,
            ("G", "SHO"): 2.5,
            ("G", "SV"): 0.25,
            ("G", "GA"): -1.0,
        }

        self.assertEqual(
            scoring,
            expected,
        )


if __name__ == "__main__":
    unittest.main()
