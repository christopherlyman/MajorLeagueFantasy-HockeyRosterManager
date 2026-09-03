from __future__ import annotations

from collections.abc import Sequence

from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    PlayerIdentityResolution,
)
from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.player_value import (
    HISTORICAL_VALUE_AVAILABLE,
    IDENTITY_UNRESOLVED,
    RESOLVED_NO_HISTORY,
    PlayerHistoricalBaseline,
)


class PlayerValueBaselineError(RuntimeError):
    """Yahoo historical baseline construction failed."""


def build_player_historical_baselines(
    *,
    players: Sequence[Player],
    resolutions: Sequence[
        PlayerIdentityResolution
    ],
    historical_values: Sequence[
        HistoricalFantasyValue
    ],
) -> tuple[
    PlayerHistoricalBaseline,
    ...,
]:
    player_by_key = {}

    for player in players:
        key = player.provider_player_key

        if key in player_by_key:
            raise PlayerValueBaselineError(
                "Duplicate Yahoo provider player key: "
                f"{key!r}."
            )

        player_by_key[key] = player

    resolution_by_key = {}

    for resolution in resolutions:
        key = (
            resolution.provider_player_key
        )

        if key in resolution_by_key:
            raise PlayerValueBaselineError(
                "Duplicate identity resolution for "
                f"Yahoo player {key!r}."
            )

        if key not in player_by_key:
            raise PlayerValueBaselineError(
                "Identity resolution referenced "
                "unknown Yahoo player "
                f"{key!r}."
            )

        resolution_by_key[
            key
        ] = resolution

    missing_resolution_keys = (
        set(player_by_key)
        - set(resolution_by_key)
    )

    if missing_resolution_keys:
        raise PlayerValueBaselineError(
            "Yahoo players were missing identity "
            "resolution rows: "
            f"{len(missing_resolution_keys)}."
        )

    value_by_nhl_id = {}

    for value in historical_values:
        player_id = value.nhl_player_id

        if player_id in value_by_nhl_id:
            raise PlayerValueBaselineError(
                "Duplicate historical value for "
                f"NHL playerId {player_id}."
            )

        value_by_nhl_id[
            player_id
        ] = value

    result = []

    for player in players:
        key = player.provider_player_key

        identity = resolution_by_key[
            key
        ]

        historical_value = None

        if (
            identity.resolution_state
            == "resolved"
        ):
            if (
                identity.nhl_player_id
                is None
            ):
                raise PlayerValueBaselineError(
                    "Resolved identity did not contain "
                    "an NHL playerId for Yahoo player "
                    f"{key!r}."
                )

            historical_value = (
                value_by_nhl_id.get(
                    identity.nhl_player_id
                )
            )

            if historical_value is None:
                coverage_state = (
                    RESOLVED_NO_HISTORY
                )
            else:
                coverage_state = (
                    HISTORICAL_VALUE_AVAILABLE
                )

                if (
                    historical_value.nhl_player_id
                    != identity.nhl_player_id
                ):
                    raise PlayerValueBaselineError(
                        "Historical value NHL playerId "
                        "did not match resolved identity."
                    )

        elif (
            identity.resolution_state
            == "unresolved"
        ):
            if (
                identity.nhl_player_id
                is not None
            ):
                raise PlayerValueBaselineError(
                    "Unresolved identity unexpectedly "
                    "contained an NHL playerId for "
                    f"Yahoo player {key!r}."
                )

            coverage_state = (
                IDENTITY_UNRESOLVED
            )

        else:
            raise PlayerValueBaselineError(
                "Unknown identity resolution state "
                f"{identity.resolution_state!r}."
            )

        result.append(
            PlayerHistoricalBaseline(
                player=player,
                identity=identity,
                coverage_state=(
                    coverage_state
                ),
                historical_value=(
                    historical_value
                ),
            )
        )

    return tuple(result)
