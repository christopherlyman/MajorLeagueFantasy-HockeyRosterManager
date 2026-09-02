from __future__ import annotations

from typing import Any, Mapping

from hockey_rmt.domain.hockey_team import (
    HockeyTeam,
)
from hockey_rmt.providers.nhl.client import (
    NhlClient,
)


class NhlTeamError(RuntimeError):
    """NHL team identity parsing failed."""


def parse_standings_teams(
    payload: Mapping[str, Any],
) -> tuple[HockeyTeam, ...]:
    standings = payload.get(
        "standings"
    )

    if not isinstance(standings, list):
        raise NhlTeamError(
            "NHL standings payload did not "
            "contain a standings list."
        )

    teams: dict[str, HockeyTeam] = {}

    for row in standings:
        if not isinstance(row, Mapping):
            raise NhlTeamError(
                "NHL standings row was not "
                "an object."
            )

        name = (
            row.get("teamName")
            or {}
        ).get("default")

        abbr = (
            row.get("teamAbbrev")
            or {}
        ).get("default")

        if not name or not abbr:
            raise NhlTeamError(
                "NHL standings row did not "
                "contain team name/abbreviation."
            )

        abbreviation = str(abbr)

        team = HockeyTeam(
            provider="nhl",
            provider_team_key=None,
            name=str(name),
            abbreviation=abbreviation,
        )

        existing = teams.get(
            abbreviation
        )

        if (
            existing is not None
            and existing != team
        ):
            raise NhlTeamError(
                "Duplicate NHL team abbreviation "
                f"{abbreviation!r}."
            )

        teams[abbreviation] = team

    return tuple(
        teams[key]
        for key in sorted(teams)
    )


def fetch_current_teams(
    client: NhlClient,
) -> tuple[HockeyTeam, ...]:
    payload = client.get_json(
        "/standings/now"
    )

    return parse_standings_teams(
        payload
    )
