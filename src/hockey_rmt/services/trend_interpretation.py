from __future__ import annotations

import math
from collections.abc import Sequence

from hockey_rmt.domain.performance_trend import (
    SITUATION_5_ON_4,
    SITUATION_ALL,
    WINDOW_LAST_10,
    WINDOW_LAST_20,
    WINDOW_SEASON,
    SkaterPerformanceRate,
)
from hockey_rmt.domain.trend_signal import (
    FINISHING_COLD,
    FINISHING_HOT,
    FINISHING_INSUFFICIENT_SAMPLE,
    FINISHING_MIXED,
    FINISHING_NEUTRAL,
    ROLE_EXPANDING,
    ROLE_INSUFFICIENT_SAMPLE,
    ROLE_MIXED,
    ROLE_SHRINKING,
    ROLE_STABLE,
    SAMPLE_AVAILABLE,
    SAMPLE_INSUFFICIENT,
    TREND_DECLINING,
    TREND_IMPROVING,
    TREND_INSUFFICIENT_SAMPLE,
    TREND_MIXED,
    TREND_STABLE,
    MetricTrendEvidence,
    SkaterTrendInterpretation,
)


ROLE_MIN_SEASON_GAMES = 10
ROLE_MIN_LAST_20_GAMES = 10
ROLE_MIN_LAST_10_GAMES = 5

PROCESS_MIN_SEASON_GAMES = 20
PROCESS_MIN_LAST_20_GAMES = 10
PROCESS_MIN_LAST_10_GAMES = 5

TOI_CHANGE_MINUTES = 1.0
POWER_PLAY_TOI_CHANGE_MINUTES = 0.5

PROCESS_RELATIVE_CHANGE_THRESHOLD = 0.15

FINISHING_CHANGE_PER_60_THRESHOLD = 0.25


_PROCESS_METRICS = (
    (
        "expected_goals_per_60",
        0.25,
    ),
    (
        "shots_on_goal_per_60",
        1.00,
    ),
    (
        "shot_attempts_per_60",
        1.50,
    ),
    (
        "high_danger_shots_per_60",
        0.25,
    ),
    (
        "primary_assists_per_60",
        0.25,
    ),
)


class TrendInterpretationError(
    RuntimeError
):
    """Skater trend evidence could not be interpreted."""


def _finite(
    value: float | None,
    *,
    label: str,
) -> float:
    if value is None:
        raise TrendInterpretationError(
            f"{label} was unavailable."
        )

    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        raise TrendInterpretationError(
            f"{label} was not finite."
        )

    return result


def _absolute_evidence(
    *,
    metric_name: str,
    season_value: float,
    last_20_value: float,
    last_10_value: float,
    threshold: float,
) -> MetricTrendEvidence:
    last_20_change = (
        last_20_value
        - season_value
    )

    last_10_change = (
        last_10_value
        - season_value
    )

    if (
        last_20_change >= threshold
        and last_10_change >= threshold
    ):
        state = TREND_IMPROVING
    elif (
        last_20_change <= -threshold
        and last_10_change <= -threshold
    ):
        state = TREND_DECLINING
    elif (
        abs(last_20_change) < threshold
        and abs(last_10_change) < threshold
    ):
        state = TREND_STABLE
    else:
        state = TREND_MIXED

    return MetricTrendEvidence(
        metric_name=metric_name,
        season_value=season_value,
        last_20_value=last_20_value,
        last_10_value=last_10_value,
        last_20_change=(
            last_20_change
        ),
        last_10_change=(
            last_10_change
        ),
        state=state,
    )


def _relative_change(
    value: float,
    *,
    baseline: float,
    scale_floor: float,
) -> float:
    denominator = max(
        abs(
            baseline
        ),
        float(
            scale_floor
        ),
    )

    return (
        value
        - baseline
    ) / denominator


