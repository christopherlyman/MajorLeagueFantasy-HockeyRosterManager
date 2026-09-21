from __future__ import annotations

import unittest
from datetime import (
    date,
    datetime,
    timezone,
)
from types import SimpleNamespace

from hockey_rmt.domain.daily_value import (
    DAILY_VALUE_AVAILABLE,
    DAILY_VALUE_GOALIE_START_LIKELY,
    DAILY_VALUE_GOALIE_START_UNCONFIRMED,
    DAILY_VALUE_GOALIE_START_UNKNOWN,
    DAILY_VALUE_OFF,
)
from hockey_rmt.domain.goalie_start import (
    GOALIE_START_CONFIRMED,
    GOALIE_START_LIKELY,
    GOALIE_START_SOURCE_DAILY_FACEOFF,
    GOALIE_START_UNCONFIRMED,
    DailyGoalieStartEvidence,
)
from hockey_rmt.services.daily_value import (
    DailyValueError,
    build_baseline_daily_expected_values,
)


SEASON = 20262027
GAME_DATE = date(
    2026,
    3,
    14,
)
NHL_GOALIE_ID = 8476883


def _strength(
    *,
    player_type: str = "G",
    nhl_player_id: int | None = NHL_GOALIE_ID,
    fppg: float = 4.75,
):
    return SimpleNamespace(
        provider_player_key="477.p.test",
        full_name="Test Player",
        projection_season_id=SEASON,
        player_type=player_type,
        nhl_player_id=nhl_player_id,
        projected_fantasy_points_per_game=fppg,
        strength_state="available",
    )


def _context(
    *,
    schedule_state: str = "scheduled",
    availability_state: str = "available",
):
    scheduled = (
        schedule_state
        == "scheduled"
    )

    return SimpleNamespace(
        provider_player_key="477.p.test",
        game_date=GAME_DATE,
        schedule_state=schedule_state,
        availability_state=(
            availability_state
        ),
        nhl_team_abbr="TBL",
        provider_game_id=(
            "20260314-TBL-CAR"
            if scheduled
            else None
        ),
        opponent_team_abbr=(
            "CAR"
            if scheduled
            else None
        ),
        home_away=(
            "home"
            if scheduled
            else None
        ),
        start_time_utc=(
            datetime(
                2026,
                3,
                14,
                23,
                0,
                tzinfo=timezone.utc,
            )
            if scheduled
            else None
        ),
        provider_status=None,
        provider_status_full=None,
    )


def _evidence(
    *,
    start_state: str,
    game_date: date = GAME_DATE,
):
    return DailyGoalieStartEvidence(
        source=(
            GOALIE_START_SOURCE_DAILY_FACEOFF
        ),
        game_date=game_date,
        game_time_utc=datetime(
            2026,
            3,
            14,
            23,
            0,
            tzinfo=timezone.utc,
        ),
        is_home=True,
        provider_goalie_id=2413,
        goalie_name="Andrei Vasilevskiy",
        provider_team_id=27,
        team_name="Tampa Bay Lightning",
        provider_opponent_team_id=6,
        opponent_team_name="Carolina Hurricanes",
        start_state=start_state,
        evidence_created_at_utc=datetime(
            2026,
            3,
            14,
            14,
            45,
            tzinfo=timezone.utc,
        ),
        evidence_source_name="Source",
        evidence_source_url=(
            "https://example.test/source"
        ),
    )


def _build(
    *,
    strength=None,
    context=None,
    goalie_mapping_marker=None,
):
    kwargs = dict(
        player_strengths=(
            strength
            if strength is not None
            else _strength(),
        ),
        game_contexts=(
            context
            if context is not None
            else _context(),
        ),
        season_id=SEASON,
        game_date=GAME_DATE,
    )

    if goalie_mapping_marker is not None:
        kwargs[
            "goalie_starts_by_nhl_id"
        ] = goalie_mapping_marker

    return (
        build_baseline_daily_expected_values(
            **kwargs
        )[0]
    )


