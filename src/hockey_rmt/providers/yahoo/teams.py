from __future__ import annotations

from typing import Any, Mapping

from hockey_rmt.domain.team import FantasyTeam
from hockey_rmt.providers.yahoo.client import (
    YahooClient,
)
from hockey_rmt.providers.yahoo.parsing import (
    indexed_collection,
    merge_metadata_fragments,
    optional_int,
    yahoo_bool,
)


def parse_teams(
    payload: Mapping[str, Any],
) -> tuple[FantasyTeam, ...]:
    league = payload[
        "fantasy_content"
    ]["league"]

    collection = league[1]["teams"]

    teams: list[FantasyTeam] = []

    for entry in indexed_collection(
        collection
    ):
        row = merge_metadata_fragments(
            entry["team"]
        )

        roster_adds = row.get(
            "roster_adds"
        ) or {}

        teams.append(
            FantasyTeam(
                provider="yahoo",
                provider_team_key=str(
                    row["team_key"]
                ),
                provider_team_id=str(
                    row["team_id"]
                ),
                name=str(
                    row["name"]
                ),
                is_owned_by_current_user=(
                    yahoo_bool(
                        row.get(
                            "is_owned_by_current_login"
                        )
                    )
                ),
                waiver_priority=(
                    optional_int(
                        row.get(
                            "waiver_priority"
                        )
                    )
                ),
                weekly_adds_used=(
                    optional_int(
                        roster_adds.get(
                            "value"
                        )
                    )
                ),
            )
        )

    return tuple(teams)


class YahooTeamsError(RuntimeError):
    """Yahoo fantasy-team acquisition failed."""


def fetch_league_teams(
    client: YahooClient,
    league_key: str,
) -> tuple[
    FantasyTeam,
    ...,
]:
    key = league_key.strip()

    if not key:
        raise ValueError(
            "Yahoo league key must not be empty."
        )

    payload = client.get_json(
        f"/league/{key}/teams"
    )

    teams = parse_teams(
        payload
    )

    team_keys = tuple(
        row.provider_team_key
        for row in teams
    )

    if len(team_keys) != len(
        set(team_keys)
    ):
        raise YahooTeamsError(
            "Yahoo returned duplicate fantasy-team keys."
        )

    return teams
