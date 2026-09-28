from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hockey_rmt.providers.fleaflicker.client import (
    FleaflickerClient,
)


@dataclass(frozen=True)
class FleaflickerRosterRow:
    provider_player_id: str
    full_name: str

    roster_slot: str

    primary_position: str
    eligible_positions: tuple[str, ...]

    nhl_team_abbr: str | None
    nhl_team_name: str | None

    status: str | None
    status_full: str | None


class FleaflickerRosterError(RuntimeError):
    """Fleaflicker roster acquisition failed."""


def parse_roster(
    payload: Mapping[str, Any],
) -> tuple[FleaflickerRosterRow, ...]:
    groups = payload.get("groups")

    if not isinstance(groups, Sequence) or isinstance(
        groups,
        (str, bytes),
    ):
        raise FleaflickerRosterError(
            "Fleaflicker roster payload has no "
            "valid groups collection."
        )

    rows: list[FleaflickerRosterRow] = []
    seen_ids: set[str] = set()

    for group in groups:
        if not isinstance(group, Mapping):
            raise FleaflickerRosterError(
                "Fleaflicker roster group was not an object."
            )

        slots = group.get("slots")

        if not isinstance(slots, Sequence) or isinstance(
            slots,
            (str, bytes),
        ):
            raise FleaflickerRosterError(
                "Fleaflicker roster group has no "
                "valid slots collection."
            )

        for slot in slots:
            if not isinstance(slot, Mapping):
                raise FleaflickerRosterError(
                    "Fleaflicker roster slot was not an object."
                )

            league_player = slot.get("leaguePlayer")

            # Empty lineup or bench slots are valid.
            if not isinstance(league_player, Mapping):
                continue

            pro_player = league_player.get("proPlayer")

            if not isinstance(pro_player, Mapping):
                raise FleaflickerRosterError(
                    "Fleaflicker rostered player has no "
                    "proPlayer object."
                )

            if pro_player.get("id") is None:
                raise FleaflickerRosterError(
                    "Fleaflicker rostered player has no ID."
                )

            player_id = str(
                pro_player["id"]
            )

            if player_id in seen_ids:
                raise FleaflickerRosterError(
                    "Fleaflicker roster returned duplicate "
                    f"player ID {player_id!r}."
                )

            seen_ids.add(player_id)

            position = slot.get("position") or {}

            if not isinstance(position, Mapping):
                position = {}

            eligibility_raw = (
                pro_player.get(
                    "positionEligibility"
                )
                or []
            )

            if not isinstance(
                eligibility_raw,
                Sequence,
            ) or isinstance(
                eligibility_raw,
                (str, bytes),
            ):
                raise FleaflickerRosterError(
                    "Fleaflicker player eligibility was "
                    "not a collection."
                )

            eligible_positions = tuple(
                str(value)
                for value in eligibility_raw
                if value
            )

            pro_team = (
                pro_player.get("proTeam")
                or {}
            )

            if not isinstance(pro_team, Mapping):
                pro_team = {}

            injury = (
                pro_player.get("injury")
                or {}
            )

            if not isinstance(injury, Mapping):
                injury = {}

            status = (
                str(injury["severity"])
                if injury.get("severity")
                else None
            )

            status_parts = tuple(
                str(value)
                for value in (
                    injury.get("typeFull"),
                    injury.get("description"),
                )
                if value
            )

            status_full = (
                " - ".join(status_parts)
                if status_parts
                else None
            )

            rows.append(
                FleaflickerRosterRow(
                    provider_player_id=player_id,
                    full_name=str(
                        pro_player.get(
                            "nameFull"
                        )
                        or ""
                    ),
                    roster_slot=str(
                        position.get("label")
                        or group.get("group")
                        or ""
                    ),
                    primary_position=str(
                        pro_player.get("position")
                        or ""
                    ),
                    eligible_positions=(
                        eligible_positions
                    ),
                    nhl_team_abbr=(
                        str(
                            pro_player[
                                "proTeamAbbreviation"
                            ]
                        )
                        if pro_player.get(
                            "proTeamAbbreviation"
                        )
                        else None
                    ),
                    nhl_team_name=(
                        str(
                            pro_team.get("name")
                            or ""
                        )
                        if pro_team.get("name")
                        else None
                    ),
                    status=status,
                    status_full=status_full,
                )
            )

    return tuple(rows)


def fetch_team_roster(
    client: FleaflickerClient,
    league_id: str,
    team_id: str,
    *,
    season: int,
    sport: str = "NHL",
) -> tuple[FleaflickerRosterRow, ...]:
    league = league_id.strip()
    team = team_id.strip()
    sport_code = sport.strip().upper()

    if not league:
        raise ValueError(
            "Fleaflicker league ID must not be empty."
        )

    if not team:
        raise ValueError(
            "Fleaflicker team ID must not be empty."
        )

    if season <= 0:
        raise ValueError(
            "Fleaflicker season must be positive."
        )

    if not sport_code:
        raise ValueError(
            "Fleaflicker sport must not be empty."
        )

    payload = client.get_json(
        "FetchRoster",
        params={
            "sport": sport_code,
            "league_id": league,
            "team_id": team,
            "season": season,
        },
    )

    return parse_roster(payload)
