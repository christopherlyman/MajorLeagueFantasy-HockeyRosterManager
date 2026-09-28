from __future__ import annotations

from typing import Any, Mapping, Sequence

from hockey_rmt.domain.team import FantasyTeam
from hockey_rmt.providers.fleaflicker.client import (
    FleaflickerClient,
)


class FleaflickerTeamsError(RuntimeError):
    """Fleaflicker fantasy-team acquisition failed."""


def _optional_int(
    value: object,
) -> int | None:
    if value is None or value == "":
        return None

    return int(value)


def parse_teams(
    payload: Mapping[str, Any],
    *,
    managed_team_id: str,
) -> tuple[FantasyTeam, ...]:
    managed_id = managed_team_id.strip()

    if not managed_id:
        raise ValueError(
            "Managed Fleaflicker team ID must not be empty."
        )

    divisions = payload.get("divisions")

    if not isinstance(divisions, Sequence) or isinstance(
        divisions,
        (str, bytes),
    ):
        raise FleaflickerTeamsError(
            "Fleaflicker standings payload has no "
            "valid divisions collection."
        )

    teams: list[FantasyTeam] = []
    seen_team_ids: set[str] = set()
    managed_matches = 0

    for division in divisions:
        if not isinstance(division, Mapping):
            raise FleaflickerTeamsError(
                "Fleaflicker division was not an object."
            )

        raw_teams = division.get("teams")

        if not isinstance(raw_teams, Sequence) or isinstance(
            raw_teams,
            (str, bytes),
        ):
            raise FleaflickerTeamsError(
                "Fleaflicker division has no valid "
                "teams collection."
            )

        for row in raw_teams:
            if not isinstance(row, Mapping):
                raise FleaflickerTeamsError(
                    "Fleaflicker team was not an object."
                )

            if row.get("id") is None:
                raise FleaflickerTeamsError(
                    "Fleaflicker team has no ID."
                )

            team_id = str(row["id"])

            if team_id in seen_team_ids:
                raise FleaflickerTeamsError(
                    "Fleaflicker returned duplicate team "
                    f"ID {team_id!r}."
                )

            seen_team_ids.add(team_id)

            is_managed = team_id == managed_id

            if is_managed:
                managed_matches += 1

            teams.append(
                FantasyTeam(
                    provider="fleaflicker",
                    provider_team_key=team_id,
                    provider_team_id=team_id,
                    name=str(
                        row.get("name")
                        or ""
                    ),
                    is_owned_by_current_user=(
                        is_managed
                    ),
                    waiver_priority=(
                        _optional_int(
                            row.get(
                                "waiverPosition"
                            )
                        )
                    ),
                    weekly_adds_used=None,
                )
            )

    if managed_matches != 1:
        raise FleaflickerTeamsError(
            "Expected exactly one managed Fleaflicker "
            f"team {managed_id!r}; found "
            f"{managed_matches}."
        )

    return tuple(teams)


def fetch_league_teams(
    client: FleaflickerClient,
    league_id: str,
    *,
    managed_team_id: str,
    sport: str = "NHL",
) -> tuple[FantasyTeam, ...]:
    league = league_id.strip()
    managed = managed_team_id.strip()
    sport_code = sport.strip().upper()

    if not league:
        raise ValueError(
            "Fleaflicker league ID must not be empty."
        )

    if not managed:
        raise ValueError(
            "Managed Fleaflicker team ID must not be empty."
        )

    if not sport_code:
        raise ValueError(
            "Fleaflicker sport must not be empty."
        )

    payload = client.get_json(
        "FetchLeagueStandings",
        params={
            "sport": sport_code,
            "league_id": league,
        },
    )

    return parse_teams(
        payload,
        managed_team_id=managed,
    )
