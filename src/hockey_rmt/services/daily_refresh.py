from __future__ import annotations

from hockey_rmt.domain.projection_adjustment import (
    PlayerProjectionAdjustment,
)

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_strength import (
    PlayerStrengthProjection,
)
from hockey_rmt.services.daily_value import (
    build_baseline_daily_expected_values,
)
from hockey_rmt.services.schedule_context import (
    build_player_game_context,
)
from hockey_rmt.services.team_identity import (
    build_yahoo_nhl_crosswalk,
)
from hockey_rmt.services.three_day_rankings import (
    build_three_day_player_rankings,
)
from hockey_rmt.ui.three_day_snapshot import (
    build_three_day_snapshot_payload,
    enrich_three_day_snapshot_availability,
    enrich_three_day_snapshot_market,
    enrich_three_day_snapshot_percent_rostered,
)


class DailyRefreshError(
    RuntimeError
):
    """Three-day refresh construction failed."""


def build_three_day_refresh_payload(
    *,
    players: Sequence[
        Player
    ],
    player_strengths: Sequence[
        PlayerStrengthProjection
    ],
    nhl_teams: Sequence[
        object
    ],
    games: Sequence[
        object
    ],
    market_states: Sequence[
        object
    ],
    percent_rostered_by_player_key: Mapping[
        str,
        int,
    ],
    projection_season_id: int,
    base_date: date,
    managed_team_key: str,
    league_name: str,
    team_name: str,
    model_label: str,
    projection_adjustments: Sequence[
        PlayerProjectionAdjustment
    ] = (),
) -> dict[
    str,
    Any,
]:
    player_rows = tuple(
        players
    )

    strength_rows = tuple(
        player_strengths
    )

    market_rows = tuple(
        market_states
    )

    if not player_rows:
        raise DailyRefreshError(
            "Yahoo player universe was empty."
        )

    player_keys = tuple(
        str(
            row.provider_player_key
        )
        for row in player_rows
    )

    strength_keys = tuple(
        str(
            row.provider_player_key
        )
        for row in strength_rows
    )

    if (
        len(
            player_keys
        )
        != len(
            set(
                player_keys
            )
        )
    ):
        raise DailyRefreshError(
            "Yahoo player universe contained "
            "duplicate player keys."
        )

    if (
        len(
            strength_keys
        )
        != len(
            set(
                strength_keys
            )
        )
    ):
        raise DailyRefreshError(
            "Strength artifact contained "
            "duplicate player keys."
        )

    if (
        set(
            player_keys
        )
        != set(
            strength_keys
        )
    ):
        raise DailyRefreshError(
            "Yahoo player universe does not "
            "exactly match canonical strength "
            "artifact."
        )

    crosswalk = (
        build_yahoo_nhl_crosswalk(
            player_rows,
            tuple(
                nhl_teams
            ),
        )
    )

    daily_values_by_date = {}

    for offset in range(
        3
    ):
        game_date = (
            base_date
            + timedelta(
                days=offset
            )
        )

        contexts = tuple(
            build_player_game_context(
                player,
                games,
                game_date,
                crosswalk,
            )
            for player in player_rows
        )

        daily_values_by_date[
            game_date
        ] = (
            build_baseline_daily_expected_values(
                player_strengths=(
                    strength_rows
                ),
                game_contexts=(
                    contexts
                ),
                season_id=(
                    projection_season_id
                ),
                game_date=(
                    game_date
                ),
                projection_adjustments=(
                    projection_adjustments
                ),
            )
        )

    rankings = (
        build_three_day_player_rankings(
            daily_values_by_date=(
                daily_values_by_date
            ),
            base_date=(
                base_date
            ),
        )
    )

    payload = (
        build_three_day_snapshot_payload(
            rows=rankings,
            league_name=(
                league_name
            ),
            team_name=(
                team_name
            ),
            model_label=(
                model_label
            ),
        )
    )

    payload = (
        enrich_three_day_snapshot_availability(
            payload,
            players=player_rows,
        )
    )

    payload = (
        enrich_three_day_snapshot_market(
            payload,
            players=player_rows,
            market_states=market_rows,
            managed_team_key=(
                managed_team_key
            ),
        )
    )

    payload = (
        enrich_three_day_snapshot_percent_rostered(
            payload,
            percent_rostered_by_player_key=(
                percent_rostered_by_player_key
            ),
        )
    )

    return payload
