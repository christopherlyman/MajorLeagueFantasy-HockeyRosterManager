from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from hockey_rmt.domain.deployment import (
    SourceTeamDeploymentSnapshot,
)
from hockey_rmt.domain.player_identity import (
    NhlPlayerIdentity,
    PlayerIdentityResolution,
)
from hockey_rmt.services.player_identity import (
    normalize_player_name,
)


RESOLUTION_METHOD_EXACT_NAME_TEAM = (
    "exact_name_team"
)

RESOLUTION_METHOD_EXPLICIT_OVERRIDE = (
    "explicit_override"
)


class DeploymentIdentityError(
    RuntimeError
):
    """Source deployment identity resolution failed."""


def resolve_deployment_identities(
    snapshot: SourceTeamDeploymentSnapshot,
    nhl_players: Sequence[
        NhlPlayerIdentity
    ],
    *,
    explicit_nhl_player_ids: Mapping[
        str,
        int,
    ] | None = None,
) -> tuple[
    PlayerIdentityResolution,
    ...,
]:
    source_team = str(
        snapshot.team_abbreviation
    ).strip().upper()

    if not source_team:
        raise DeploymentIdentityError(
            "Deployment snapshot team "
            "abbreviation was empty."
        )

    source_ids = [
        str(
            player.source_player_id
        )
        for player in snapshot.players
    ]

    if (
        len(source_ids)
        != len(
            set(
                source_ids
            )
        )
    ):
        raise DeploymentIdentityError(
            "Deployment snapshot contained "
            "duplicate source player IDs."
        )

    source_by_id = {
        str(
            player.source_player_id
        ): player
        for player in snapshot.players
    }

    nhl_by_name: dict[
        str,
        list[
            NhlPlayerIdentity
        ],
    ] = defaultdict(
        list
    )

    nhl_by_id: dict[
        int,
        NhlPlayerIdentity,
    ] = {}

    seen_nhl_ids = set()

    for player in nhl_players:
        nhl_player_id = int(
            player.nhl_player_id
        )

        if nhl_player_id in seen_nhl_ids:
            raise DeploymentIdentityError(
                "NHL identity registry contained "
                "duplicate playerId "
                f"{nhl_player_id}."
            )

        seen_nhl_ids.add(
            nhl_player_id
        )

        nhl_by_id[
            nhl_player_id
        ] = player

        name_key = normalize_player_name(
            player.full_name
        )

        if not name_key:
            raise DeploymentIdentityError(
                "NHL identity registry contained "
                "an empty normalized player name "
                f"for playerId {nhl_player_id}."
            )

        nhl_by_name[
            name_key
        ].append(
            player
        )

    overrides = {
        str(
            source_player_id
        ): int(
            nhl_player_id
        )
        for (
            source_player_id,
            nhl_player_id,
        ) in (
            explicit_nhl_player_ids
            or {}
        ).items()
    }

    for (
        source_player_id,
        nhl_player_id,
    ) in sorted(
        overrides.items()
    ):
        if (
            source_player_id
            not in source_by_id
        ):
            raise DeploymentIdentityError(
                "Explicit deployment identity "
                "override referenced unknown "
                "source playerId "
                f"{source_player_id!r}."
            )

        if nhl_player_id not in nhl_by_id:
            raise DeploymentIdentityError(
                "Explicit deployment identity "
                "override referenced unknown "
                "NHL playerId "
                f"{nhl_player_id}."
            )

    result = []
    assigned_nhl_ids = set()

    for source_player in snapshot.players:
        source_player_id = str(
            source_player.source_player_id
        )

        player_team = str(
            source_player.team_abbreviation
        ).strip().upper()

        if player_team != source_team:
            raise DeploymentIdentityError(
                "Source player deployment team "
                "did not match snapshot team: "
                f"{source_player_id!r}, "
                f"{player_team!r}, "
                f"{source_team!r}."
            )

        name_key = normalize_player_name(
            source_player.full_name
        )

        if not name_key:
            raise DeploymentIdentityError(
                "Source deployment contained "
                "an empty normalized player name "
                f"for source player "
                f"{source_player_id!r}."
            )

        explicit_nhl_id = (
            overrides.get(
                source_player_id
            )
        )

        if explicit_nhl_id is not None:
            candidate = nhl_by_id[
                explicit_nhl_id
            ]

            candidate_team = str(
                candidate.team_abbr
                or ""
            ).strip().upper()

            if candidate_team != source_team:
                raise DeploymentIdentityError(
                    "Explicit deployment identity "
                    "override team did not match "
                    "the source deployment team: "
                    f"source playerId "
                    f"{source_player_id!r}, "
                    f"NHL playerId "
                    f"{explicit_nhl_id}, "
                    f"source team "
                    f"{source_team!r}, "
                    f"NHL team "
                    f"{candidate_team!r}."
                )

            method = (
                RESOLUTION_METHOD_EXPLICIT_OVERRIDE
            )

        else:
            name_candidates = (
                nhl_by_name.get(
                    name_key,
                    [],
                )
            )

            team_candidates = [
                candidate
                for candidate in name_candidates
                if (
                    str(
                        candidate.team_abbr
                        or ""
                    )
                    .strip()
                    .upper()
                    == source_team
                )
            ]

            if len(team_candidates) == 1:
                candidate = (
                    team_candidates[0]
                )

                method = (
                    RESOLUTION_METHOD_EXACT_NAME_TEAM
                )

            else:
                result.append(
                    PlayerIdentityResolution(
                        provider_player_key=(
                            source_player_id
                        ),
                        resolution_state=(
                            "unresolved"
                        ),
                        resolution_method=None,
                        nhl_player_id=None,
                        nhl_full_name=None,
                        nhl_position=None,
                        nhl_team_abbr=None,
                    )
                )

                continue

        if (
            candidate.nhl_player_id
            in assigned_nhl_ids
        ):
            raise DeploymentIdentityError(
                "One NHL playerId resolved to "
                "multiple source deployment "
                "players: "
                f"{candidate.nhl_player_id}."
            )

        assigned_nhl_ids.add(
            candidate.nhl_player_id
        )

        result.append(
            PlayerIdentityResolution(
                provider_player_key=(
                    source_player_id
                ),
                resolution_state=(
                    "resolved"
                ),
                resolution_method=(
                    method
                ),
                nhl_player_id=(
                    candidate.nhl_player_id
                ),
                nhl_full_name=(
                    candidate.full_name
                ),
                nhl_position=(
                    candidate.position
                ),
                nhl_team_abbr=(
                    candidate.team_abbr
                ),
            )
        )

    if (
        len(result)
        != len(
            snapshot.players
        )
    ):
        raise DeploymentIdentityError(
            "Deployment identity result count "
            "did not match source-player count."
        )

    return tuple(
        result
    )
