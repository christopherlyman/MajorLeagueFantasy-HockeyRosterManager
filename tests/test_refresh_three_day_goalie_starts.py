from __future__ import annotations

import unittest
from datetime import (
    date,
    timedelta,
)
from unittest.mock import (
    call,
    patch,
)

import hockey_rmt.refresh_three_day as module


BASE_DATE = date(
    2026,
    9,
    29,
)


class RefreshThreeDayGoalieStartTests(
    unittest.TestCase
):
    def test_fetches_and_resolves_all_three_dates(
        self,
    ):
        evidence0 = (
            object(),
        )
        evidence1 = (
            object(),
        )
        evidence2 = ()

        resolved0 = {
            1: object(),
        }
        resolved1 = {
            2: object(),
        }
        resolved2 = {}

        with patch.object(
            module,
            "fetch_starting_goalies",
            side_effect=(
                evidence0,
                evidence1,
                evidence2,
            ),
        ) as fetch:
            with patch.object(
                module,
                "build_goalie_starts_by_nhl_id",
                side_effect=(
                    resolved0,
                    resolved1,
                    resolved2,
                ),
            ) as resolve:
                result = (
                    module._fetch_goalie_start_mappings(
                        base_date=BASE_DATE,
                        nhl_player_registry=(
                            "registry",
                        ),
                        nhl_teams=(
                            "teams",
                        ),
                    )
                )

        dates = [
            BASE_DATE
            + timedelta(
                days=offset
            )
            for offset in range(
                3
            )
        ]

        self.assertEqual(
            fetch.call_args_list,
            [
                call(dates[0]),
                call(dates[1]),
                call(dates[2]),
            ],
        )

        self.assertEqual(
            set(result),
            set(dates),
        )

        self.assertEqual(
            result[
                dates[0]
            ],
            resolved0,
        )

        self.assertEqual(
            result[
                dates[1]
            ],
            resolved1,
        )

        self.assertEqual(
            result[
                dates[2]
            ],
            {},
        )

        self.assertEqual(
            resolve.call_count,
            3,
        )

        for index, resolution_call in enumerate(
            resolve.call_args_list
        ):
            self.assertEqual(
                resolution_call.kwargs[
                    "game_date"
                ],
                dates[index],
            )

    def test_provider_failure_aborts_required_window(
        self,
    ):
        with patch.object(
            module,
            "fetch_starting_goalies",
            side_effect=(
                module.DailyFaceoffStartingGoaliesError(
                    "provider down"
                )
            ),
        ):
            with patch.object(
                module,
                "build_goalie_starts_by_nhl_id",
            ) as resolve:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "failed for required date",
                ):
                    module._fetch_goalie_start_mappings(
                        base_date=BASE_DATE,
                        nhl_player_registry=(
                            "registry",
                        ),
                        nhl_teams=(
                            "teams",
                        ),
                    )

        resolve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
