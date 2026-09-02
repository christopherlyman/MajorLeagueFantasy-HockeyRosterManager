from __future__ import annotations

from typing import Any, Mapping

from hockey_rmt.domain.player import Player
from hockey_rmt.providers.yahoo.parsing import (
    indexed_collection,
    merge_metadata_fragments,
    yahoo_bool,
)


def parse_players(
    payload: Mapping[str, Any],
) -> tuple[Player, ...]:
    league = payload[
        "fantasy_content"
    ]["league"]

    collection = league[1]["players"]

    players: list[Player] = []

    for entry in indexed_collection(
        collection
    ):
        row = merge_metadata_fragments(
            entry["player"]
        )

        name = row.get("name") or {}

        eligible_positions = tuple(
            str(item["position"])
            for item in (
                row.get(
                    "eligible_positions"
                )
                or []
            )
            if item.get("position")
        )

        players.append(
            Player(
                provider="yahoo",
                provider_player_key=str(
                    row["player_key"]
                ),
                provider_player_id=str(
                    row["player_id"]
                ),
                full_name=str(
                    name.get("full")
                    or ""
                ),
                nhl_team_key=(
                    str(
                        row[
                            "editorial_team_key"
                        ]
                    )
                    if row.get(
                        "editorial_team_key"
                    )
                    else None
                ),
                nhl_team_name=(
                    str(
                        row[
                            "editorial_team_full_name"
                        ]
                    )
                    if row.get(
                        "editorial_team_full_name"
                    )
                    else None
                ),
                nhl_team_abbr=(
                    str(
                        row[
                            "editorial_team_abbr"
                        ]
                    )
                    if row.get(
                        "editorial_team_abbr"
                    )
                    else None
                ),
                position_type=str(
                    row.get(
                        "position_type"
                    )
                    or ""
                ),
                primary_position=str(
                    row.get(
                        "primary_position"
                    )
                    or ""
                ),
                eligible_positions=(
                    eligible_positions
                ),
                status=(
                    str(row["status"])
                    if row.get("status")
                    else None
                ),
                status_full=(
                    str(
                        row["status_full"]
                    )
                    if row.get(
                        "status_full"
                    )
                    else None
                ),
                is_undroppable=(
                    yahoo_bool(
                        row.get(
                            "is_undroppable"
                        )
                    )
                ),
            )
        )

    return tuple(players)
