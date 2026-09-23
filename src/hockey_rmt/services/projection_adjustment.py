from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from hockey_rmt.domain.current_production import (
    CURRENT_PRODUCTION_AVAILABLE,
    CurrentSeasonProduction,
)
from hockey_rmt.domain.deployment import (
    CATEGORY_EVEN_STRENGTH,
    CATEGORY_POWER_PLAY,
    DEPLOYMENT_SOURCE_DAILY_FACEOFF,
    SourcePlayerDeployment,
)
from hockey_rmt.domain.player_strength import (
    STRENGTH_AVAILABLE,
    PlayerStrengthProjection,
)
from hockey_rmt.domain.projection_adjustment import (
    ADJUSTMENT_APPLIED,
    ADJUSTMENT_BASELINE_ONLY,
    ADJUSTMENT_NOT_APPLICABLE,
    ADJUSTMENT_STRENGTH_UNAVAILABLE,
    PlayerProjectionAdjustment,
)
from hockey_rmt.domain.trend_signal import (
    FINISHING_COLD,
    FINISHING_HOT,
    ROLE_EXPANDING,
    ROLE_SHRINKING,
    TREND_DECLINING,
    TREND_IMPROVING,
    SkaterTrendInterpretation,
)


class ProjectionAdjustmentError(
    RuntimeError
):
    """Current-state projection inputs were invalid."""


_DFO_EV_EFFECT = {
    "f1": 0.015,
    "f2": 0.005,
    "f3": -0.005,
    "f4": -0.015,
    "d1": 0.010,
    "d2": 0.000,
    "d3": -0.010,
}

_DFO_PP_EFFECT = {
    "pp1": 0.025,
    "pp2": 0.005,
}

_DFO_NO_PP_EFFECT = -0.010

_DFO_MIN_EFFECT = -0.030
_DFO_MAX_EFFECT = 0.040

_ROLE_EFFECT = 0.030
_PROCESS_EFFECT = 0.015

_PRODUCTION_MAX_WEIGHT = 0.30
_PRODUCTION_FULL_WEIGHT_GAMES = 60

_PRODUCTION_RATIO_MIN = 0.75
_PRODUCTION_RATIO_MAX = 1.25

_FINISHING_VARIANCE_WEIGHT_MULTIPLIER = 0.50

_COMBINED_FACTOR_MIN = 0.88
_COMBINED_FACTOR_MAX = 1.12


def _finite(
    value: float,
    *,
    label: str,
) -> float:
    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        raise ProjectionAdjustmentError(
            f"{label} must be finite."
        )

    return result


def _clip(
    value: float,
    *,
    lower: float,
    upper: float,
) -> float:
    return min(
        upper,
        max(
            lower,
            value,
        ),
    )


def _index_current_production(
    rows: Sequence[
        CurrentSeasonProduction
    ],
    *,
    projection_season_id: int,
) -> dict[
    str,
    CurrentSeasonProduction,
]:
    result = {}

    for row in rows:
        key = str(
            row.provider_player_key
        )

        if key in result:
            raise ProjectionAdjustmentError(
                "Current-production input contained "
                "duplicate provider player key "
                f"{key!r}."
            )

        if (
            int(
                row.season_id
            )
            != projection_season_id
        ):
            raise ProjectionAdjustmentError(
                "Current-production input contained "
                "a different season_id."
            )

        result[
            key
        ] = row

    return result


def _index_trends(
    rows: Sequence[
        SkaterTrendInterpretation
    ],
    *,
    projection_season_id: int,
) -> dict[
    int,
    SkaterTrendInterpretation,
]:
    result = {}

    for row in rows:
        if (
            int(
                row.season_id
            )
            != projection_season_id
        ):
            raise ProjectionAdjustmentError(
                "Trend input contained a different "
                "season_id."
            )

        player_id = int(
            row.nhl_player_id
        )

        if player_id in result:
            raise ProjectionAdjustmentError(
                "Trend input contained duplicate "
                f"NHL playerId {player_id}."
            )

        result[
            player_id
        ] = row

    return result


