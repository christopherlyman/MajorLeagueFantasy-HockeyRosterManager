from __future__ import annotations

from collections.abc import Sequence

from hockey_rmt.domain.deployment import (
    SourcePlayerDeployment,
    SourceTeamDeploymentSnapshot,
)
from hockey_rmt.domain.performance_trend import (
    SkaterPerformanceTrend,
)
from hockey_rmt.domain.player_identity import (
    NhlPlayerIdentity,
)
from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.player_strength import (
    PlayerStrengthProjection,
)
from hockey_rmt.domain.projection_adjustment import (
    PlayerProjectionAdjustment,
)
from hockey_rmt.services.current_production import (
    build_current_season_production,
)
from hockey_rmt.services.deployment_identity import (
    resolve_deployment_identities,
)
from hockey_rmt.services.performance_rates import (
    build_skater_performance_rates,
)
from hockey_rmt.services.projection_adjustment import (
    build_player_projection_adjustments,
)
from hockey_rmt.services.trend_interpretation import (
    build_skater_trend_interpretations,
)


class CurrentStateEvidenceError(
    RuntimeError
):
    """Current-state evidence assembly failed."""


def build_deployments_by_nhl_id(
    *,
    deployment_snapshots: Sequence[
        SourceTeamDeploymentSnapshot
    ],
    nhl_players: Sequence[
        NhlPlayerIdentity
    ],
) -> dict[
    int,
    SourcePlayerDeployment,
]:
    snapshots = tuple(
        deployment_snapshots
    )

    if not snapshots:
        return {}

    registry = tuple(
        nhl_players
    )

    if not registry:
        raise CurrentStateEvidenceError(
            "Deployment snapshots were supplied "
            "without an NHL identity registry."
        )

    result = {}

    for snapshot in snapshots:
        source_by_id = {
            str(
                row.source_player_id
            ): row
            for row in snapshot.players
        }

        if len(source_by_id) != len(
            snapshot.players
        ):
            raise CurrentStateEvidenceError(
                "Deployment snapshot contained "
                "duplicate source player IDs."
            )

        resolutions = (
            resolve_deployment_identities(
                snapshot,
                registry,
            )
        )

        for resolution in resolutions:
            if (
                resolution.resolution_state
                != "resolved"
            ):
                continue

            if resolution.nhl_player_id is None:
                raise CurrentStateEvidenceError(
                    "Resolved deployment identity "
                    "was missing NHL playerId."
                )

            source_player_id = str(
                resolution.provider_player_key
            )

            try:
                deployment = source_by_id[
                    source_player_id
                ]
            except KeyError as exc:
                raise CurrentStateEvidenceError(
                    "Deployment identity referenced "
                    "an unknown source player ID."
                ) from exc

            nhl_player_id = int(
                resolution.nhl_player_id
            )

            if nhl_player_id in result:
                raise CurrentStateEvidenceError(
                    "One NHL playerId resolved from "
                    "multiple Daily Faceoff snapshots."
                )

            result[
                nhl_player_id
            ] = deployment

    return result


def build_current_state_projection_adjustments(
    *,
    player_strengths: Sequence[
        PlayerStrengthProjection
    ],
    projection_season_id: int,
    season_values: Sequence[
        HistoricalFantasyValue
    ] = (),
    performance_trends: Sequence[
        SkaterPerformanceTrend
    ] = (),
    deployment_snapshots: Sequence[
        SourceTeamDeploymentSnapshot
    ] = (),
    nhl_players: Sequence[
        NhlPlayerIdentity
    ] = (),
) -> tuple[
    PlayerProjectionAdjustment,
    ...,
]:
    current_production = (
        build_current_season_production(
            player_strengths=(
                player_strengths
            ),
            season_values=(
                season_values
            ),
            season_id=(
                projection_season_id
            ),
        )
    )

    trend_rows = tuple(
        performance_trends
    )

    if trend_rows:
        rates = (
            build_skater_performance_rates(
                trend_rows
            )
        )

        trend_interpretations = (
            build_skater_trend_interpretations(
                season_id=(
                    projection_season_id
                ),
                rates=rates,
            )
        )
    else:
        trend_interpretations = ()

    deployments_by_nhl_id = (
        build_deployments_by_nhl_id(
            deployment_snapshots=(
                deployment_snapshots
            ),
            nhl_players=(
                nhl_players
            ),
        )
    )

    return (
        build_player_projection_adjustments(
            player_strengths=(
                player_strengths
            ),
            projection_season_id=(
                projection_season_id
            ),
            current_production=(
                current_production
            ),
            trend_interpretations=(
                trend_interpretations
            ),
            deployments_by_nhl_id=(
                deployments_by_nhl_id
            ),
        )
    )
