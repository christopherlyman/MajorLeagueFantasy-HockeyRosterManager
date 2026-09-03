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
    canonical_team_by_yahoo_key = {}

    for row in team_crosswalk:
        if (
            row.source_team_key
            in canonical_team_by_yahoo_key
        ):
            raise PlayerIdentityError(
                "Duplicate Yahoo team key in "
                "team crosswalk: "
                f"{row.source_team_key!r}."
            )

        canonical_team_by_yahoo_key[
            row.source_team_key
        ] = row.canonical_team_abbr

    yahoo_by_name = defaultdict(
        list
    )

    for player in players:
        yahoo_by_name[
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

    def yahoo_team(
        player: Player,
    ) -> str:
        if not player.nhl_team_key:
            return ""

        return (
            canonical_team_by_yahoo_key.get(
                player.nhl_team_key,
                "",
            )
            or ""
        )

    def yahoo_position(
        player: Player,
    ) -> str:
        return normalize_position(
            player.primary_position
        )

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
                "Yahoo player was assigned "
                "more than once: "
                f"{provider_key!r}."
            )

        if (
            nhl_player.nhl_player_id
            in assigned_nhl_ids
        ):
            raise PlayerIdentityError(
                "NHL playerId was assigned "
                "to more than one Yahoo player: "
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
                "unknown Yahoo player key "
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
        yahoo_by_name
    ):
        yahoo_group = [
            player
            for player in yahoo_by_name[
                name_key
            ]
            if (
                player.provider_player_key
                not in resolved
            )
        ]

        if not yahoo_group:
            continue

        nhl_group = list(
            nhl_by_name.get(
                name_key,
                [],
            )
        )

        if (
            len(yahoo_group) == 1
            and len(nhl_group) == 1
        ):
            assign(
                yahoo_group[0],
                nhl_group[0],
                "unique_name",
            )

            continue

        remaining_yahoo = list(
            yahoo_group
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
                remaining_yahoo
            ):
                team = yahoo_team(
                    player
                )

                position = (
                    yahoo_position(
                        player
                    )
                )

                if (
                    not team
                    or not position
                ):
                    continue

                candidates = [
                    candidate
                    for candidate
                    in remaining_nhl.values()
                    if (
                        candidate.team_abbr
                        == team
                        and normalize_position(
                            candidate.position
                        )
                        == position
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

                remaining_yahoo.remove(
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
                remaining_yahoo
            ):
                position = (
                    yahoo_position(
                        player
                    )
                )

                if not position:
                    continue

                yahoo_same_position = [
                    other
                    for other
                    in remaining_yahoo
                    if (
                        yahoo_position(
                            other
                        )
                        == position
                    )
                ]

                nhl_same_position = [
                    candidate
                    for candidate
                    in remaining_nhl.values()
                    if (
                        normalize_position(
                            candidate.position
                        )
                        == position
                    )
                ]

                if (
                    len(
                        yahoo_same_position
                    )
                    != 1
                    or len(
                        nhl_same_position
                    )
                    != 1
                ):
                    continue

                candidate = (
                    nhl_same_position[0]
                )

                assign(
                    player,
                    candidate,
                    "position_within_name_group",
                )

                remaining_yahoo.remove(
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
                remaining_yahoo
            ):
                team = yahoo_team(
                    player
                )

                if not team:
                    continue

                yahoo_same_team = [
                    other
                    for other
                    in remaining_yahoo
                    if (
                        yahoo_team(
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
                        candidate.team_abbr
                        == team
                    )
                ]

                if (
                    len(
                        yahoo_same_team
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

                remaining_yahoo.remove(
                    player
                )

                remaining_nhl.pop(
                    candidate.nhl_player_id
                )

                changed = True

        # Final safe elimination.
        if (
            len(remaining_yahoo) == 1
            and len(remaining_nhl) == 1
        ):
            player = (
                remaining_yahoo[0]
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

            remaining_yahoo.clear()
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
            "did not match Yahoo player count."
        )

    return tuple(result)