def _relative_evidence(
    *,
    metric_name: str,
    season_value: float,
    last_20_value: float,
    last_10_value: float,
    scale_floor: float,
) -> MetricTrendEvidence:
    last_20_change = (
        _relative_change(
            last_20_value,
            baseline=season_value,
            scale_floor=scale_floor,
        )
    )

    last_10_change = (
        _relative_change(
            last_10_value,
            baseline=season_value,
            scale_floor=scale_floor,
        )
    )

    threshold = (
        PROCESS_RELATIVE_CHANGE_THRESHOLD
    )

    if (
        last_20_change >= threshold
        and last_10_change >= threshold
    ):
        state = TREND_IMPROVING
    elif (
        last_20_change <= -threshold
        and last_10_change <= -threshold
    ):
        state = TREND_DECLINING
    elif (
        abs(last_20_change) < threshold
        and abs(last_10_change) < threshold
    ):
        state = TREND_STABLE
    else:
        state = TREND_MIXED

    return MetricTrendEvidence(
        metric_name=metric_name,
        season_value=season_value,
        last_20_value=last_20_value,
        last_10_value=last_10_value,
        last_20_change=(
            last_20_change
        ),
        last_10_change=(
            last_10_change
        ),
        state=state,
    )


def _toi_per_game(
    rate: SkaterPerformanceRate,
) -> float:
    games_played = int(
        rate.games_played
    )

    if games_played <= 0:
        raise TrendInterpretationError(
            "TOI/game requires a positive "
            "games_played sample."
        )

    seconds = float(
        rate.ice_time_seconds
    )

    if (
        not math.isfinite(
            seconds
        )
        or seconds < 0
    ):
        raise TrendInterpretationError(
            "ice_time_seconds was invalid."
        )

    return (
        seconds
        / games_played
        / 60.0
    )


def _sample_available(
    *,
    season_games: int,
    last_20_games: int,
    last_10_games: int,
    minimum_season_games: int,
    minimum_last_20_games: int,
    minimum_last_10_games: int,
) -> bool:
    return (
        season_games
        >= minimum_season_games
        and last_20_games
        >= minimum_last_20_games
        and last_10_games
        >= minimum_last_10_games
    )


def _role_state(
    *,
    sample_available: bool,
    toi_state: str,
    pp_state: str,
) -> str:
    if not sample_available:
        return (
            ROLE_INSUFFICIENT_SAMPLE
        )

    states = {
        toi_state,
        pp_state,
    }

    if (
        TREND_IMPROVING in states
        and TREND_DECLINING not in states
    ):
        return ROLE_EXPANDING

    if (
        TREND_DECLINING in states
        and TREND_IMPROVING not in states
    ):
        return ROLE_SHRINKING

    if states == {
        TREND_STABLE
    }:
        return ROLE_STABLE

    return ROLE_MIXED


def _process_state(
    *,
    sample_available: bool,
    evidence: Sequence[
        MetricTrendEvidence
    ],
) -> tuple[
    str,
    int,
    int,
    int,
    int,
]:
    improving = sum(
        row.state
        == TREND_IMPROVING
        for row in evidence
    )

    stable = sum(
        row.state
        == TREND_STABLE
        for row in evidence
    )

    declining = sum(
        row.state
        == TREND_DECLINING
        for row in evidence
    )

    mixed = sum(
        row.state
        == TREND_MIXED
        for row in evidence
    )

    if not sample_available:
        state = (
            TREND_INSUFFICIENT_SAMPLE
        )
    elif (
        improving >= 3
        and declining <= 1
    ):
        state = TREND_IMPROVING
    elif (
        declining >= 3
        and improving <= 1
    ):
        state = TREND_DECLINING
    elif (
        stable >= 3
        and improving <= 1
        and declining <= 1
    ):
        state = TREND_STABLE
    else:
        state = TREND_MIXED

    return (
        state,
        improving,
        stable,
        declining,
        mixed,
    )


def _finishing_state(
    *,
    sample_available: bool,
    season_value: float,
    last_20_value: float,
    last_10_value: float,
) -> str:
    if not sample_available:
        return (
            FINISHING_INSUFFICIENT_SAMPLE
        )

    threshold = (
        FINISHING_CHANGE_PER_60_THRESHOLD
    )

    last_20_change = (
        last_20_value
        - season_value
    )

    last_10_change = (
        last_10_value
        - season_value
    )

    if (
        last_20_change >= threshold
        and last_10_change >= threshold
    ):
        return FINISHING_HOT

    if (
        last_20_change <= -threshold
        and last_10_change <= -threshold
    ):
        return FINISHING_COLD

    if (
        abs(last_20_change) < threshold
        and abs(last_10_change) < threshold
    ):
        return FINISHING_NEUTRAL

    return FINISHING_MIXED


