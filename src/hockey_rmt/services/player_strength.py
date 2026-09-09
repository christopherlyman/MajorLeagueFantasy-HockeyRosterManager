from __future__ import annotations

import math
from collections.abc import Sequence

from hockey_rmt.domain.goalie_projection import (
    PreseasonGoalieProjection,
)
from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    PlayerIdentityResolution,
)
from hockey_rmt.domain.player_strength import (
    SOURCE_ESTABLISHED_SKATER,
    SOURCE_GOALIE_QUALITY,
    SOURCE_LONG_ABSENCE_SKATER,
    SOURCE_ROOKIE_SKATER,
    STRENGTH_AVAILABLE,
    STRENGTH_IDENTITY_UNRESOLVED,
    STRENGTH_NO_PROJECTION,
    PlayerStrengthProjection,
)
from hockey_rmt.domain.returner_projection import (
    LongAbsenceSkaterProjection,
)
from hockey_rmt.domain.rookie_projection import (
    RookieSkaterProjection,
)
from hockey_rmt.domain.skater_projection import (
    CalibratedSkaterProjection,
)


class PlayerStrengthError(RuntimeError):
    """Canonical player-strength join failed."""


def _finite_number(
    *,
    value: float,
    label: str,
) -> float:
    numeric = float(
        value
    )

    if not math.isfinite(
        numeric
    ):
        raise PlayerStrengthError(
            f"{label} must be finite."
        )

    return numeric


def _finite_nonnegative(
    *,
    value: float,
    label: str,
) -> float:
    parsed = float(
        value
    )

    if (
        not math.isfinite(parsed)
        or parsed < 0
    ):
        raise PlayerStrengthError(
            f"{label} must be finite and "
            "nonnegative."
        )

    return parsed


def _unique_by_nhl_id(
    rows: Sequence[
        CalibratedSkaterProjection
        | RookieSkaterProjection
        | LongAbsenceSkaterProjection
    ],
    *,
    label: str,
) -> dict[
    int,
    CalibratedSkaterProjection
    | RookieSkaterProjection
    | LongAbsenceSkaterProjection,
]:
    result = {}

    for row in rows:
        player_id = int(
            row.nhl_player_id
        )

        if player_id in result:
            raise PlayerStrengthError(
                f"{label} contained duplicate "
                f"NHL playerId {player_id}."
            )

        _finite_nonnegative(
            value=(
                row
                .projected_fantasy_points_per_game
            ),
            label=(
                f"{label} projected FPPG"
            ),
        )

        result[
            player_id
        ] = row

    return result


