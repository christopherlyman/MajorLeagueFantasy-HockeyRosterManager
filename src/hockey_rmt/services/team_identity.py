from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from hockey_rmt.domain.hockey_team import (
    HockeyTeam,
    TeamIdentityCrosswalk,
)
from hockey_rmt.domain.player import Player


class TeamIdentityError(RuntimeError):
    """Cross-provider team identity could not be resolved."""


def normalize_team_name(
    value: str,
) -> str:
    decomposed = unicodedata.normalize(
        "NFKD",
        value,
    )

    without_marks = "".join(
        char
        for char in decomposed
        if not unicodedata.combining(char)
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        without_marks.lower(),
    )


def build_yahoo_nhl_crosswalk(
    players: Sequence[Player],
    nhl_teams: Sequence[HockeyTeam],
) -> tuple[TeamIdentityCrosswalk, ...]:
    yahoo_teams: dict[
        str,
        tuple[str, str, str],
    ] = {}

    for player in players:
        if (
            not player.nhl_team_key
            or not player.nhl_team_name
            or not player.nhl_team_abbr
        ):
            continue

        row = (
            player.nhl_team_key,
            player.nhl_team_name,
            player.nhl_team_abbr,
        )

        existing = yahoo_teams.get(
            player.nhl_team_key
        )

        if (
            existing is not None
            and existing != row
        ):
            raise TeamIdentityError(
                "Conflicting Yahoo team identity "
                f"for {player.nhl_team_key!r}."
            )

        yahoo_teams[
            player.nhl_team_key
        ] = row

    nhl_by_name: dict[
        str,
        HockeyTeam,
    ] = {}

    for team in nhl_teams:
        key = normalize_team_name(
            team.name
        )

        if key in nhl_by_name:
            raise TeamIdentityError(
                "Normalized NHL team name "
                f"{key!r} was not unique."
            )

        nhl_by_name[key] = team

    result: list[
        TeamIdentityCrosswalk
    ] = []

    for (
        yahoo_key,
        yahoo_name,
        yahoo_abbr,
    ) in sorted(
        yahoo_teams.values(),
        key=lambda row: row[1],
    ):
        normalized = normalize_team_name(
            yahoo_name
        )

        nhl_team = nhl_by_name.get(
            normalized
        )

        if nhl_team is None:
            raise TeamIdentityError(
                "No NHL team matched Yahoo team "
                f"{yahoo_name!r} "
                f"({yahoo_abbr!r}, "
                f"{yahoo_key!r})."
            )

        result.append(
            TeamIdentityCrosswalk(
                source_provider="yahoo",
                source_team_key=yahoo_key,
                source_team_abbr=yahoo_abbr,
                canonical_team_name=(
                    nhl_team.name
                ),
                canonical_team_abbr=(
                    nhl_team.abbreviation
                ),
            )
        )

    return tuple(result)
