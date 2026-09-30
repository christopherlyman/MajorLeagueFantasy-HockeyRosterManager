from __future__ import annotations

from collections.abc import Mapping, Sequence

from hockey_rmt.domain.league import (
    LeagueDefinition,
)
from hockey_rmt.domain.player_stats import (
    FantasyPointComponent,
    GoalieSeasonStats,
    HistoricalFantasyValue,
    SkaterSeasonStats,
)


class FantasyValueError(RuntimeError):
    """Fantasy scoring calculation failed."""


SKATER_CATEGORIES = (
    "G",
    "A",
    "PIM",
    "PPP",
    "SHP",
    "SOG",
    "HIT",
    "BLK",
)

REQUIRED_GOALIE_CATEGORIES = (
    "W",
    "GA",
    "SV",
    "SHO",
)

OPTIONAL_GOALIE_CATEGORIES = (
    "L",
    "OTL",
)

GOALIE_CATEGORIES = (
    "W",
    "L",
    "OTL",
    "GA",
    "SV",
    "SHO",
)

SCORING_ABBREVIATION_ALIASES = {
    "SO": "SHO",
}


def scoring_weights(
    league: LeagueDefinition,
) -> dict[str, float]:
    result: dict[str, float] = {}

    for rule in league.scoring_rules:
        raw_abbreviation = (
            rule.abbreviation
        )

        if not raw_abbreviation:
            continue

        abbreviation = (
            SCORING_ABBREVIATION_ALIASES.get(
                raw_abbreviation,
                raw_abbreviation,
            )
        )

        if abbreviation in result:
            raise FantasyValueError(
                "Duplicate league scoring "
                f"abbreviation "
                f"{abbreviation!r}."
            )

        result[
            abbreviation
        ] = float(
            rule.points
        )

    required = (
        SKATER_CATEGORIES
        + REQUIRED_GOALIE_CATEGORIES
    )

    missing = [
        category
        for category in required
        if category not in result
    ]

    if missing:
        raise FantasyValueError(
            "League scoring definition is "
            "missing required categories: "
            + ", ".join(missing)
        )

    for category in OPTIONAL_GOALIE_CATEGORIES:
        result.setdefault(
            category,
            0.0,
        )

    return result


def _components(
    values: Mapping[str, float],
    weights: Mapping[str, float],
    categories: Sequence[str],
) -> tuple[
    FantasyPointComponent,
    ...,
]:
    result = []

    for category in categories:
        stat_value = float(
            values[
                category
            ]
        )

        points_per_unit = float(
            weights[
                category
            ]
        )

        result.append(
            FantasyPointComponent(
                category=category,
                stat_value=stat_value,
                points_per_unit=(
                    points_per_unit
                ),
                fantasy_points=(
                    stat_value
                    * points_per_unit
                ),
            )
        )

    return tuple(result)


def _historical_value(
    *,
    nhl_player_id: int,
    full_name: str,
    player_type: str,
    season_id: int,
    games_played: int,
    components: tuple[
        FantasyPointComponent,
        ...,
    ],
) -> HistoricalFantasyValue:
    fantasy_points = sum(
        component.fantasy_points
        for component in components
    )

    fantasy_points_per_game = (
        fantasy_points
        / games_played
        if games_played > 0
        else None
    )

    return HistoricalFantasyValue(
        nhl_player_id=nhl_player_id,
        full_name=full_name,
        player_type=player_type,
        season_id=season_id,
        games_played=games_played,
        fantasy_points=fantasy_points,
        fantasy_points_per_game=(
            fantasy_points_per_game
        ),
        components=components,
    )


def score_skater(
    stats: SkaterSeasonStats,
    league: LeagueDefinition,
) -> HistoricalFantasyValue:
    weights = scoring_weights(
        league
    )

    values = {
        "G": stats.goals,
        "A": stats.assists,
        "PIM": stats.penalty_minutes,
        "PPP": stats.power_play_points,
        "SHP": stats.short_handed_points,
        "SOG": stats.shots,
        "HIT": stats.hits,
        "BLK": stats.blocked_shots,
    }

    return _historical_value(
        nhl_player_id=(
            stats.nhl_player_id
        ),
        full_name=stats.full_name,
        player_type="skater",
        season_id=stats.season_id,
        games_played=(
            stats.games_played
        ),
        components=_components(
            values,
            weights,
            SKATER_CATEGORIES,
        ),
    )


def _goalie_stat_value(
    value: int | None,
    *,
    category: str,
    points_per_unit: float,
) -> float:
    if value is not None:
        return float(value)

    if float(points_per_unit) != 0.0:
        raise FantasyValueError(
            "Goalie stat evidence for "
            f"{category!r} is unavailable, "
            "but the league assigns that "
            "category a non-zero score."
        )

    return 0.0


def score_goalie(
    stats: GoalieSeasonStats,
    league: LeagueDefinition,
) -> HistoricalFantasyValue:
    weights = scoring_weights(
        league
    )

    values = {
        "W": stats.wins,
        "L": _goalie_stat_value(
            stats.losses,
            category="L",
            points_per_unit=weights["L"],
        ),
        "OTL": _goalie_stat_value(
            stats.overtime_losses,
            category="OTL",
            points_per_unit=weights["OTL"],
        ),
        "GA": stats.goals_against,
        "SV": stats.saves,
        "SHO": stats.shutouts,
    }

    return _historical_value(
        nhl_player_id=(
            stats.nhl_player_id
        ),
        full_name=stats.full_name,
        player_type="goalie",
        season_id=stats.season_id,
        games_played=(
            stats.games_played
        ),
        components=_components(
            values,
            weights,
            GOALIE_CATEGORIES,
        ),
    )


def score_historical_season(
    *,
    skaters: Sequence[
        SkaterSeasonStats
    ],
    goalies: Sequence[
        GoalieSeasonStats
    ],
    league: LeagueDefinition,
) -> tuple[
    HistoricalFantasyValue,
    ...,
]:
    values = [
        score_skater(
            stats,
            league,
        )
        for stats in skaters
    ]

    values.extend(
        score_goalie(
            stats,
            league,
        )
        for stats in goalies
    )

    ids = [
        value.nhl_player_id
        for value in values
    ]

    if len(ids) != len(set(ids)):
        raise FantasyValueError(
            "Historical value set contained "
            "duplicate NHL playerId values."
        )

    return tuple(values)