def build_player_strength_projections(
    *,
    projection_season_id: int,
    players: Sequence[Player],
    identity_resolutions: Sequence[
        PlayerIdentityResolution
    ],
    established_skater_projections: Sequence[
        CalibratedSkaterProjection
    ],
    rookie_skater_projections: Sequence[
        RookieSkaterProjection
    ],
    long_absence_skater_projections: Sequence[
        LongAbsenceSkaterProjection
    ],
    goalie_projections: Sequence[
        PreseasonGoalieProjection
    ],
) -> tuple[
    PlayerStrengthProjection,
    ...,
]:
    season_id = int(
        projection_season_id
    )

    if season_id <= 0:
        raise ValueError(
            "Projection season ID must "
            "be positive."
        )

    player_by_key: dict[
        str,
        Player,
    ] = {}

    for player in players:
        key = (
            player.provider_player_key
        )

        if key in player_by_key:
            raise PlayerStrengthError(
                "Duplicate Yahoo player key "
                f"{key!r}."
            )

        player_by_key[
            key
        ] = player

    identity_by_key: dict[
        str,
        PlayerIdentityResolution,
    ] = {}

    for identity in identity_resolutions:
        key = (
            identity.provider_player_key
        )

        if key in identity_by_key:
            raise PlayerStrengthError(
                "Duplicate identity resolution "
                f"for Yahoo player {key!r}."
            )

        if key not in player_by_key:
            raise PlayerStrengthError(
                "Identity resolution referenced "
                "an unknown Yahoo player "
                f"{key!r}."
            )

        identity_by_key[
            key
        ] = identity

    if (
        set(identity_by_key)
        != set(player_by_key)
    ):
        raise PlayerStrengthError(
            "Identity-resolution coverage did "
            "not exactly match the Yahoo "
            "player universe."
        )

    established_by_id = (
        _unique_by_nhl_id(
            established_skater_projections,
            label=(
                "Established-skater projections"
            ),
        )
    )

    rookie_by_id = (
        _unique_by_nhl_id(
            rookie_skater_projections,
            label=(
                "Rookie-skater projections"
            ),
        )
    )

    returner_by_id = (
        _unique_by_nhl_id(
            long_absence_skater_projections,
            label=(
                "Long-absence skater projections"
            ),
        )
    )

    established_ids = set(
        established_by_id
    )
    rookie_ids = set(
        rookie_by_id
    )
    returner_ids = set(
        returner_by_id
    )

    overlaps = (
        (
            established_ids
            & rookie_ids
        )
        | (
            established_ids
            & returner_ids
        )
        | (
            rookie_ids
            & returner_ids
        )
    )

    if overlaps:
        raise PlayerStrengthError(
            "Skater projection families "
            "overlapped for NHL playerIds: "
            f"{sorted(overlaps)!r}."
        )

    goalie_by_key: dict[
        str,
        PreseasonGoalieProjection,
    ] = {}

    for row in goalie_projections:
        key = (
            row.provider_player_key
        )

        if key in goalie_by_key:
            raise PlayerStrengthError(
                "Goalie projections contained "
                "duplicate Yahoo player key "
                f"{key!r}."
            )

        if key not in player_by_key:
            raise PlayerStrengthError(
                "Goalie projection referenced "
                "an unknown Yahoo player "
                f"{key!r}."
            )

        player = player_by_key[
            key
        ]

        if (
            player.position_type
            .strip()
            .upper()
            != "G"
        ):
            raise PlayerStrengthError(
                "Goalie projection referenced "
                "a non-goalie Yahoo player "
                f"{key!r}."
            )

        if (
            row.projected_fantasy_points_per_game
            is not None
        ):
            _finite_number(
                value=(
                    row
                    .projected_fantasy_points_per_game
                ),
                label="Goalie projected FPPG",
            )

        goalie_by_key[
            key
        ] = row

    yahoo_goalie_keys = {
        player.provider_player_key
        for player in players
        if (
            player.position_type
            .strip()
            .upper()
            == "G"
        )
    }

    if (
        set(goalie_by_key)
        != yahoo_goalie_keys
    ):
        missing = sorted(
            yahoo_goalie_keys
            - set(goalie_by_key)
        )

        unexpected = sorted(
            set(goalie_by_key)
            - yahoo_goalie_keys
        )

        raise PlayerStrengthError(
            "Goalie projection coverage did not "
            "exactly match Yahoo goalies. "
            f"missing={missing!r} "
            f"unexpected={unexpected!r}"
        )

    result: list[
        PlayerStrengthProjection
    ] = []

    for player in players:
        key = (
            player.provider_player_key
        )

        identity = identity_by_key[
            key
        ]

        is_goalie = (
            player.position_type
            .strip()
            .upper()
            == "G"
        )

        if is_goalie:
            goalie = goalie_by_key[
                key
            ]

            if (
                identity.resolution_state
                == "unresolved"
            ):
                if (
                    identity.nhl_player_id
                    is not None
                ):
                    raise PlayerStrengthError(
                        "Unresolved goalie identity "
                        "contained an NHL playerId."
                    )

                if (
                    goalie.nhl_player_id
                    is not None
                    or goalie
                    .projected_fantasy_points_per_game
                    is not None
                ):
                    raise PlayerStrengthError(
                        "Unresolved goalie received "
                        "resolved projection data."
                    )

                result.append(
                    PlayerStrengthProjection(
                        provider_player_key=key,
                        full_name=(
                            player.full_name
                        ),
                        projection_season_id=(
                            season_id
                        ),
                        player_type=(
                            player.position_type
                        ),
                        nhl_player_id=None,
                        strength_state=(
                            STRENGTH_IDENTITY_UNRESOLVED
                        ),
                        projection_source=None,
                        source_state=None,
                        projected_fantasy_points_per_game=None,
                    )
                )

                continue

            if (
                identity.resolution_state
                != "resolved"
                or identity.nhl_player_id
                is None
            ):
                raise PlayerStrengthError(
                    "Unexpected goalie identity "
                    "resolution state."
                )

            if (
                goalie.nhl_player_id
                != identity.nhl_player_id
            ):
                raise PlayerStrengthError(
                    "Goalie projection NHL playerId "
                    "did not match canonical "
                    "identity."
                )

            if (
                goalie
                .projected_fantasy_points_per_game
                is None
            ):
                raise PlayerStrengthError(
                    "Resolved goalie projection "
                    "did not contain projected "
                    "FPPG."
                )

            result.append(
                PlayerStrengthProjection(
                    provider_player_key=key,
                    full_name=(
                        player.full_name
                    ),
                    projection_season_id=(
                        season_id
                    ),
                    player_type=(
                        player.position_type
                    ),
                    nhl_player_id=(
                        identity.nhl_player_id
                    ),
                    strength_state=(
                        STRENGTH_AVAILABLE
                    ),
                    projection_source=(
                        SOURCE_GOALIE_QUALITY
                    ),
                    source_state=(
                        goalie.quality_state
                    ),
                    projected_fantasy_points_per_game=(
                        goalie
                        .projected_fantasy_points_per_game
                    ),
                )
            )

            continue

        if (
            identity.resolution_state
            == "unresolved"
        ):
            if (
                identity.nhl_player_id
                is not None
            ):
                raise PlayerStrengthError(
                    "Unresolved skater identity "
                    "contained an NHL playerId."
                )

            result.append(
                PlayerStrengthProjection(
                    provider_player_key=key,
                    full_name=(
                        player.full_name
                    ),
                    projection_season_id=(
                        season_id
                    ),
                    player_type=(
                        player.position_type
                    ),
                    nhl_player_id=None,
                    strength_state=(
                        STRENGTH_IDENTITY_UNRESOLVED
                    ),
                    projection_source=None,
                    source_state=None,
                    projected_fantasy_points_per_game=None,
                )
            )

            continue

        if (
            identity.resolution_state
            != "resolved"
            or identity.nhl_player_id
            is None
        ):
            raise PlayerStrengthError(
                "Unexpected skater identity "
                "resolution state."
            )

        player_id = int(
            identity.nhl_player_id
        )

        projection = None
        source = None
        source_state = None

        if player_id in established_by_id:
            projection = (
                established_by_id[
                    player_id
                ]
            )
            source = (
                SOURCE_ESTABLISHED_SKATER
            )

        elif player_id in rookie_by_id:
            projection = (
                rookie_by_id[
                    player_id
                ]
            )
            source = (
                SOURCE_ROOKIE_SKATER
            )

        elif player_id in returner_by_id:
            projection = (
                returner_by_id[
                    player_id
                ]
            )
            source = (
                SOURCE_LONG_ABSENCE_SKATER
            )
            source_state = (
                projection.projection_state
            )

        if projection is None:
            result.append(
                PlayerStrengthProjection(
                    provider_player_key=key,
                    full_name=(
                        player.full_name
                    ),
                    projection_season_id=(
                        season_id
                    ),
                    player_type=(
                        player.position_type
                    ),
                    nhl_player_id=(
                        player_id
                    ),
                    strength_state=(
                        STRENGTH_NO_PROJECTION
                    ),
                    projection_source=None,
                    source_state=None,
                    projected_fantasy_points_per_game=None,
                )
            )

            continue

        result.append(
            PlayerStrengthProjection(
                provider_player_key=key,
                full_name=(
                    player.full_name
                ),
                projection_season_id=(
                    season_id
                ),
                player_type=(
                    player.position_type
                ),
                nhl_player_id=(
                    player_id
                ),
                strength_state=(
                    STRENGTH_AVAILABLE
                ),
                projection_source=(
                    source
                ),
                source_state=(
                    source_state
                ),
                projected_fantasy_points_per_game=(
                    projection
                    .projected_fantasy_points_per_game
                ),
            )
        )

    return tuple(
        result
    )