def build_skater_trend_interpretations(
    *,
    season_id: int,
    rates: Sequence[
        SkaterPerformanceRate
    ],
) -> tuple[
    SkaterTrendInterpretation,
    ...,
]:
    target_season = int(
        season_id
    )

    if target_season <= 0:
        raise TrendInterpretationError(
            "season_id must be positive."
        )

    index: dict[
        tuple[
            str,
            int,
            str,
        ],
        SkaterPerformanceRate,
    ] = {}

    sources: set[str] = set()

    for rate in rates:
        if (
            rate.season_id
            != target_season
        ):
            raise TrendInterpretationError(
                "Trend input contained a "
                "different season_id."
            )

        sources.add(
            rate.source
        )

        key = (
            rate.window,
            rate.nhl_player_id,
            rate.situation,
        )

        if key in index:
            raise TrendInterpretationError(
                "Duplicate trend-rate row: "
                f"{key!r}."
            )

        index[
            key
        ] = rate

    if len(sources) != 1:
        raise TrendInterpretationError(
            "Trend interpretation requires "
            "exactly one source."
        )

    source = next(
        iter(
            sources
        )
    )

    season_all = {
        player_id: rate
        for (
            window,
            player_id,
            situation,
        ), rate in index.items()
        if (
            window
            == WINDOW_SEASON
            and situation
            == SITUATION_ALL
        )
    }

    result: list[
        SkaterTrendInterpretation
    ] = []

    for player_id in sorted(
        season_all
    ):
        required_keys = (
            (
                WINDOW_SEASON,
                player_id,
                SITUATION_ALL,
            ),
            (
                WINDOW_LAST_20,
                player_id,
                SITUATION_ALL,
            ),
            (
                WINDOW_LAST_10,
                player_id,
                SITUATION_ALL,
            ),
            (
                WINDOW_SEASON,
                player_id,
                SITUATION_5_ON_4,
            ),
            (
                WINDOW_LAST_20,
                player_id,
                SITUATION_5_ON_4,
            ),
            (
                WINDOW_LAST_10,
                player_id,
                SITUATION_5_ON_4,
            ),
        )

        missing = [
            key
            for key in required_keys
            if key not in index
        ]

        if missing:
            raise TrendInterpretationError(
                "Player was missing required "
                "trend-rate rows: "
                f"{player_id}, {missing!r}."
            )

        season = index[
            required_keys[0]
        ]
        last_20 = index[
            required_keys[1]
        ]
        last_10 = index[
            required_keys[2]
        ]

        season_pp = index[
            required_keys[3]
        ]
        last_20_pp = index[
            required_keys[4]
        ]
        last_10_pp = index[
            required_keys[5]
        ]

        names = {
            season.full_name,
            last_20.full_name,
            last_10.full_name,
        }

        if len(names) != 1:
            raise TrendInterpretationError(
                "Player name changed across "
                f"trend windows for {player_id}."
            )

        season_games = int(
            season.games_played
        )
        last_20_games = int(
            last_20.games_played
        )
        last_10_games = int(
            last_10.games_played
        )

        role_available = (
            _sample_available(
                season_games=season_games,
                last_20_games=(
                    last_20_games
                ),
                last_10_games=(
                    last_10_games
                ),
                minimum_season_games=(
                    ROLE_MIN_SEASON_GAMES
                ),
                minimum_last_20_games=(
                    ROLE_MIN_LAST_20_GAMES
                ),
                minimum_last_10_games=(
                    ROLE_MIN_LAST_10_GAMES
                ),
            )
        )

        process_available = (
            _sample_available(
                season_games=season_games,
                last_20_games=(
                    last_20_games
                ),
                last_10_games=(
                    last_10_games
                ),
                minimum_season_games=(
                    PROCESS_MIN_SEASON_GAMES
                ),
                minimum_last_20_games=(
                    PROCESS_MIN_LAST_20_GAMES
                ),
                minimum_last_10_games=(
                    PROCESS_MIN_LAST_10_GAMES
                ),
            )
        )

        toi_evidence = (
            _absolute_evidence(
                metric_name=(
                    "toi_per_game_minutes"
                ),
                season_value=(
                    _toi_per_game(
                        season
                    )
                ),
                last_20_value=(
                    _toi_per_game(
                        last_20
                    )
                ),
                last_10_value=(
                    _toi_per_game(
                        last_10
                    )
                ),
                threshold=(
                    TOI_CHANGE_MINUTES
                ),
            )
        )

        pp_evidence = (
            _absolute_evidence(
                metric_name=(
                    "power_play_toi_per_game_minutes"
                ),
                season_value=(
                    _toi_per_game(
                        season_pp
                    )
                ),
                last_20_value=(
                    _toi_per_game(
                        last_20_pp
                    )
                ),
                last_10_value=(
                    _toi_per_game(
                        last_10_pp
                    )
                ),
                threshold=(
                    POWER_PLAY_TOI_CHANGE_MINUTES
                ),
            )
        )

        process_evidence: list[
            MetricTrendEvidence
        ] = []

        for (
            metric_name,
            scale_floor,
        ) in _PROCESS_METRICS:
            process_evidence.append(
                _relative_evidence(
                    metric_name=metric_name,
                    season_value=(
                        _finite(
                            getattr(
                                season,
                                metric_name,
                            ),
                            label=(
                                f"{metric_name} season"
                            ),
                        )
                    ),
                    last_20_value=(
                        _finite(
                            getattr(
                                last_20,
                                metric_name,
                            ),
                            label=(
                                f"{metric_name} last20"
                            ),
                        )
                    ),
                    last_10_value=(
                        _finite(
                            getattr(
                                last_10,
                                metric_name,
                            ),
                            label=(
                                f"{metric_name} last10"
                            ),
                        )
                    ),
                    scale_floor=scale_floor,
                )
            )

        (
            process_state,
            improving_count,
            stable_count,
            declining_count,
            mixed_count,
        ) = _process_state(
            sample_available=(
                process_available
            ),
            evidence=(
                process_evidence
            ),
        )

        season_finishing = _finite(
            season
            .goals_minus_expected_per_60,
            label="season finishing",
        )

        last_20_finishing = _finite(
            last_20
            .goals_minus_expected_per_60,
            label="last20 finishing",
        )

        last_10_finishing = _finite(
            last_10
            .goals_minus_expected_per_60,
            label="last10 finishing",
        )

        result.append(
            SkaterTrendInterpretation(
                source=source,
                season_id=(
                    target_season
                ),
                nhl_player_id=(
                    player_id
                ),
                full_name=(
                    last_10.full_name
                ),
                nhl_team_abbr=(
                    last_10.nhl_team_abbr
                ),
                position=(
                    last_10.position
                ),
                season_games_played=(
                    season_games
                ),
                last_20_games_played=(
                    last_20_games
                ),
                last_10_games_played=(
                    last_10_games
                ),
                role_sample_state=(
                    SAMPLE_AVAILABLE
                    if role_available
                    else SAMPLE_INSUFFICIENT
                ),
                process_sample_state=(
                    SAMPLE_AVAILABLE
                    if process_available
                    else SAMPLE_INSUFFICIENT
                ),
                toi_usage=(
                    toi_evidence
                ),
                power_play_toi_usage=(
                    pp_evidence
                ),
                role_state=(
                    _role_state(
                        sample_available=(
                            role_available
                        ),
                        toi_state=(
                            toi_evidence.state
                        ),
                        pp_state=(
                            pp_evidence.state
                        ),
                    )
                ),
                process_metrics=tuple(
                    process_evidence
                ),
                process_state=(
                    process_state
                ),
                process_improving_metrics=(
                    improving_count
                ),
                process_stable_metrics=(
                    stable_count
                ),
                process_declining_metrics=(
                    declining_count
                ),
                process_mixed_metrics=(
                    mixed_count
                ),
                finishing_state=(
                    _finishing_state(
                        sample_available=(
                            process_available
                        ),
                        season_value=(
                            season_finishing
                        ),
                        last_20_value=(
                            last_20_finishing
                        ),
                        last_10_value=(
                            last_10_finishing
                        ),
                    )
                ),
                season_goals_minus_expected_per_60=(
                    season_finishing
                ),
                last_20_goals_minus_expected_per_60=(
                    last_20_finishing
                ),
                last_10_goals_minus_expected_per_60=(
                    last_10_finishing
                ),
            )
        )

    return tuple(
        result
    )
