from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from hockey_rmt.domain.daily_value import (
    DAILY_VALUE_AVAILABLE,
    DAILY_VALUE_OFF,
    DAILY_VALUE_SCHEDULE_UNKNOWN,
    DAILY_VALUE_SOURCE_SEASON_STRENGTH,
    DAILY_VALUE_STRENGTH_UNAVAILABLE,
    DailyExpectedValue,
)
from hockey_rmt.domain.game_context import (
    PlayerGameContext,
)
from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    PlayerStrengthProjection,
)


class DailyValueError(RuntimeError):
    """Baseline daily expected-value construction failed."""


VALID_SCHEDULE_STATES = {
    "scheduled",
    "off",
    "unknown_team",
}


def build_baseline_daily_expected_values(
    *,
    player_strengths: Sequence[
        PlayerStrengthProjection
    ],
    game_contexts: Sequence[
        PlayerGameContext
    ],
    season_id: int,
    game_date: date,
) -> tuple[
    DailyExpectedValue,
    ...,
]:
    requested_season = int(
        season_id
    )

    strength_by_key = {}
    strength_order = []

    for strength in player_strengths:
        key = str(
            strength.provider_player_key
        )

        if key in strength_by_key:
            raise DailyValueError(
                "Player-strength input contained "
                "duplicate provider player key "
                f"{key!r}."
            )

        if (
            int(
                strength.projection_season_id
            )
            != requested_season
        ):
            raise DailyValueError(
                "Player-strength season mismatch "
                f"for {key!r}: "
                f"{strength.projection_season_id} "
                f"!= {requested_season}."
            )

        strength_by_key[
            key
        ] = strength

        strength_order.append(
            key
        )

    context_by_key = {}

    for context in game_contexts:
        key = str(
            context.provider_player_key
        )

        if key in context_by_key:
            raise DailyValueError(
                "Game-context input contained "
                "duplicate provider player key "
                f"{key!r}."
            )

        if (
            context.game_date
            != game_date
        ):
            raise DailyValueError(
                "Game-context date mismatch for "
                f"{key!r}: "
                f"{context.game_date.isoformat()} "
                f"!= {game_date.isoformat()}."
            )

        if (
            context.schedule_state
            not in VALID_SCHEDULE_STATES
        ):
            raise DailyValueError(
                "Unsupported schedule state "
                f"{context.schedule_state!r} "
                f"for {key!r}."
            )

        context_by_key[
            key
        ] = context

    strength_keys = set(
        strength_by_key
    )

    context_keys = set(
        context_by_key
    )

    if strength_keys != context_keys:
        raise DailyValueError(
            "Player-strength and game-context "
            "provider-key sets did not match: "
            f"strength_only="
            f"{len(strength_keys - context_keys)}, "
            f"context_only="
            f"{len(context_keys - strength_keys)}."
        )

    result = []

    for key in strength_order:
        strength = strength_by_key[
            key
        ]

        context = context_by_key[
            key
        ]

        schedule_state = (
            context.schedule_state
        )

        raw_baseline_fppg = (
            strength
            .projected_fantasy_points_per_game
        )

        strength_available = (
            strength.strength_state
            == STRENGTH_AVAILABLE
            and raw_baseline_fppg
            is not None
        )

        baseline_fppg = (
            float(
                raw_baseline_fppg
            )
            if strength_available
            else None
        )

        if (
            baseline_fppg is not None
            and baseline_fppg < 0
        ):
            raise DailyValueError(
                "Available player strength "
                "contained negative FPPG for "
                f"{key!r}: "
                f"{baseline_fppg}."
            )

        if (
            schedule_state
            == "unknown_team"
        ):
            value_state = (
                DAILY_VALUE_SCHEDULE_UNKNOWN
            )

            baseline_source = (
                DAILY_VALUE_SOURCE_SEASON_STRENGTH
                if strength_available
                else None
            )

            expected_points = None

        elif schedule_state == "off":
            value_state = (
                DAILY_VALUE_OFF
            )

            baseline_source = (
                DAILY_VALUE_SOURCE_SEASON_STRENGTH
                if strength_available
                else None
            )

            expected_points = 0.0

        elif not strength_available:
            value_state = (
                DAILY_VALUE_STRENGTH_UNAVAILABLE
            )

            baseline_source = None
            expected_points = None

        else:
            value_state = (
                DAILY_VALUE_AVAILABLE
            )

            baseline_source = (
                DAILY_VALUE_SOURCE_SEASON_STRENGTH
            )

            expected_points = (
                baseline_fppg
            )

        result.append(
            DailyExpectedValue(
                provider_player_key=(
                    key
                ),
                full_name=(
                    strength.full_name
                ),
                season_id=(
                    requested_season
                ),
                game_date=(
                    game_date
                ),
                player_type=(
                    strength.player_type
                ),
                nhl_player_id=(
                    strength.nhl_player_id
                ),
                nhl_team_abbr=(
                    context.nhl_team_abbr
                ),
                schedule_state=(
                    schedule_state
                ),
                value_state=(
                    value_state
                ),
                baseline_source=(
                    baseline_source
                ),
                baseline_fantasy_points_per_game=(
                    baseline_fppg
                ),
                expected_fantasy_points=(
                    expected_points
                ),
                provider_game_id=(
                    context.provider_game_id
                ),
                opponent_team_abbr=(
                    context.opponent_team_abbr
                ),
                home_away=(
                    context.home_away
                ),
            )
        )

    if (
        len(result)
        != len(
            player_strengths
        )
    ):
        raise DailyValueError(
            "Daily-value result count did not "
            "match player-strength count."
        )

    result_keys = [
        row.provider_player_key
        for row in result
    ]

    if result_keys != strength_order:
        raise DailyValueError(
            "Daily-value output order did not "
            "preserve player-strength input order."
        )

    return tuple(
        result
    )
