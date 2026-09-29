from __future__ import annotations

from typing import Any, Mapping, Sequence

from hockey_rmt.domain.player import Player
from hockey_rmt.providers.fleaflicker.client import (
    FleaflickerClient,
)


PLAYER_LISTING_SORT = "SORT_DRAFT_RANKING"


class FleaflickerPlayerPoolError(RuntimeError):
    """Fleaflicker player-pool acquisition failed."""


def parse_player_listing(
    payload: Mapping[str, Any],
) -> tuple[Player, ...]:
    rows = payload.get("players")

    if not isinstance(rows, Sequence) or isinstance(
        rows,
        (str, bytes),
    ):
        raise FleaflickerPlayerPoolError(
            "Fleaflicker player listing has no "
            "valid players collection."
        )

    players: list[Player] = []
    seen_ids: set[str] = set()

    for row in rows:
        if not isinstance(row, Mapping):
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player listing row "
                "was not an object."
            )

        pro_player = row.get("proPlayer")

        if not isinstance(pro_player, Mapping):
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player listing row has no "
                "proPlayer object."
            )

        if pro_player.get("id") is None:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player has no ID."
            )

        player_id = str(
            pro_player["id"]
        )

        if player_id in seen_ids:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player listing returned "
                f"duplicate player ID {player_id!r}."
            )

        seen_ids.add(player_id)

        full_name = str(
            pro_player.get("nameFull")
            or ""
        ).strip()

        if not full_name:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player has no name."
            )

        primary_position = str(
            pro_player.get("position")
            or ""
        ).strip()

        if not primary_position:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player has no "
                "primary position."
            )

        eligibility_raw = (
            pro_player.get(
                "positionEligibility"
            )
        )

        if not isinstance(
            eligibility_raw,
            Sequence,
        ) or isinstance(
            eligibility_raw,
            (str, bytes),
        ):
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player eligibility was "
                "not a collection."
            )

        eligible_positions = tuple(
            str(value).strip()
            for value in eligibility_raw
            if str(value).strip()
        )

        if not eligible_positions:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player has no "
                "eligible positions."
            )

        display_group = str(
            row.get("displayGroup")
            or ""
        ).strip()

        if display_group == "GOALIE":
            position_type = "G"
        elif display_group == "SKATER":
            position_type = "P"
        else:
            raise FleaflickerPlayerPoolError(
                "Unexpected Fleaflicker display group "
                f"{display_group!r} for player "
                f"{player_id!r}."
            )

        nhl_team_abbr = str(
            pro_player.get(
                "proTeamAbbreviation"
            )
            or ""
        ).strip()

        if not nhl_team_abbr:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player has no "
                f"NHL team abbreviation: {player_id!r}."
            )

        pro_team = (
            pro_player.get("proTeam")
            or {}
        )

        if not isinstance(pro_team, Mapping):
            pro_team = {}

        nhl_team_name_value = str(
            pro_team.get("name")
            or ""
        ).strip()

        nhl_team_name = (
            nhl_team_name_value
            if nhl_team_name_value
            else None
        )

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

        players.append(
            Player(
                provider="fleaflicker",
                provider_player_key=player_id,
                provider_player_id=player_id,
                full_name=full_name,
                nhl_team_key=None,
                nhl_team_name=nhl_team_name,
                nhl_team_abbr=nhl_team_abbr,
                position_type=position_type,
                primary_position=primary_position,
                eligible_positions=(
                    eligible_positions
                ),
                status=status,
                status_full=status_full,
                is_undroppable=None,
            )
        )

    return tuple(players)


def fetch_all_players(
    client: FleaflickerClient,
    league_id: str,
    *,
    season: int,
    sport: str = "NHL",
    max_pages: int = 100,
) -> tuple[Player, ...]:
    league = league_id.strip()
    sport_code = sport.strip().upper()

    if not league:
        raise ValueError(
            "Fleaflicker league ID must not be empty."
        )

    if season <= 0:
        raise ValueError(
            "Fleaflicker season must be positive."
        )

    if not sport_code:
        raise ValueError(
            "Fleaflicker sport must not be empty."
        )

    if max_pages <= 0:
        raise ValueError(
            "Maximum page count must be positive."
        )

    players: list[Player] = []
    seen_ids: set[str] = set()

    result_total: int | None = None
    offset = 0

    for _ in range(max_pages):
        payload = client.get_json(
            "FetchPlayerListing",
            params={
                "sport": sport_code,
                "league_id": league,
                "sort": PLAYER_LISTING_SORT,
                "sort_season": season,
                "result_offset": offset,
            },
        )

        current_total = payload.get(
            "resultTotal"
        )

        if not isinstance(current_total, int):
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player listing returned "
                "an invalid resultTotal."
            )

        if current_total < 0:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player listing returned "
                "a negative resultTotal."
            )

        if result_total is None:
            result_total = current_total
        elif current_total != result_total:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker resultTotal changed "
                "during player pagination."
            )

        rows = payload.get("players")

        if not isinstance(rows, Sequence) or isinstance(
            rows,
            (str, bytes),
        ):
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player listing has no "
                "valid players collection."
            )

        remaining = (
            result_total
            - len(players)
        )

        if remaining < 0:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player pagination "
                "exceeded resultTotal."
            )

        accepted_rows = tuple(
            rows[:remaining]
        )

        page_payload = dict(payload)
        page_payload["players"] = accepted_rows

        page_players = parse_player_listing(
            page_payload
        )

        if (
            remaining > 0
            and not page_players
        ):
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player pagination "
                "returned no rows before resultTotal "
                "was reached."
            )

        for player in page_players:
            key = (
                player.provider_player_key
            )

            if key in seen_ids:
                raise FleaflickerPlayerPoolError(
                    "Fleaflicker returned duplicate "
                    f"player ID {key!r} inside the "
                    "valid result window."
                )

            seen_ids.add(key)

        players.extend(page_players)

        if len(players) == result_total:
            return tuple(players)

        next_offset = payload.get(
            "resultOffsetNext"
        )

        if not isinstance(next_offset, int):
            raise FleaflickerPlayerPoolError(
                "Fleaflicker player pagination "
                "ended before resultTotal was reached."
            )

        if next_offset <= offset:
            raise FleaflickerPlayerPoolError(
                "Fleaflicker resultOffsetNext did "
                "not advance."
            )

        offset = next_offset

    raise FleaflickerPlayerPoolError(
        "Fleaflicker player pagination exceeded "
        f"{max_pages} pages before resultTotal "
        "was reached."
    )
