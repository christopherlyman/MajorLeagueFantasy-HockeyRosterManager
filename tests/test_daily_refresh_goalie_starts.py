from __future__ import annotations

import unittest
from contextlib import ExitStack
from datetime import (
    date,
    timedelta,
)
from types import SimpleNamespace
from unittest.mock import patch

import hockey_rmt.services.daily_refresh as module


BASE_DATE = date(
    2026,
    9,
    29,
)


def _player():
    return SimpleNamespace(
        provider_player_key="477.p.test",
    )


def _strength():
    return SimpleNamespace(
        provider_player_key="477.p.test",
    )


def _kwargs():
    return {
        "players": (
            _player(),
        ),
        "player_strengths": (
            _strength(),
        ),
        "nhl_teams": (),
        "games": (),
        "market_states": (),
        "percent_rostered_by_player_key": {},
        "projection_season_id": 20262027,
        "base_date": BASE_DATE,
        "managed_team_key": "477.l.10961.t.1",
        "league_name": "NFHL",
        "team_name": "Drop The Gloves",
        "model_label": "test",
        "projection_adjustments": (),
    }


class DailyRefreshGoalieStartTests(
    unittest.TestCase
):
    def test_exact_three_day_goalie_mappings_reach_matching_dates(
        self,
    ):
        day0 = {
            1: object(),
        }
        day1 = {
            2: object(),
        }
        day2 = {}

        goalie_by_date = {
            BASE_DATE: day0,
            BASE_DATE
            + timedelta(
                days=1
            ): day1,
            BASE_DATE
            + timedelta(
                days=2
            ): day2,
        }

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    module,
                    "build_yahoo_nhl_crosswalk",
                    return_value=(),
                )
            )

            stack.enter_context(
                patch.object(
                    module,
                    "build_player_game_context",
                    return_value=(
                        SimpleNamespace(
                            provider_player_key=(
                                "477.p.test"
                            )
                        )
                    ),
                )
            )

            daily = stack.enter_context(
                patch.object(
                    module,
                    "build_baseline_daily_expected_values",
                    side_effect=(
                        ("day0",),
                        ("day1",),
                        ("day2",),
                    ),
                )
            )

            stack.enter_context(
                patch.object(
                    module,
                    "build_three_day_player_rankings",
                    return_value=(),
                )
            )

            stack.enter_context(
                patch.object(
                    module,
                    "build_three_day_snapshot_payload",
                    return_value={
                        "rows": [],
                    },
                )
            )

            for name in (
                "enrich_three_day_snapshot_availability",
                "enrich_three_day_snapshot_market",
                "enrich_three_day_snapshot_percent_rostered",
            ):
                stack.enter_context(
                    patch.object(
                        module,
                        name,
                        side_effect=(
                            lambda payload, **kwargs: payload
                        ),
                    )
                )

            kwargs = _kwargs()
            kwargs[
                "goalie_starts_by_date"
            ] = goalie_by_date

            module.build_three_day_refresh_payload(
                **kwargs
            )

        self.assertEqual(
            daily.call_count,
            3,
        )

        calls = daily.call_args_list

        self.assertEqual(
            calls[0].kwargs[
                "goalie_starts_by_nhl_id"
            ],
            day0,
        )

        self.assertEqual(
            calls[1].kwargs[
                "goalie_starts_by_nhl_id"
            ],
            day1,
        )

        self.assertEqual(
            calls[2].kwargs[
                "goalie_starts_by_nhl_id"
            ],
            day2,
        )

    def test_partial_goalie_date_coverage_fails_closed(
        self,
    ):
        kwargs = _kwargs()

        kwargs[
            "goalie_starts_by_date"
        ] = {
            BASE_DATE: {},
            BASE_DATE
            + timedelta(
                days=1
            ): {},
        }

        with self.assertRaisesRegex(
            module.DailyRefreshError,
            "did not exactly match",
        ):
            module.build_three_day_refresh_payload(
                **kwargs
            )

    def test_omitted_goalie_mapping_preserves_legacy_call(
        self,
    ):
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    module,
                    "build_yahoo_nhl_crosswalk",
                    return_value=(),
                )
            )

            stack.enter_context(
                patch.object(
                    module,
                    "build_player_game_context",
                    return_value=(
                        SimpleNamespace(
                            provider_player_key=(
                                "477.p.test"
                            )
                        )
                    ),
                )
            )

            daily = stack.enter_context(
                patch.object(
                    module,
                    "build_baseline_daily_expected_values",
                    return_value=(),
                )
            )

            stack.enter_context(
                patch.object(
                    module,
                    "build_three_day_player_rankings",
                    return_value=(),
                )
            )

            stack.enter_context(
                patch.object(
                    module,
                    "build_three_day_snapshot_payload",
                    return_value={
                        "rows": [],
                    },
                )
            )

            for name in (
                "enrich_three_day_snapshot_availability",
                "enrich_three_day_snapshot_market",
                "enrich_three_day_snapshot_percent_rostered",
            ):
                stack.enter_context(
                    patch.object(
                        module,
                        name,
                        side_effect=(
                            lambda payload, **kwargs: payload
                        ),
                    )
                )

            module.build_three_day_refresh_payload(
                **_kwargs()
            )

        self.assertEqual(
            daily.call_count,
            3,
        )

        for call in daily.call_args_list:
            self.assertIsNone(
                call.kwargs[
                    "goalie_starts_by_nhl_id"
                ]
            )


if __name__ == "__main__":
    unittest.main()
