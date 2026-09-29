from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence

from hockey_rmt.domain.hockey_team import (
    TeamIdentityCrosswalk,
)
from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    NhlPlayerIdentity,
    PlayerIdentityResolution,
)


class PlayerIdentityError(RuntimeError):
    """Cross-provider player identity resolution failed."""


def normalize_player_name(
    value: str,
) -> str:
    decomposed = unicodedata.normalize(
        "NFKD",
        value,
    )

    without_marks = "".join(
        char
        for char in decomposed
        if not unicodedata.combining(
            char
        )
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        without_marks.lower(),
    )


def normalize_position(
    value: str | None,
) -> str:
    position = str(
        value or ""
    ).upper()

    aliases = {
        "LW": "L",
        "RW": "R",
    }

    return aliases.get(
        position,
        position,
    )


def resolve_player_identities(
    players: Sequence[Player],
    nhl_players: Sequence[NhlPlayerIdentity],
    team_crosswalk: Sequence[
        TeamIdentityCrosswalk
    ],
    explicit_nhl_player_ids: Mapping[
        str,
        int,
    ] | None = None,
) -> tuple[
    PlayerIdentityResolution,
    ...,
]:
    canonical_team_by_source_key = {}

    for row in team_crosswalk:
        source_key = (
            row.source_provider,
            row.source_team_key,
        )

        if (
            source_key
            in canonical_team_by_source_key
        ):
            raise PlayerIdentityError(
                "Duplicate provider team key in "
                "team crosswalk: "
                f"{source_key!r}."
            )

        canonical_team_by_source_key[
            source_key
        ] = row.canonical_team_abbr

    provider_by_name = defaultdict(
        list
    )

    for player in players:
        provider_by_name[
            normalize_player_name(
                player.full_name
            )
        ].append(player)

    nhl_by_name = defaultdict(
        list
    )

    seen_nhl_ids = set()

    for nhl_player in nhl_players:
        if (
            nhl_player.nhl_player_id
            in seen_nhl_ids
        ):
            raise PlayerIdentityError(
                "Duplicate NHL playerId "
                f"{nhl_player.nhl_player_id!r} "
                "in identity registry."
            )

        seen_nhl_ids.add(
            nhl_player.nhl_player_id
        )

        nhl_by_name[
            normalize_player_name(
                nhl_player.full_name
            )
        ].append(
            nhl_player
        )

    resolved: dict[
        str,
        PlayerIdentityResolution,
    ] = {}

    assigned_nhl_ids = set()

    nhl_by_id = {
        player.nhl_player_id: player
        for player in nhl_players
    }

    explicit_nhl_player_ids = dict(
        explicit_nhl_player_ids or {}
    )

    def provider_team(
        player: Player,
    ) -> str:
        if player.nhl_team_key:
            canonical = (
                canonical_team_by_source_key.get(
                    (
                        player.provider,
                        player.nhl_team_key,
                    )
                )
            )

            if canonical:
                return str(
                    canonical
                ).strip().upper()

        return str(
            player.nhl_team_abbr
            or ""
        ).strip().upper()

    def provider_positions(
        player: Player,
    ) -> frozenset[str]:
        identity_positions = {
            "C",
            "L",
            "R",
            "D",
            "G",
        }

        primary = normalize_position(
            player.primary_position
        )

        # Preserve the historical single-primary-position
        # behavior whenever the provider gives us a normal
        # NHL position.
        if primary in identity_positions:
            return frozenset(
                (primary,)
            )

        result = set()

        for raw_position in (
            player.eligible_positions
        ):
            normalized = normalize_position(
                raw_position
            )

            if (
                normalized
                in identity_positions
            ):
                result.add(normalized)

        return frozenset(result)

    def assign(
        player: Player,
        nhl_player: NhlPlayerIdentity,
        method: str,
    ) -> None:
        provider_key = (
            player.provider_player_key
        )

        if provider_key in resolved:
            raise PlayerIdentityError(
                "Provider player was assigned "
                "more than once: "
                f"{provider_key!r}."
            )

        if (
            nhl_player.nhl_player_id
            in assigned_nhl_ids
        ):
            raise PlayerIdentityError(
                "NHL playerId was assigned "
                "to more than one provider player: "
                f"{nhl_player.nhl_player_id!r}."
            )

        assigned_nhl_ids.add(
            nhl_player.nhl_player_id
        )

        resolved[
            provider_key
        ] = PlayerIdentityResolution(
            provider_player_key=(
                provider_key
            ),
            resolution_state="resolved",
            resolution_method=method,
            nhl_player_id=(
                nhl_player.nhl_player_id
            ),
            nhl_full_name=(
                nhl_player.full_name
            ),
            nhl_position=(
                nhl_player.position
            ),
            nhl_team_abbr=(
                nhl_player.team_abbr
            ),
        )

    player_by_key = {
        player.provider_player_key: player
        for player in players
    }

    for (
        provider_player_key,
        nhl_player_id,
    ) in sorted(
        explicit_nhl_player_ids.items()
    ):
        player = player_by_key.get(
            provider_player_key
        )

        if player is None:
            raise PlayerIdentityError(
                "Explicit identity override referenced "
                "unknown provider player key "
                f"{provider_player_key!r}."
            )

        nhl_player = nhl_by_id.get(
            int(nhl_player_id)
        )

        if nhl_player is None:
            raise PlayerIdentityError(
                "Explicit identity override referenced "
                "unknown NHL playerId "
                f"{nhl_player_id!r}."
            )

        assign(
            player,
            nhl_player,
            "explicit_override",
        )

    for name_key in sorted(
        provider_by_name
    ):
        provider_group = [
            player
            for player in provider_by_name[
                name_key
            ]
            if (
                player.provider_player_key
                not in resolved
            )
        ]

        if not provider_group:
            continue

        nhl_group = list(
            nhl_by_name.get(
                name_key,
                [],
            )
        )

        if (
            len(provider_group) == 1
            and len(nhl_group) == 1
        ):
            assign(
                provider_group[0],
                nhl_group[0],
                "unique_name",
            )

            continue

        remaining_provider = list(
            provider_group
        )

        remaining_nhl = {
            player.nhl_player_id:
                player
            for player in nhl_group
        }

        # Pass 1:
        # canonical NHL team + position.
        changed = True

        while changed:
            changed = False

            for player in list(
                remaining_provider
            ):
                team = provider_team(
                    player
                )

                positions = (
                    provider_positions(
                        player
                    )
                )

                if (
                    not team
                    or not positions
                ):
                    continue

                candidates = [
                    candidate
                    for candidate
                    in remaining_nhl.values()
                    if (
                        str(
                            candidate.team_abbr
                            or ""
                        ).strip().upper()
                        == team
                        and normalize_position(
                            candidate.position
                        )
                        in positions
                    )
                ]

                if (
                    len(candidates)
                    != 1
                ):
                    continue

                candidate = (
                    candidates[0]
                )

                assign(
                    player,
                    candidate,
                    "team_position",
                )

                remaining_provider.remove(
                    player
                )

                remaining_nhl.pop(
                    candidate.nhl_player_id
                )

                changed = True

        # Pass 2:
        # position within this exact-name
        # group, only when one-to-one.
        changed = True

        while changed:
            changed = False

            for player in list(
                remaining_provider
            ):
                positions = (
                    provider_positions(
                        player
                    )
                )

                if not positions:
                    continue

                nhl_same_position = [
                    candidate
                    for candidate
                    in remaining_nhl.values()
                    if (
                        normalize_position(
                            candidate.position
                        )
                        in positions
                    )
                ]

                if (
                    len(
                        nhl_same_position
                    )
                    != 1
                ):
                    continue

                candidate = (
                    nhl_same_position[0]
                )

                candidate_position = (
                    normalize_position(
                        candidate.position
                    )
                )

                provider_same_position = [
                    other
                    for other
                    in remaining_provider
                    if (
                        candidate_position
                        in provider_positions(
                            other
                        )
                    )
                ]

                if (
                    len(
                        provider_same_position
                    )
                    != 1
                ):
                    continue

                assign(
                    player,
                    candidate,
                    "position_within_name_group",
                )

                remaining_provider.remove(
                    player
                )

                remaining_nhl.pop(
                    candidate.nhl_player_id
                )

                changed = True

        # Pass 3:
        # team within this exact-name group,
        # again only when one-to-one.
        changed = True

        while changed:
            changed = False

            for player in list(
                remaining_provider
            ):
                team = provider_team(
                    player
                )

                if not team:
                    continue

                provider_same_team = [
                    other
                    for other
                    in remaining_provider
                    if (
                        provider_team(
                            other
                        )
                        == team
                    )
                ]

                nhl_same_team = [
                    candidate
                    for candidate
                    in remaining_nhl.values()
                    if (
                        str(
                            candidate.team_abbr
                            or ""
                        ).strip().upper()
                        == team
                    )
                ]

                if (
                    len(
                        provider_same_team
                    )
                    != 1
                    or len(
                        nhl_same_team
                    )
                    != 1
                ):
                    continue

                candidate = (
                    nhl_same_team[0]
                )

                assign(
                    player,
                    candidate,
                    "team_within_name_group",
                )

                remaining_provider.remove(
                    player
                )

                remaining_nhl.pop(
                    candidate.nhl_player_id
                )

                changed = True

        # Final safe elimination.
        if (
            len(remaining_provider) == 1
            and len(remaining_nhl) == 1
        ):
            player = (
                remaining_provider[0]
            )

            candidate = next(
                iter(
                    remaining_nhl.values()
                )
            )

            assign(
                player,
                candidate,
                "one_to_one_elimination",
            )

            remaining_provider.clear()
            remaining_nhl.clear()

    result = []

    for player in players:
        resolution = resolved.get(
            player.provider_player_key
        )

        if resolution is None:
            resolution = (
                PlayerIdentityResolution(
                    provider_player_key=(
                        player.provider_player_key
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

        result.append(
            resolution
        )

    if len(result) != len(players):
        raise PlayerIdentityError(
            "Player identity result count "
            "did not match provider player count."
        )

    return tuple(result)
