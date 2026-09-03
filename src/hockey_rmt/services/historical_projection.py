from __future__ import annotations

from collections.abc import Mapping, Sequence

from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.projection import (
    HISTORICAL_PROJECTION_AVAILABLE,
    NO_NHL_HISTORY,
    HistoricalRateProjection,
)


class HistoricalProjectionError(RuntimeError):
    """Historical projection construction failed."""


DECAY_WEIGHTS = (
    0.25,
    0.50,
    1.00,
)

SKATER_SHRINKAGE_GAMES = 10.0
GOALIE_SHRINKAGE_GAMES = 40.0


def _validate_seasons(
    seasons: Sequence[int],
) -> tuple[int, ...]:
    result = tuple(
        int(season)
        for season in seasons
    )

    if len(result) != len(
        DECAY_WEIGHTS
    ):
        raise HistoricalProjectionError(
            "Historical projection requires "
            f"{len(DECAY_WEIGHTS)} prior seasons."
        )

    if tuple(sorted(result)) != result:
        raise HistoricalProjectionError(
            "Prior seasons must be ordered "
            "oldest to newest."
        )

    if len(set(result)) != len(result):
        raise HistoricalProjectionError(
            "Prior seasons contained duplicates."
        )

    return result


def _value_map(
    values: Sequence[
        HistoricalFantasyValue
    ],
    *,
    expected_player_type: str,
    expected_season_id: int,
) -> dict[int, HistoricalFantasyValue]:
    result = {}

    for value in values:
        if (
            value.player_type
            != expected_player_type
        ):
            raise HistoricalProjectionError(
                "Historical value player type "
                "did not match projection input."
            )

        if (
            value.season_id
            != expected_season_id
        ):
            raise HistoricalProjectionError(
                "Historical value season did not "
                "match projection input."
            )

        if (
            value.nhl_player_id
            in result
        ):
            raise HistoricalProjectionError(
                "Duplicate NHL playerId in "
                "historical season values: "
                f"{value.nhl_player_id}."
            )

        result[
            value.nhl_player_id
        ] = value

    return result


def _population_mean(
    season_maps: Sequence[
        Mapping[
            int,
            HistoricalFantasyValue,
        ]
    ],
) -> float:
    weighted_points = 0.0
    weighted_games = 0.0

    for season_map, decay_weight in zip(
        season_maps,
        DECAY_WEIGHTS,
    ):
        for value in season_map.values():
            if value.games_played <= 0:
                continue

            weighted_points += (
                value.fantasy_points
                * decay_weight
            )

            weighted_games += (
                value.games_played
                * decay_weight
            )

    if weighted_games <= 0:
        raise HistoricalProjectionError(
            "Historical population contained "
            "no positive games played."
        )

    return (
        weighted_points
        / weighted_games
    )


def build_historical_rate_projections(
    *,
    player_type: str,
    seasons: Sequence[int],
    historical_values_by_season: Mapping[
        int,
        Sequence[
            HistoricalFantasyValue
        ],
    ],
) -> tuple[
    HistoricalRateProjection,
    ...,
]:
    seasons = _validate_seasons(
        seasons
    )

    if player_type == "skater":
        shrinkage_games = (
            SKATER_SHRINKAGE_GAMES
        )
    elif player_type == "goalie":
        shrinkage_games = (
            GOALIE_SHRINKAGE_GAMES
        )
    else:
        raise HistoricalProjectionError(
            "Unsupported player type "
            f"{player_type!r}."
        )

    season_maps = []

    for season_id in seasons:
        if (
            season_id
            not in historical_values_by_season
        ):
            raise HistoricalProjectionError(
                "Missing historical values for "
                f"season {season_id}."
            )

        season_maps.append(
            _value_map(
                historical_values_by_season[
                    season_id
                ],
                expected_player_type=(
                    player_type
                ),
                expected_season_id=(
                    season_id
                ),
            )
        )

    population_mean = _population_mean(
        season_maps
    )

    player_ids = set()

    for season_map in season_maps:
        player_ids.update(
            season_map
        )

    result = []

    for player_id in sorted(
        player_ids
    ):
        historical_points = 0.0
        effective_games = 0.0
        raw_games = 0
        seasons_used = 0
        full_name = None

        for (
            season_map,
            decay_weight,
        ) in zip(
            season_maps,
            DECAY_WEIGHTS,
        ):
            value = season_map.get(
                player_id
            )

            if value is None:
                continue

            if value.games_played <= 0:
                continue

            if full_name is None:
                full_name = value.full_name

            historical_points += (
                value.fantasy_points
                * decay_weight
            )

            effective_games += (
                value.games_played
                * decay_weight
            )

            raw_games += (
                value.games_played
            )

            seasons_used += 1

        if (
            effective_games <= 0
            or full_name is None
        ):
            continue

        unshrunk_rate = (
            historical_points
            / effective_games
        )

        projected_rate = (
            (
                unshrunk_rate
                * effective_games
            )
            + (
                population_mean
                * shrinkage_games
            )
        ) / (
            effective_games
            + shrinkage_games
        )

        result.append(
            HistoricalRateProjection(
                nhl_player_id=player_id,
                full_name=full_name,
                player_type=player_type,
                projection_state=(
                    HISTORICAL_PROJECTION_AVAILABLE
                ),
                projected_fantasy_points_per_game=(
                    projected_rate
                ),
                historical_seasons_used=(
                    seasons_used
                ),
                historical_games_played=(
                    raw_games
                ),
                effective_games_played=(
                    effective_games
                ),
                unshrunk_fantasy_points_per_game=(
                    unshrunk_rate
                ),
                population_mean_fantasy_points_per_game=(
                    population_mean
                ),
                shrinkage_games=(
                    shrinkage_games
                ),
            )
        )

    return tuple(result)


def no_history_projection(
    *,
    nhl_player_id: int,
    full_name: str,
    player_type: str,
) -> HistoricalRateProjection:
    return HistoricalRateProjection(
        nhl_player_id=nhl_player_id,
        full_name=full_name,
        player_type=player_type,
        projection_state=NO_NHL_HISTORY,
        projected_fantasy_points_per_game=None,
        historical_seasons_used=0,
        historical_games_played=0,
        effective_games_played=0.0,
        unshrunk_fantasy_points_per_game=None,
        population_mean_fantasy_points_per_game=None,
        shrinkage_games=(
            SKATER_SHRINKAGE_GAMES
            if player_type == "skater"
            else GOALIE_SHRINKAGE_GAMES
        ),
    )