def _validate_deployments(
    rows: Mapping[
        int,
        SourcePlayerDeployment,
    ],
) -> dict[
    int,
    SourcePlayerDeployment,
]:
    result = {}

    for raw_player_id, row in rows.items():
        player_id = int(
            raw_player_id
        )

        if player_id in result:
            raise ProjectionAdjustmentError(
                "Deployment mapping contained "
                "duplicate NHL playerId "
                f"{player_id}."
            )

        if (
            row.source
            != DEPLOYMENT_SOURCE_DAILY_FACEOFF
        ):
            raise ProjectionAdjustmentError(
                "Unsupported deployment source "
                f"{row.source!r}."
            )

        result[
            player_id
        ] = row

    return result


def _deployment_factor(
    deployment: SourcePlayerDeployment | None,
) -> tuple[
    float,
    str | None,
    str | None,
    tuple[
        str,
        ...,
    ],
]:
    if deployment is None:
        return (
            1.0,
            None,
            None,
            (),
        )

    ev_groups = {
        str(
            assignment.group_identifier
        ).strip().lower()
        for assignment in deployment.assignments
        if (
            str(
                assignment.category_identifier
            )
            .strip()
            .lower()
            == CATEGORY_EVEN_STRENGTH
        )
    }

    pp_groups = {
        str(
            assignment.group_identifier
        ).strip().lower()
        for assignment in deployment.assignments
        if (
            str(
                assignment.category_identifier
            )
            .strip()
            .lower()
            == CATEGORY_POWER_PLAY
        )
    }

    if len(ev_groups) > 1:
        raise ProjectionAdjustmentError(
            "Daily Faceoff deployment contained "
            "multiple even-strength groups for "
            f"{deployment.full_name!r}: "
            f"{sorted(ev_groups)!r}."
        )

    pp_ambiguity_reason = None

    if len(pp_groups) > 1:
        if pp_groups == {
            "pp1",
            "pp2",
        }:
            pp_group = None
            pp_ambiguity_reason = (
                "dfo_pp_ambiguous:"
                "pp1,pp2:neutral"
            )
        else:
            raise ProjectionAdjustmentError(
                "Daily Faceoff deployment contained "
                "multiple power-play groups for "
                f"{deployment.full_name!r}: "
                f"{sorted(pp_groups)!r}."
            )
    else:
        pp_group = (
            next(
                iter(
                    pp_groups
                )
            )
            if pp_groups
            else None
        )

    ev_group = (
        next(
            iter(
                ev_groups
            )
        )
        if ev_groups
        else None
    )

    effect = 0.0
    reasons = []

    if pp_ambiguity_reason is not None:
        reasons.append(
            pp_ambiguity_reason
        )

    if ev_group is not None:
        ev_effect = (
            _DFO_EV_EFFECT.get(
                ev_group
            )
        )

        if ev_effect is None:
            reasons.append(
                f"dfo_ev_unknown:{ev_group}"
            )
        else:
            effect += ev_effect

            reasons.append(
                f"dfo_ev:{ev_group}:"
                f"{ev_effect:+.3f}"
            )

    if pp_group is not None:
        pp_effect = (
            _DFO_PP_EFFECT.get(
                pp_group
            )
        )

        if pp_effect is None:
            reasons.append(
                f"dfo_pp_unknown:{pp_group}"
            )
        else:
            effect += pp_effect

            reasons.append(
                f"dfo_pp:{pp_group}:"
                f"{pp_effect:+.3f}"
            )

    elif (
        pp_ambiguity_reason is None
        and ev_group is not None
    ):
        effect += (
            _DFO_NO_PP_EFFECT
        )

        reasons.append(
            "dfo_pp:none:"
            f"{_DFO_NO_PP_EFFECT:+.3f}"
        )

    bounded_effect = _clip(
        effect,
        lower=(
            _DFO_MIN_EFFECT
        ),
        upper=(
            _DFO_MAX_EFFECT
        ),
    )

    if (
        not math.isclose(
            bounded_effect,
            effect,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ):
        reasons.append(
            "dfo_effect_capped:"
            f"{effect:+.3f}"
            "->"
            f"{bounded_effect:+.3f}"
        )

    return (
        1.0
        + bounded_effect,
        ev_group,
        pp_group,
        tuple(
            reasons
        ),
    )


def _trend_role_factor(
    trend: SkaterTrendInterpretation | None,
) -> tuple[
    float,
    tuple[
        str,
        ...,
    ],
]:
    if trend is None:
        return (
            1.0,
            (),
        )

    if (
        trend.role_state
        == ROLE_EXPANDING
    ):
        return (
            1.0
            + _ROLE_EFFECT,
            (
                "trend_role:expanding:"
                f"{_ROLE_EFFECT:+.3f}",
            ),
        )

    if (
        trend.role_state
        == ROLE_SHRINKING
    ):
        return (
            1.0
            - _ROLE_EFFECT,
            (
                "trend_role:shrinking:"
                f"{-_ROLE_EFFECT:+.3f}",
            ),
        )

    return (
        1.0,
        (
            f"trend_role:{trend.role_state}:"
            "+0.000",
        ),
    )


def _process_factor(
    trend: SkaterTrendInterpretation | None,
) -> tuple[
    float,
    tuple[
        str,
        ...,
    ],
]:
    if trend is None:
        return (
            1.0,
            (),
        )

    if (
        trend.process_state
        == TREND_IMPROVING
    ):
        return (
            1.0
            + _PROCESS_EFFECT,
            (
                "trend_process:improving:"
                f"{_PROCESS_EFFECT:+.3f}",
            ),
        )

    if (
        trend.process_state
        == TREND_DECLINING
    ):
        return (
            1.0
            - _PROCESS_EFFECT,
            (
                "trend_process:declining:"
                f"{-_PROCESS_EFFECT:+.3f}",
            ),
        )

    return (
        1.0,
        (
            f"trend_process:"
            f"{trend.process_state}:"
            "+0.000",
        ),
    )


def _production_factor(
    *,
    baseline_fppg: float,
    production: CurrentSeasonProduction | None,
    trend: SkaterTrendInterpretation | None,
) -> tuple[
    float,
    int | None,
    float | None,
    tuple[
        str,
        ...,
    ],
]:
    if (
        production is None
        or production.production_state
        != CURRENT_PRODUCTION_AVAILABLE
        or production.games_played <= 0
        or production.fantasy_points_per_game
        is None
    ):
        return (
            1.0,
            (
                None
                if production is None
                else int(
                    production.games_played
                )
            ),
            (
                None
                if production is None
                else production
                .fantasy_points_per_game
            ),
            (),
        )

    games_played = int(
        production.games_played
    )

    current_fppg = _finite(
        production
        .fantasy_points_per_game,
        label=(
            "current-production FPPG"
        ),
    )

    if baseline_fppg <= 0.0:
        return (
            1.0,
            games_played,
            current_fppg,
            (
                "production_skipped:"
                "nonpositive_baseline",
            ),
        )

    raw_ratio = (
        current_fppg
        / baseline_fppg
    )

    bounded_ratio = _clip(
        raw_ratio,
        lower=(
            _PRODUCTION_RATIO_MIN
        ),
        upper=(
            _PRODUCTION_RATIO_MAX
        ),
    )

    weight = min(
        _PRODUCTION_MAX_WEIGHT,
        (
            float(
                games_played
            )
            / float(
                _PRODUCTION_FULL_WEIGHT_GAMES
            )
            * _PRODUCTION_MAX_WEIGHT
        ),
    )

    reasons = [
        "production_weight:"
        f"{weight:.4f}",
        "production_ratio:"
        f"{raw_ratio:.4f}"
        "->"
        f"{bounded_ratio:.4f}",
    ]

    finishing_state = (
        trend.finishing_state
        if trend is not None
        else None
    )

    finishing_brake = (
        (
            finishing_state
            == FINISHING_HOT
            and bounded_ratio > 1.0
        )
        or (
            finishing_state
            == FINISHING_COLD
            and bounded_ratio < 1.0
        )
    )

    if finishing_brake:
        original_weight = weight

        weight *= (
            _FINISHING_VARIANCE_WEIGHT_MULTIPLIER
        )

        reasons.append(
            "finishing_variance_brake:"
            f"{original_weight:.4f}"
            "->"
            f"{weight:.4f}"
        )

    factor = (
        1.0
        + weight
        * (
            bounded_ratio
            - 1.0
        )
    )

    reasons.append(
        f"production_factor:{factor:.4f}"
    )

    return (
        factor,
        games_played,
        current_fppg,
        tuple(
            reasons
        ),
    )


def build_player_projection_adjustments(
    *,
    player_strengths: Sequence[
        PlayerStrengthProjection
    ],
    projection_season_id: int,
    current_production: Sequence[
        CurrentSeasonProduction
    ] = (),
    trend_interpretations: Sequence[
        SkaterTrendInterpretation
    ] = (),
    deployments_by_nhl_id: Mapping[
        int,
        SourcePlayerDeployment,
    ] | None = None,
) -> tuple[
    PlayerProjectionAdjustment,
    ...,
]:
    target_season = int(
        projection_season_id
    )

    if target_season <= 0:
        raise ProjectionAdjustmentError(
            "projection_season_id must "
            "be positive."
        )

    strengths = tuple(
        player_strengths
    )

    provider_keys = tuple(
        str(
            row.provider_player_key
        )
        for row in strengths
    )

    if (
        len(
            provider_keys
        )
        != len(
            set(
                provider_keys
            )
        )
    ):
        raise ProjectionAdjustmentError(
            "Player-strength input contained "
            "duplicate provider player keys."
        )

    production_by_key = (
        _index_current_production(
            tuple(
                current_production
            ),
            projection_season_id=(
                target_season
            ),
        )
    )

    trend_by_nhl_id = (
        _index_trends(
            tuple(
                trend_interpretations
            ),
            projection_season_id=(
                target_season
            ),
        )
    )

    deployments = (
        _validate_deployments(
            deployments_by_nhl_id
            or {}
        )
    )

    result = []

    for strength in strengths:
        if (
            int(
                strength
                .projection_season_id
            )
            != target_season
        ):
            raise ProjectionAdjustmentError(
                "Player-strength input contained "
                "a different projection season."
            )

        provider_key = str(
            strength.provider_player_key
        )

        raw_baseline = (
            strength
            .projected_fantasy_points_per_game
        )

        baseline = (
            None
            if raw_baseline is None
            else _finite(
                raw_baseline,
                label=(
                    "canonical baseline FPPG"
                ),
            )
        )

        production = (
            production_by_key.get(
                provider_key
            )
        )

        if (
            production is not None
            and production.nhl_player_id
            != strength.nhl_player_id
        ):
            raise ProjectionAdjustmentError(
                "Current-production NHL identity "
                "did not match player strength for "
                f"{provider_key!r}."
            )

        if (
            strength.strength_state
            != STRENGTH_AVAILABLE
            or baseline is None
        ):
            result.append(
                PlayerProjectionAdjustment(
                    provider_player_key=(
                        provider_key
                    ),
                    full_name=(
                        strength.full_name
                    ),
                    projection_season_id=(
                        target_season
                    ),
                    player_type=(
                        strength.player_type
                    ),
                    nhl_player_id=(
                        strength.nhl_player_id
                    ),
                    adjustment_state=(
                        ADJUSTMENT_STRENGTH_UNAVAILABLE
                    ),
                    baseline_fantasy_points_per_game=(
                        baseline
                    ),
                    adjusted_fantasy_points_per_game=None,
                    deployment_factor=1.0,
                    trend_role_factor=1.0,
                    process_factor=1.0,
                    production_factor=1.0,
                    combined_factor=1.0,
                    deployment_even_strength_group=None,
                    deployment_power_play_group=None,
                    current_production_games=(
                        None
                    ),
                    current_production_fantasy_points_per_game=(
                        None
                    ),
                    role_state=None,
                    process_state=None,
                    finishing_state=None,
                    reasons=(
                        "canonical_strength_unavailable",
                    ),
                )
            )

            continue

        canonical_player_type = str(
            strength.player_type
        ).strip()

        if canonical_player_type in {
            "P",
            "skater",
        }:
            is_skater = True

        elif canonical_player_type in {
            "G",
            "goalie",
        }:
            is_skater = False

        else:
            raise ProjectionAdjustmentError(
                "Unsupported canonical player type "
                f"{canonical_player_type!r} for "
                f"{provider_key!r}."
            )

        if not is_skater:
            result.append(
                PlayerProjectionAdjustment(
                    provider_player_key=(
                        provider_key
                    ),
                    full_name=(
                        strength.full_name
                    ),
                    projection_season_id=(
                        target_season
                    ),
                    player_type=(
                        strength.player_type
                    ),
                    nhl_player_id=(
                        strength.nhl_player_id
                    ),
                    adjustment_state=(
                        ADJUSTMENT_NOT_APPLICABLE
                    ),
                    baseline_fantasy_points_per_game=(
                        baseline
                    ),
                    adjusted_fantasy_points_per_game=(
                        baseline
                    ),
                    deployment_factor=1.0,
                    trend_role_factor=1.0,
                    process_factor=1.0,
                    production_factor=1.0,
                    combined_factor=1.0,
                    deployment_even_strength_group=None,
                    deployment_power_play_group=None,
                    current_production_games=(
                        None
                    ),
                    current_production_fantasy_points_per_game=(
                        None
                    ),
                    role_state=None,
                    process_state=None,
                    finishing_state=None,
                    reasons=(
                        "skater_adjustment_not_applicable",
                    ),
                )
            )

            continue

        nhl_player_id = (
            int(
                strength.nhl_player_id
            )
            if strength.nhl_player_id
            is not None
            else None
        )

        trend = (
            trend_by_nhl_id.get(
                nhl_player_id
            )
            if nhl_player_id
            is not None
            else None
        )

        deployment = (
            deployments.get(
                nhl_player_id
            )
            if nhl_player_id
            is not None
            else None
        )

        (
            deployment_factor,
            ev_group,
            pp_group,
            deployment_reasons,
        ) = _deployment_factor(
            deployment
        )

        (
            role_factor,
            role_reasons,
        ) = _trend_role_factor(
            trend
        )

        (
            process_factor,
            process_reasons,
        ) = _process_factor(
            trend
        )

        (
            production_factor,
            production_games,
            production_fppg,
            production_reasons,
        ) = _production_factor(
            baseline_fppg=(
                baseline
            ),
            production=(
                production
            ),
            trend=(
                trend
            ),
        )

        raw_combined = (
            deployment_factor
            * role_factor
            * process_factor
            * production_factor
        )

        combined = _clip(
            raw_combined,
            lower=(
                _COMBINED_FACTOR_MIN
            ),
            upper=(
                _COMBINED_FACTOR_MAX
            ),
        )

        adjusted = (
            baseline
            * combined
        )

        reasons = (
            deployment_reasons
            + role_reasons
            + process_reasons
            + production_reasons
        )

        if (
            not math.isclose(
                raw_combined,
                combined,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            reasons += (
                "combined_factor_capped:"
                f"{raw_combined:.4f}"
                "->"
                f"{combined:.4f}",
            )

        state = (
            ADJUSTMENT_BASELINE_ONLY
            if math.isclose(
                combined,
                1.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            else ADJUSTMENT_APPLIED
        )

        result.append(
            PlayerProjectionAdjustment(
                provider_player_key=(
                    provider_key
                ),
                full_name=(
                    strength.full_name
                ),
                projection_season_id=(
                    target_season
                ),
                player_type=(
                    strength.player_type
                ),
                nhl_player_id=(
                    strength.nhl_player_id
                ),
                adjustment_state=state,
                baseline_fantasy_points_per_game=(
                    baseline
                ),
                adjusted_fantasy_points_per_game=(
                    adjusted
                ),
                deployment_factor=(
                    deployment_factor
                ),
                trend_role_factor=(
                    role_factor
                ),
                process_factor=(
                    process_factor
                ),
                production_factor=(
                    production_factor
                ),
                combined_factor=(
                    combined
                ),
                deployment_even_strength_group=(
                    ev_group
                ),
                deployment_power_play_group=(
                    pp_group
                ),
                current_production_games=(
                    production_games
                ),
                current_production_fantasy_points_per_game=(
                    production_fppg
                ),
                role_state=(
                    trend.role_state
                    if trend is not None
                    else None
                ),
                process_state=(
                    trend.process_state
                    if trend is not None
                    else None
                ),
                finishing_state=(
                    trend.finishing_state
                    if trend is not None
                    else None
                ),
                reasons=tuple(
                    reasons
                ),
            )
        )

    if (
        len(
            result
        )
        != len(
            strengths
        )
    ):
        raise ProjectionAdjustmentError(
            "Adjustment output count did not "
            "match player-strength input count."
        )

    result_keys = tuple(
        row.provider_player_key
        for row in result
    )

    if result_keys != provider_keys:
        raise ProjectionAdjustmentError(
            "Adjustment output did not preserve "
            "player-strength order."
        )

    return tuple(
        result
    )
