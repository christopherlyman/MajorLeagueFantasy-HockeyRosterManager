from __future__ import annotations

import unittest

from hockey_rmt.providers.yahoo.percent_rostered import (
    YahooPercentRosteredError,
    parse_player_percent_rostered,
)


def _payload(
    percent_owned,
):
    return {
        "fantasy_content": {
            "league": [
                {
                    "league_key": (
                        "477.l.10961"
                    )
                },
                {
                    "players": {
                        "0": {
                            "player": [
                                {
                                    "player_key": (
                                        "477.p.1"
                                    )
                                },
                                {
                                    "percent_owned": (
                                        percent_owned
                                    )
                                },
                            ]
                        },
                        "count": 1,
                    }
                },
            ]
        }
    }


class YahooPercentRosteredTests(
    unittest.TestCase
):
    def test_explicit_percent(
        self,
    ):
        result = (
            parse_player_percent_rostered(
                _payload(
                    [
                        {
                            "coverage_type": (
                                "week"
                            ),
                            "week": 1,
                        },
                        {
                            "value": 98,
                        },
                        {
                            "delta": "0",
                        },
                    ]
                )
            )
        )

        self.assertEqual(
            result,
            {
                "477.p.1": 98,
            },
        )


    def test_missing_value_means_zero(
        self,
    ):
        result = (
            parse_player_percent_rostered(
                _payload(
                    [
                        {
                            "coverage_type": (
                                "week"
                            ),
                            "week": 1,
                        },
                        {
                            "delta": "0",
                        },
                    ]
                )
            )
        )

        self.assertEqual(
            result,
            {
                "477.p.1": 0,
            },
        )


    def test_rejects_non_week_coverage(
        self,
    ):
        with self.assertRaises(
            YahooPercentRosteredError
        ):
            parse_player_percent_rostered(
                _payload(
                    [
                        {
                            "coverage_type": (
                                "season"
                            ),
                        },
                        {
                            "value": 50,
                        },
                    ]
                )
            )


    def test_rejects_out_of_range(
        self,
    ):
        with self.assertRaises(
            YahooPercentRosteredError
        ):
            parse_player_percent_rostered(
                _payload(
                    [
                        {
                            "coverage_type": (
                                "week"
                            ),
                            "week": 1,
                        },
                        {
                            "value": 101,
                        },
                    ]
                )
            )


    def test_rejects_fractional_percent(
        self,
    ):
        with self.assertRaises(
            YahooPercentRosteredError
        ):
            parse_player_percent_rostered(
                _payload(
                    [
                        {
                            "coverage_type": (
                                "week"
                            ),
                            "week": 1,
                        },
                        {
                            "value": "12.5",
                        },
                    ]
                )
            )


if __name__ == "__main__":
    unittest.main()
