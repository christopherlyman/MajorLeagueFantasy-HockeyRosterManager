from __future__ import annotations

from collections.abc import Sequence

from hockey_rmt.domain.current_production import (
    CURRENT_PRODUCTION_AVAILABLE,
    CURRENT_PRODUCTION_IDENTITY_UNRESOLVED,
    CURRENT_PRODUCTION_NO_SAMPLE,
    CURRENT_PRODUCTION_SOURCE_OFFICIAL_NHL,
    CurrentSeasonProduction,
)
from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.player_strength import (
    PlayerStrengthProjection,
)


class CurrentProductionError(
    RuntimeError
):
    """Current-season production construction failed."""


def build_current_season_production(
    *,
    player_strengths: Sequence[
        PlayerStrengthProjection
    ],
    season_values: Sequence[
        HistoricalFantasyValue
    ],
    season_id: int,
) -> tuple[
    CurrentSeasonProduction,
    ...,
]:
    requested_season = int(
        season_id
    )

    provider_keys = [
        str(
            player.provider_player_key
        )
        for player in player_strengths
    ]

    if (
        len(provider_keys)
        != len(
            set(
                provider_keys
            )
        )
    ):
        raise CurrentProductionError(
            "Player-strength input contained "
            "duplicate provider player keys."
        )

    for player in player_strengths:
        if (
            int(
                player.projection_season_id
            )
            != requested_season
        ):
            raise CurrentProductionError(
                "Player-strength projection season "
                "did not match requested current "
                "season for provider player "
                f"{player.provider_player_key!r}: "
                f"{player.projection_season_id} "
                f"!= {requested_season}."
            )

    value_by_nhl_id: dict[
        int,
        HistoricalFantasyValue,
    ] = {}

    for value in season_values:
        if (
            int(
                value.season_id
            )
            != requested_season
        ):
            raise CurrentProductionError(
                "Season fantasy value contained "
                "the wrong season: "
                f"NHL playerId "
                f"{value.nhl_player_id}, "
                f"{value.season_id} "
                f"!= {requested_season}."
            )

        nhl_player_id = int(
            value.nhl_player_id
        )

        if (
            nhl_player_id
            in value_by_nhl_id
        ):
            raise CurrentProductionError(
                "Season fantasy values contained "
                "duplicate NHL playerId "
                f"{nhl_player_id}."
            )

        if value.games_played < 0:
            raise CurrentProductionError(
                "Season fantasy value contained "
                "negative games played for "
                f"NHL playerId {nhl_player_id}."
            )

        if (
            value.games_played > 0
            and value.fantasy_points_per_game
            is None
        ):
            raise CurrentProductionError(
                "Season fantasy value with games "
                "played was missing FPPG for "
                f"NHL playerId {nhl_player_id}."
            )

        value_by_nhl_id[
            nhl_player_id
        ] = value

    result = []

    seen_resolved_nhl_ids = set()

    for player in player_strengths:
        provider_key = str(
            player.provider_player_key
        )

        canonical_player_type = str(
            player.player_type
        ).strip()

        player_type = {
            "P": "skater",
            "G": "goalie",
            "skater": "skater",
            "goalie": "goalie",
        }.get(
            canonical_player_type
        )

        if player_type is None:
            raise CurrentProductionError(
                "Unsupported player type for "
                f"{provider_key!r}: "
                f"{canonical_player_type!r}."
            )

        if player.nhl_player_id is None:
            result.append(
                CurrentSeasonProduction(
                    provider_player_key=(
                        provider_key
                    ),
                    full_name=(
                        player.full_name
                    ),
                    season_id=(
                        requested_season
                    ),
                    player_type=(
                        player_type
                    ),
                    nhl_player_id=None,
                    production_state=(
                        CURRENT_PRODUCTION_IDENTITY_UNRESOLVED
                    ),
                    production_source=(
                        CURRENT_PRODUCTION_SOURCE_OFFICIAL_NHL
                    ),
                    games_played=0,
                    fantasy_points=None,
                    fantasy_points_per_game=None,
                    components=None,
                )
            )

            continue

        nhl_player_id = int(
            player.nhl_player_id
        )

        if (
            nhl_player_id
            in seen_resolved_nhl_ids
        ):
            raise CurrentProductionError(
                "Player-strength input assigned "
                "one NHL playerId to multiple "
                "provider players: "
                f"{nhl_player_id}."
            )

        seen_resolved_nhl_ids.add(
            nhl_player_id
        )

        value = value_by_nhl_id.get(
            nhl_player_id
        )

        if (
            value is None
            or value.games_played == 0
        ):
            result.append(
                CurrentSeasonProduction(
                    provider_player_key=(
                        provider_key
                    ),
                    full_name=(
                        player.full_name
                    ),
                    season_id=(
                        requested_season
                    ),
                    player_type=(
                        player_type
                    ),
                    nhl_player_id=(
                        nhl_player_id
                    ),
                    production_state=(
                        CURRENT_PRODUCTION_NO_SAMPLE
                    ),
                    production_source=(
                        CURRENT_PRODUCTION_SOURCE_OFFICIAL_NHL
                    ),
                    games_played=0,
                    fantasy_points=None,
                    fantasy_points_per_game=None,
                    components=None,
                )
            )

            continue

        if (
            value.player_type
            != player_type
        ):
            raise CurrentProductionError(
                "Season fantasy value player type "
                "did not match player strength for "
                f"NHL playerId {nhl_player_id}: "
                f"{value.player_type!r} "
                f"!= {player_type!r}."
            )

        if (
            value.fantasy_points_per_game
            is None
        ):
            raise CurrentProductionError(
                "Available current-season value "
                "was missing fantasy points per "
                f"game for NHL playerId "
                f"{nhl_player_id}."
            )

        result.append(
            CurrentSeasonProduction(
                provider_player_key=(
                    provider_key
                ),
                full_name=(
                    player.full_name
                ),
                season_id=(
                    requested_season
                ),
                player_type=(
                    player_type
                ),
                nhl_player_id=(
                    nhl_player_id
                ),
                production_state=(
                    CURRENT_PRODUCTION_AVAILABLE
                ),
                production_source=(
                    CURRENT_PRODUCTION_SOURCE_OFFICIAL_NHL
                ),
                games_played=(
                    value.games_played
                ),
                fantasy_points=(
                    value.fantasy_points
                ),
                fantasy_points_per_game=(
                    value.fantasy_points_per_game
                ),
                components=(
                    value.components
                ),
            )
        )

    if (
        len(result)
        != len(
            player_strengths
        )
    ):
        raise CurrentProductionError(
            "Current-production result count "
            "did not match player-strength "
            "input count."
        )

    result_keys = [
        row.provider_player_key
        for row in result
    ]

    if result_keys != provider_keys:
        raise CurrentProductionError(
            "Current-production result order "
            "did not preserve player-strength "
            "input order."
        )

    return tuple(
        result
    )
