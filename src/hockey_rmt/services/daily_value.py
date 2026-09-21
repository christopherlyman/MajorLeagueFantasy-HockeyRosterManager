from __future__ import annotations

from hockey_rmt.domain.projection_adjustment import (
    PlayerProjectionAdjustment,
)

from hockey_rmt.domain.daily_value import (
    DAILY_VALUE_PLAYER_UNAVAILABLE,
)
from hockey_rmt.domain.player_availability import (
    PLAYER_AVAILABILITY_UNAVAILABLE,
    VALID_PLAYER_AVAILABILITY_STATES,
)

import math

from collections.abc import Mapping, Sequence
from datetime import date

from hockey_rmt.domain.daily_value import (
    DAILY_VALUE_AVAILABLE,
    DAILY_VALUE_GOALIE_START_LIKELY,
    DAILY_VALUE_GOALIE_START_UNCONFIRMED,
    DAILY_VALUE_GOALIE_START_UNKNOWN,
    DAILY_VALUE_OFF,
    DAILY_VALUE_SCHEDULE_UNKNOWN,
    DAILY_VALUE_SOURCE_SEASON_STRENGTH,
    DAILY_VALUE_STRENGTH_UNAVAILABLE,
    DailyExpectedValue,
)
from hockey_rmt.domain.game_context import (
    PlayerGameContext,
)
from hockey_rmt.domain.goalie_start import (
    GOALIE_START_CONFIRMED,
    GOALIE_START_LIKELY,
    GOALIE_START_STATES,
    GOALIE_START_UNCONFIRMED,
    DailyGoalieStartEvidence,
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
    projection_adjustments: Sequence[
        PlayerProjectionAdjustment
    ] = (),
    goalie_starts_by_nhl_id: Mapping[
        int,
        DailyGoalieStartEvidence,
    ] | None = None,
) -> tuple[
    DailyExpectedValue,
    ...,
]:
    requested_season = int(
        season_id
    )

    goalie_start_rows = None

    if goalie_starts_by_nhl_id is not None:
        goalie_start_rows = {}

        for (
            raw_nhl_player_id,
            evidence,
        ) in goalie_starts_by_nhl_id.items():
            if isinstance(
                raw_nhl_player_id,
                bool,
            ):
                raise DailyValueError(
                    "Goalie-start NHL playerId "
                    "must be an integer."
                )

            try:
                nhl_player_id = int(
                    raw_nhl_player_id
                )
            except (
                TypeError,
                ValueError,
            ) as exc:
                raise DailyValueError(
                    "Goalie-start NHL playerId "
                    "must be an integer."
                ) from exc

            if nhl_player_id <= 0:
                raise DailyValueError(
                    "Goalie-start NHL playerId "
                    "must be positive."
                )

            if (
                nhl_player_id
                in goalie_start_rows
            ):
                raise DailyValueError(
                    "Goalie-start input contained "
                    "duplicate NHL playerId "
                    f"{nhl_player_id}."
                )

            if not isinstance(
                evidence,
                DailyGoalieStartEvidence,
            ):
                raise DailyValueError(
                    "Goalie-start input contained "
                    "an invalid evidence object for "
                    f"NHL playerId {nhl_player_id}."
                )

            if evidence.game_date != game_date:
                raise DailyValueError(
                    "Goalie-start evidence date "
                    f"{evidence.game_date.isoformat()} "
                    "did not match requested date "
                    f"{game_date.isoformat()}."
                )

            if (
                evidence.start_state
                not in GOALIE_START_STATES
            ):
                raise DailyValueError(
                    "Goalie-start evidence contained "
                    "unsupported state "
                    f"{evidence.start_state!r}."
                )

            goalie_start_rows[
                nhl_player_id
            ] = evidence

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

    adjustment_rows = tuple(
        projection_adjustments
    )

    adjustment_by_key = {}

    if adjustment_rows:
        for adjustment in adjustment_rows:
            key = str(
                adjustment.provider_player_key
            )

            if key in adjustment_by_key:
                raise DailyValueError(
                    "Projection-adjustment input "
                    "contained duplicate provider "
                    f"player key {key!r}."
                )

            if (
                int(
                    adjustment.projection_season_id
                )
                != requested_season
            ):
                raise DailyValueError(
                    "Projection-adjustment season "
                    f"mismatch for {key!r}: "
                    f"{adjustment.projection_season_id} "
                    f"!= {requested_season}."
                )

            adjustment_by_key[
                key
            ] = adjustment

        adjustment_keys = set(
            adjustment_by_key
        )

        strength_keys_for_adjustments = set(
            strength_by_key
        )

        if (
            adjustment_keys
            != strength_keys_for_adjustments
        ):
            raise DailyValueError(
                "Projection-adjustment and "
                "player-strength provider-key "
                "sets did not match: "
                "strength_only="
                f"{len(strength_keys_for_adjustments - adjustment_keys)}, "
                "adjustment_only="
                f"{len(adjustment_keys - strength_keys_for_adjustments)}."
            )

        for key, strength in (
            strength_by_key.items()
        ):
            adjustment = (
                adjustment_by_key[
                    key
                ]
            )

            if (
                adjustment.player_type
                != strength.player_type
            ):
                raise DailyValueError(
                    "Projection-adjustment player "
                    f"type mismatch for {key!r}: "
                    f"{adjustment.player_type!r} "
                    f"!= {strength.player_type!r}."
                )

            if (
                adjustment.nhl_player_id
                != strength.nhl_player_id
            ):
                raise DailyValueError(
                    "Projection-adjustment NHL "
                    f"identity mismatch for {key!r}."
                )

            strength_baseline = (
                strength
                .projected_fantasy_points_per_game
            )

            adjustment_baseline = (
                adjustment
                .baseline_fantasy_points_per_game
            )

            if (
                strength_baseline is None
                and adjustment_baseline
                is not None
            ):
                raise DailyValueError(
                    "Projection-adjustment baseline "
                    f"mismatch for {key!r}."
                )

            if (
                strength_baseline is not None
                and adjustment_baseline
                is None
            ):
                raise DailyValueError(
                    "Projection-adjustment baseline "
                    f"mismatch for {key!r}."
                )

            if (
                strength_baseline is not None
                and adjustment_baseline
                is not None
                and float(
                    strength_baseline
                )
                != float(
                    adjustment_baseline
                )
            ):
                raise DailyValueError(
                    "Projection-adjustment baseline "
                    f"value mismatch for {key!r}: "
                    f"{adjustment_baseline} "
                    f"!= {strength_baseline}."
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


        if (
            context.availability_state
            not in VALID_PLAYER_AVAILABILITY_STATES
        ):
            raise DailyValueError(
                "Unsupported player availability "
                f"state {context.availability_state!r} "
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
            and not math.isfinite(
                baseline_fppg
            )
        ):
            raise DailyValueError(
                "Available player strength "
                "contained non-finite FPPG for "
                f"{key!r}: "
                f"{baseline_fppg}."
            )

        adjustment = (
            adjustment_by_key.get(
                key
            )
            if adjustment_rows
            else None
        )

        adjustment_state = (
            adjustment.adjustment_state
            if adjustment is not None
            else None
        )

        adjusted_fppg = (
            adjustment
            .adjusted_fantasy_points_per_game
            if adjustment is not None
            else baseline_fppg
        )

        adjustment_factor = (
            float(
                adjustment.combined_factor
            )
            if adjustment is not None
            else 1.0
        )

        if (
            strength_available
            and adjustment is not None
            and adjusted_fppg is None
        ):
            raise DailyValueError(
                "Available player adjustment "
                "was missing adjusted FPPG for "
                f"{key!r}."
            )

        if (
            adjusted_fppg is not None
            and not math.isfinite(
                float(
                    adjusted_fppg
                )
            )
        ):
            raise DailyValueError(
                "Projection adjustment contained "
                "non-finite adjusted FPPG for "
                f"{key!r}."
            )

        if not math.isfinite(
            adjustment_factor
        ):
            raise DailyValueError(
                "Projection adjustment contained "
                "non-finite combined factor for "
                f"{key!r}."
            )

        goalie_start = None
        goalie_start_state = None
        goalie_start_source = None
        goalie_start_provider_goalie_id = None
        goalie_start_evidence_created_at_utc = None
        goalie_start_evidence_source_name = None
        goalie_start_evidence_source_url = None

        goalie_start_model_enabled = (
            goalie_start_rows is not None
            and str(
                strength.player_type
            ).strip().upper()
            == "G"
        )

        if (
            goalie_start_model_enabled
            and strength.nhl_player_id
            is not None
        ):
            goalie_start = (
                goalie_start_rows.get(
                    int(
                        strength.nhl_player_id
                    )
                )
            )

        if goalie_start is not None:
            if schedule_state != "scheduled":
                raise DailyValueError(
                    "Goalie-start evidence was "
                    "supplied for a player without "
                    "a scheduled game: "
                    f"{key!r}, "
                    f"schedule_state="
                    f"{schedule_state!r}."
                )

            goalie_start_state = (
                goalie_start.start_state
            )
            goalie_start_source = (
                goalie_start.source
            )
            goalie_start_provider_goalie_id = (
                goalie_start.provider_goalie_id
            )
            goalie_start_evidence_created_at_utc = (
                goalie_start
                .evidence_created_at_utc
            )
            goalie_start_evidence_source_name = (
                goalie_start
                .evidence_source_name
            )
            goalie_start_evidence_source_url = (
                goalie_start
                .evidence_source_url
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

        elif (
            context.availability_state
            == PLAYER_AVAILABILITY_UNAVAILABLE
        ):
            value_state = (
                DAILY_VALUE_PLAYER_UNAVAILABLE
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

        elif (
            goalie_start_model_enabled
            and goalie_start is None
        ):
            value_state = (
                DAILY_VALUE_GOALIE_START_UNKNOWN
            )

            baseline_source = (
                DAILY_VALUE_SOURCE_SEASON_STRENGTH
            )

            expected_points = None

        elif (
            goalie_start_model_enabled
            and goalie_start_state
            == GOALIE_START_LIKELY
        ):
            value_state = (
                DAILY_VALUE_GOALIE_START_LIKELY
            )

            baseline_source = (
                DAILY_VALUE_SOURCE_SEASON_STRENGTH
            )

            expected_points = None

        elif (
            goalie_start_model_enabled
            and goalie_start_state
            == GOALIE_START_UNCONFIRMED
        ):
            value_state = (
                DAILY_VALUE_GOALIE_START_UNCONFIRMED
            )

            baseline_source = (
                DAILY_VALUE_SOURCE_SEASON_STRENGTH
            )

            expected_points = None

        elif (
            goalie_start_model_enabled
            and goalie_start_state
            != GOALIE_START_CONFIRMED
        ):
            raise DailyValueError(
                "Goalie-start valuation received "
                "an unsupported state "
                f"{goalie_start_state!r} "
                f"for {key!r}."
            )

        else:
            value_state = (
                DAILY_VALUE_AVAILABLE
            )

            baseline_source = (
                DAILY_VALUE_SOURCE_SEASON_STRENGTH
            )

            expected_points = (
                float(
                    adjusted_fppg
                )
                if adjusted_fppg
                is not None
                else baseline_fppg
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
                adjustment_state=(
                    adjustment_state
                ),
                adjusted_fantasy_points_per_game=(
                    (
                        float(
                            adjusted_fppg
                        )
                        if adjusted_fppg
                        is not None
                        else None
                    )
                ),
                adjustment_factor=(
                    adjustment_factor
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
                start_time_utc=context.start_time_utc,
                availability_state=(
                    context.availability_state
                ),
                provider_status=(
                    context.provider_status
                ),
                provider_status_full=(
                    context.provider_status_full
                ),
                goalie_start_state=(
                    goalie_start_state
                ),
                goalie_start_source=(
                    goalie_start_source
                ),
                goalie_start_provider_goalie_id=(
                    goalie_start_provider_goalie_id
                ),
                goalie_start_evidence_created_at_utc=(
                    goalie_start_evidence_created_at_utc
                ),
                goalie_start_evidence_source_name=(
                    goalie_start_evidence_source_name
                ),
                goalie_start_evidence_source_url=(
                    goalie_start_evidence_source_url
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
