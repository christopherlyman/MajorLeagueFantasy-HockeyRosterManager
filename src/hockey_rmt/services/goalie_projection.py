from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence

from hockey_rmt.domain.goalie_projection import (
    QUALITY_HISTORICAL_RATE,
    QUALITY_POPULATION_PRIOR,
    WORKLOAD_EXTERNAL_IMPLIED_ZERO,
    WORKLOAD_EXTERNAL_PROJECTED,
    WORKLOAD_IDENTITY_UNRESOLVED,
    WORKLOAD_INTERNAL_FALLBACK,
    WORKLOAD_NO_CURRENT_NHL_ROSTER,
    PreseasonGoalieProjection,
)
from hockey_rmt.domain.goalie_workload import (
    GoalieWorkloadProjection,
)
from hockey_rmt.domain.nhl_roster import (
    CurrentNhlGoalie,
)
from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    PlayerIdentityResolution,
)
from hockey_rmt.domain.projection import (
    HISTORICAL_PROJECTION_AVAILABLE,
    HistoricalRateProjection,
)
from hockey_rmt.services.player_identity import (
    normalize_player_name,
)


class GoalieProjectionError(RuntimeError):
    """Preseason goalie projection construction failed."""


def _goalie_population_mean(
    historical_quality: Sequence[
        HistoricalRateProjection
    ],
) -> float:
    values = []

    for row in historical_quality:
        if row.player_type != "goalie":
            raise GoalieProjectionError(
                "Non-goalie historical "
                "projection supplied to goalie "
                "projection service."
            )

        value = (
            row.population_mean_fantasy_points_per_game
        )

        if value is not None:
            values.append(
                float(value)
            )

    if not values:
        raise GoalieProjectionError(
            "Historical goalie projections "
            "did not contain a population mean."
        )

    reference = values[0]

    if not math.isfinite(
        reference
    ):
        raise GoalieProjectionError(
            "Goalie population mean was "
            "not finite."
        )

    for value in values[1:]:
        if not math.isclose(
            value,
            reference,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise GoalieProjectionError(
                "Historical goalie projections "
                "contained inconsistent "
                "population means."
            )

    return reference


def build_preseason_goalie_projections(
    *,
    projection_season_id: int,
    players: Sequence[Player],
    identity_resolutions: Sequence[
        PlayerIdentityResolution
    ],
    current_nhl_goalies: Sequence[
        CurrentNhlGoalie
    ],
    historical_quality: Sequence[
        HistoricalRateProjection
    ],
    external_workload: Sequence[
        GoalieWorkloadProjection
    ] | None,
    fallback_projected_starts_by_nhl_id: (
        Mapping[int, float] | None
    ) = None,
    fallback_source: str = (
        "historical_workload_model"
    ),
) -> tuple[
    PreseasonGoalieProjection,
    ...,
]:
    goalie_players = [
        player
        for player in players
        if player.position_type == "G"
    ]

    identity_by_key = {}

    for row in identity_resolutions:
        key = (
            row.provider_player_key
        )

        if key in identity_by_key:
            raise GoalieProjectionError(
                "Duplicate player identity "
                f"resolution for {key!r}."
            )

        identity_by_key[
            key
        ] = row

    current_team_by_nhl_id = {}

    for row in current_nhl_goalies:
        if (
            row.nhl_player_id
            in current_team_by_nhl_id
        ):
            raise GoalieProjectionError(
                "NHL goalie appeared on "
                "multiple current NHL rosters: "
                f"{row.nhl_player_id}."
            )

        current_team_by_nhl_id[
            row.nhl_player_id
        ] = row.nhl_team_abbr

    quality_by_nhl_id = {}

    for row in historical_quality:
        if row.player_type != "goalie":
            raise GoalieProjectionError(
                "Historical quality input "
                "contained a non-goalie."
            )

        if (
            row.nhl_player_id
            in quality_by_nhl_id
        ):
            raise GoalieProjectionError(
                "Duplicate historical goalie "
                "projection for NHL playerId "
                f"{row.nhl_player_id}."
            )

        quality_by_nhl_id[
            row.nhl_player_id
        ] = row

    population_mean = (
        _goalie_population_mean(
            historical_quality
        )
    )

    external_by_key = defaultdict(
        list
    )

    external_source = None

    if external_workload is not None:
        for row in external_workload:
            if (
                row.projection_season_id
                != int(
                    projection_season_id
                )
            ):
                raise GoalieProjectionError(
                    "External goalie workload "
                    "season did not match "
                    "projection season."
                )

            if (
                external_source is None
            ):
                external_source = (
                    row.source
                )
            elif (
                row.source
                != external_source
            ):
                raise GoalieProjectionError(
                    "External goalie workload "
                    "contained multiple sources."
                )

            key = (
                normalize_player_name(
                    row.full_name
                ),
                row.nhl_team_abbr,
            )

            external_by_key[
                key
            ].append(
                row
            )

        for key, rows in (
            external_by_key.items()
        ):
            if len(rows) != 1:
                raise GoalieProjectionError(
                    "External goalie workload "
                    "contained duplicate "
                    "normalized player/team key "
                    f"{key!r}."
                )

    fallback = {
        int(player_id): float(starts)
        for player_id, starts
        in (
            fallback_projected_starts_by_nhl_id
            or {}
        ).items()
    }

    for player_id, starts in fallback.items():
        if (
            not math.isfinite(starts)
            or starts < 0
        ):
            raise GoalieProjectionError(
                "Fallback goalie workload "
                "was invalid for NHL playerId "
                f"{player_id}: {starts!r}."
            )

    result = []

    for player in sorted(
        goalie_players,
        key=lambda row: (
            row.full_name,
            row.provider_player_key,
        ),
    ):
        identity = identity_by_key.get(
            player.provider_player_key
        )

        if (
            identity is None
            or identity.resolution_state
            != "resolved"
            or identity.nhl_player_id
            is None
        ):
            result.append(
                PreseasonGoalieProjection(
                    provider_player_key=(
                        player.provider_player_key
                    ),
                    full_name=(
                        player.full_name
                    ),
                    projection_season_id=int(
                        projection_season_id
                    ),
                    nhl_player_id=None,
                    nhl_team_abbr=None,
                    quality_state=None,
                    projected_fantasy_points_per_game=None,
                    historical_games_played=0,
                    historical_seasons_used=0,
                    workload_state=(
                        WORKLOAD_IDENTITY_UNRESOLVED
                    ),
                    workload_source=None,
                    projected_games_started=None,
                    projected_start_based_fantasy_points=None,
                )
            )
            continue

        nhl_player_id = int(
            identity.nhl_player_id
        )

        current_team = (
            current_team_by_nhl_id.get(
                nhl_player_id
            )
        )

        historical = (
            quality_by_nhl_id.get(
                nhl_player_id
            )
        )

        if (
            historical is not None
            and historical.projection_state
            == HISTORICAL_PROJECTION_AVAILABLE
            and historical.projected_fantasy_points_per_game
            is not None
        ):
            quality_state = (
                QUALITY_HISTORICAL_RATE
            )

            quality_fppg = float(
                historical
                .projected_fantasy_points_per_game
            )

            historical_games = (
                historical
                .historical_games_played
            )

            historical_seasons = (
                historical
                .historical_seasons_used
            )
        else:
            quality_state = (
                QUALITY_POPULATION_PRIOR
            )

            quality_fppg = (
                population_mean
            )

            historical_games = 0
            historical_seasons = 0

        if current_team is None:
            workload_state = (
                WORKLOAD_NO_CURRENT_NHL_ROSTER
            )

            workload_source = (
                external_source
                if external_workload
                is not None
                else fallback_source
            )

            projected_starts = 0.0

        elif external_workload is not None:
            identity_name = (
                identity.nhl_full_name
                or player.full_name
            )

            key = (
                normalize_player_name(
                    identity_name
                ),
                current_team,
            )

            rows = external_by_key.get(
                key,
                [],
            )

            if len(rows) == 1:
                workload_state = (
                    WORKLOAD_EXTERNAL_PROJECTED
                )

                workload_source = (
                    rows[0].source
                )

                projected_starts = float(
                    rows[0]
                    .projected_games_started
                )

            elif len(rows) == 0:
                workload_state = (
                    WORKLOAD_EXTERNAL_IMPLIED_ZERO
                )

                workload_source = (
                    external_source
                )

                projected_starts = 0.0

            else:
                raise GoalieProjectionError(
                    "Multiple external workload "
                    "rows matched goalie "
                    f"{player.full_name!r}."
                )

        else:
            if (
                nhl_player_id
                not in fallback
            ):
                raise GoalieProjectionError(
                    "No external goalie workload "
                    "was supplied and no internal "
                    "fallback workload exists for "
                    f"NHL playerId {nhl_player_id} "
                    f"({player.full_name})."
                )

            workload_state = (
                WORKLOAD_INTERNAL_FALLBACK
            )

            workload_source = (
                fallback_source
            )

            projected_starts = (
                fallback[
                    nhl_player_id
                ]
            )

        projected_points = (
            quality_fppg
            * projected_starts
        )

        result.append(
            PreseasonGoalieProjection(
                provider_player_key=(
                    player.provider_player_key
                ),
                full_name=(
                    player.full_name
                ),
                projection_season_id=int(
                    projection_season_id
                ),
                nhl_player_id=(
                    nhl_player_id
                ),
                nhl_team_abbr=(
                    current_team
                ),
                quality_state=(
                    quality_state
                ),
                projected_fantasy_points_per_game=(
                    quality_fppg
                ),
                historical_games_played=(
                    historical_games
                ),
                historical_seasons_used=(
                    historical_seasons
                ),
                workload_state=(
                    workload_state
                ),
                workload_source=(
                    workload_source
                ),
                projected_games_started=(
                    projected_starts
                ),
                projected_start_based_fantasy_points=(
                    projected_points
                ),
            )
        )

    return tuple(
        result
    )
