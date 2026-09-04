from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from hockey_rmt.domain.hockey_team import HockeyTeam
from hockey_rmt.domain.nhl_roster import CurrentNhlGoalie
from hockey_rmt.providers.nhl.client import NhlClient


class NhlRosterError(RuntimeError):
    """NHL roster retrieval or parsing failed."""


def parse_current_goalies(
    payload: Mapping[str, Any],
    *,
    expected_team_abbr: str,
) -> tuple[CurrentNhlGoalie, ...]:
    team = str(
        expected_team_abbr
    ).strip().upper()

    if not team:
        raise NhlRosterError(
            "Expected NHL team abbreviation "
            "must not be empty."
        )

    raw_goalies = payload.get(
        "goalies"
    )

    if not isinstance(
        raw_goalies,
        list,
    ):
        raise NhlRosterError(
            "NHL current roster payload did "
            "not contain a goalies list."
        )

    result = []
    seen_ids = set()

    for row in raw_goalies:
        if not isinstance(
            row,
            Mapping,
        ):
            raise NhlRosterError(
                "NHL current roster goalie "
                "was not an object."
            )

        try:
            nhl_player_id = int(
                row["id"]
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise NhlRosterError(
                "NHL current roster goalie "
                "did not contain a valid id."
            ) from exc

        if nhl_player_id in seen_ids:
            raise NhlRosterError(
                "NHL current roster contained "
                "duplicate goalie playerId "
                f"{nhl_player_id}."
            )

        seen_ids.add(
            nhl_player_id
        )

        result.append(
            CurrentNhlGoalie(
                nhl_player_id=(
                    nhl_player_id
                ),
                nhl_team_abbr=team,
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.nhl_player_id
            ),
        )
    )


def fetch_current_goalies(
    client: NhlClient,
    *,
    teams: Sequence[HockeyTeam],
) -> tuple[CurrentNhlGoalie, ...]:
    if not teams:
        raise NhlRosterError(
            "No NHL teams were supplied."
        )

    result = []
    seen_player_ids = set()

    for team in teams:
        abbreviation = str(
            team.abbreviation
        ).strip().upper()

        if not abbreviation:
            raise NhlRosterError(
                "Canonical NHL team had "
                "no abbreviation."
            )

        payload = client.get_json(
            f"/roster/{abbreviation}/current"
        )

        goalies = parse_current_goalies(
            payload,
            expected_team_abbr=(
                abbreviation
            ),
        )

        for goalie in goalies:
            if (
                goalie.nhl_player_id
                in seen_player_ids
            ):
                raise NhlRosterError(
                    "NHL playerId appeared on "
                    "multiple current rosters: "
                    f"{goalie.nhl_player_id}."
                )

            seen_player_ids.add(
                goalie.nhl_player_id
            )

            result.append(
                goalie
            )

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.nhl_team_abbr,
                row.nhl_player_id,
            ),
        )
    )
