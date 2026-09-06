from __future__ import annotations

import math
from collections.abc import Sequence

from hockey_rmt.domain.performance_trend import (
    RATE_AVAILABLE,
    RATE_NO_SAMPLE,
    SkaterPerformanceRate,
    SkaterPerformanceTrend,
)


class PerformanceRateError(RuntimeError):
    """Skater performance rates could not be normalized."""


def _per_60(
    value: float,
    *,
    ice_time_seconds: float,
) -> float:
    result = (
        float(value)
        * 3600.0
        / float(ice_time_seconds)
    )

    if not math.isfinite(
        result
    ):
        raise PerformanceRateError(
            "Normalized per-60 value "
            "was not finite."
        )

    return result


def normalize_skater_performance_trend(
    trend: SkaterPerformanceTrend,
) -> SkaterPerformanceRate:
    games_played = int(
        trend.games_played
    )

    ice_time_seconds = float(
        trend.ice_time_seconds
    )

    if games_played < 0:
        raise PerformanceRateError(
            "games_played cannot be negative."
        )

    if not math.isfinite(
        ice_time_seconds
    ):
        raise PerformanceRateError(
            "ice_time_seconds must be finite."
        )

    if ice_time_seconds < 0:
        raise PerformanceRateError(
            "ice_time_seconds cannot be negative."
        )

    if (
        games_played == 0
        or ice_time_seconds == 0
    ):
        return SkaterPerformanceRate(
            source=trend.source,
            season_id=trend.season_id,
            window=trend.window,
            nhl_player_id=(
                trend.nhl_player_id
            ),
            full_name=trend.full_name,
            nhl_team_abbr=(
                trend.nhl_team_abbr
            ),
            position=trend.position,
            situation=trend.situation,
            games_played=games_played,
            ice_time_seconds=(
                ice_time_seconds
            ),
            rate_state=RATE_NO_SAMPLE,
            toi_per_game_minutes=None,
            expected_goals_per_60=None,
            shots_on_goal_per_60=None,
            shot_attempts_per_60=None,
            high_danger_shots_per_60=None,
            goals_per_60=None,
            goals_minus_expected_per_60=None,
            primary_assists_per_60=None,
            secondary_assists_per_60=None,
            shots_blocked_per_60=None,
            penalties_per_60=None,
            on_ice_expected_goals_percentage=(
                float(
                    trend
                    .on_ice_expected_goals_percentage
                )
            ),
        )

    toi_per_game_minutes = (
        ice_time_seconds
        / float(
            games_played
        )
        / 60.0
    )

    expected_goals_per_60 = _per_60(
        trend.individual_expected_goals,
        ice_time_seconds=ice_time_seconds,
    )

    goals_per_60 = _per_60(
        trend.goals,
        ice_time_seconds=ice_time_seconds,
    )

    return SkaterPerformanceRate(
        source=trend.source,
        season_id=trend.season_id,
        window=trend.window,
        nhl_player_id=(
            trend.nhl_player_id
        ),
        full_name=trend.full_name,
        nhl_team_abbr=(
            trend.nhl_team_abbr
        ),
        position=trend.position,
        situation=trend.situation,
        games_played=games_played,
        ice_time_seconds=(
            ice_time_seconds
        ),
        rate_state=RATE_AVAILABLE,
        toi_per_game_minutes=(
            toi_per_game_minutes
        ),
        expected_goals_per_60=(
            expected_goals_per_60
        ),
        shots_on_goal_per_60=(
            _per_60(
                trend.shots_on_goal,
                ice_time_seconds=(
                    ice_time_seconds
                ),
            )
        ),
        shot_attempts_per_60=(
            _per_60(
                trend.shot_attempts,
                ice_time_seconds=(
                    ice_time_seconds
                ),
            )
        ),
        high_danger_shots_per_60=(
            _per_60(
                trend.high_danger_shots,
                ice_time_seconds=(
                    ice_time_seconds
                ),
            )
        ),
        goals_per_60=(
            goals_per_60
        ),
        goals_minus_expected_per_60=(
            goals_per_60
            - expected_goals_per_60
        ),
        primary_assists_per_60=(
            _per_60(
                trend.primary_assists,
                ice_time_seconds=(
                    ice_time_seconds
                ),
            )
        ),
        secondary_assists_per_60=(
            _per_60(
                trend.secondary_assists,
                ice_time_seconds=(
                    ice_time_seconds
                ),
            )
        ),
        shots_blocked_per_60=(
            _per_60(
                trend.shots_blocked,
                ice_time_seconds=(
                    ice_time_seconds
                ),
            )
        ),
        penalties_per_60=(
            _per_60(
                trend.penalties,
                ice_time_seconds=(
                    ice_time_seconds
                ),
            )
        ),
        on_ice_expected_goals_percentage=(
            float(
                trend
                .on_ice_expected_goals_percentage
            )
        ),
    )


def build_skater_performance_rates(
    trends: Sequence[
        SkaterPerformanceTrend
    ],
) -> tuple[
    SkaterPerformanceRate,
    ...,
]:
    result: list[
        SkaterPerformanceRate
    ] = []

    seen: set[
        tuple[
            str,
            int,
            str,
            int,
            str,
            str,
        ]
    ] = set()

    for trend in trends:
        key = (
            trend.source,
            trend.season_id,
            trend.window,
            trend.nhl_player_id,
            trend.nhl_team_abbr,
            trend.situation,
        )

        if key in seen:
            raise PerformanceRateError(
                "Duplicate performance trend "
                "observation: "
                f"{key!r}."
            )

        seen.add(
            key
        )

        result.append(
            normalize_skater_performance_trend(
                trend
            )
        )

    return tuple(
        result
    )