class DailyValueGoalieStartTests(
    unittest.TestCase
):
    def test_legacy_goalie_path_is_unchanged_when_mapping_omitted(
        self,
    ):
        row = _build()

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_AVAILABLE,
        )
        self.assertEqual(
            row.expected_fantasy_points,
            4.75,
        )
        self.assertIsNone(
            row.goalie_start_state
        )

    def test_confirmed_goalie_receives_per_start_value(
        self,
    ):
        evidence = _evidence(
            start_state=(
                GOALIE_START_CONFIRMED
            )
        )

        row = _build(
            goalie_mapping_marker={
                NHL_GOALIE_ID: evidence,
            }
        )

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_AVAILABLE,
        )
        self.assertEqual(
            row.expected_fantasy_points,
            4.75,
        )
        self.assertEqual(
            row.goalie_start_state,
            GOALIE_START_CONFIRMED,
        )
        self.assertEqual(
            row.goalie_start_source,
            GOALIE_START_SOURCE_DAILY_FACEOFF,
        )
        self.assertEqual(
            row.goalie_start_provider_goalie_id,
            2413,
        )
        self.assertEqual(
            row.goalie_start_evidence_source_name,
            "Source",
        )

    def test_likely_goalie_does_not_invent_probability(
        self,
    ):
        row = _build(
            goalie_mapping_marker={
                NHL_GOALIE_ID: _evidence(
                    start_state=(
                        GOALIE_START_LIKELY
                    )
                ),
            }
        )

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_GOALIE_START_LIKELY,
        )
        self.assertIsNone(
            row.expected_fantasy_points
        )
        self.assertEqual(
            row.goalie_start_state,
            GOALIE_START_LIKELY,
        )

    def test_unconfirmed_goalie_is_unknown_not_zero(
        self,
    ):
        row = _build(
            goalie_mapping_marker={
                NHL_GOALIE_ID: _evidence(
                    start_state=(
                        GOALIE_START_UNCONFIRMED
                    )
                ),
            }
        )

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_GOALIE_START_UNCONFIRMED,
        )
        self.assertIsNone(
            row.expected_fantasy_points
        )
        self.assertNotEqual(
            row.expected_fantasy_points,
            0.0,
        )

    def test_missing_resolved_evidence_is_unknown_not_zero(
        self,
    ):
        row = _build(
            goalie_mapping_marker={}
        )

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_GOALIE_START_UNKNOWN,
        )
        self.assertIsNone(
            row.expected_fantasy_points
        )

    def test_skater_value_is_unchanged_when_goalie_model_enabled(
        self,
    ):
        row = _build(
            strength=_strength(
                player_type="C",
                nhl_player_id=8478402,
            ),
            goalie_mapping_marker={},
        )

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_AVAILABLE,
        )
        self.assertEqual(
            row.expected_fantasy_points,
            4.75,
        )
        self.assertIsNone(
            row.goalie_start_state
        )

    def test_off_day_still_zero_without_goalie_evidence(
        self,
    ):
        row = _build(
            context=_context(
                schedule_state="off",
            ),
            goalie_mapping_marker={},
        )

        self.assertEqual(
            row.value_state,
            DAILY_VALUE_OFF,
        )
        self.assertEqual(
            row.expected_fantasy_points,
            0.0,
        )

    def test_evidence_for_off_day_fails_closed(
        self,
    ):
        with self.assertRaisesRegex(
            DailyValueError,
            "without a scheduled game",
        ):
            _build(
                context=_context(
                    schedule_state="off",
                ),
                goalie_mapping_marker={
                    NHL_GOALIE_ID: _evidence(
                        start_state=(
                            GOALIE_START_CONFIRMED
                        )
                    ),
                },
            )

    def test_wrong_evidence_date_fails_closed(
        self,
    ):
        with self.assertRaisesRegex(
            DailyValueError,
            "did not match requested date",
        ):
            _build(
                goalie_mapping_marker={
                    NHL_GOALIE_ID: _evidence(
                        start_state=(
                            GOALIE_START_CONFIRMED
                        ),
                        game_date=date(
                            2026,
                            3,
                            15,
                        ),
                    ),
                }
            )

    def test_unknown_start_state_fails_closed(
        self,
    ):
        with self.assertRaisesRegex(
            DailyValueError,
            "unsupported state",
        ):
            _build(
                goalie_mapping_marker={
                    NHL_GOALIE_ID: _evidence(
                        start_state="probable",
                    ),
                }
            )


if __name__ == "__main__":
    unittest.main()
