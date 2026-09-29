from __future__ import annotations

from collections.abc import Sequence

from hockey_rmt.domain.market import (
    PlayerMarketState,
)
from hockey_rmt.domain.player import Player
from hockey_rmt.providers.fleaflicker.roster import (
    FleaflickerRosterRow,
)


MARKET_STATE_OWNERSHIP_UNKNOWN = (
    "ownership_unknown"
)


class FleaflickerOwnershipError(RuntimeError):
    """Safe Fleaflicker ownership normalization failed."""


def build_managed_roster_market_states(
    *,
    players: Sequence[Player],
    roster: Sequence[FleaflickerRosterRow],
    league_id: str,
    managed_team_id: str,
    managed_team_name: str,
) -> tuple[PlayerMarketState, ...]:
    league = league_id.strip()
    managed_id = managed_team_id.strip()
    managed_name = managed_team_name.strip()

    if not league:
        raise ValueError(
            "Fleaflicker league ID must not be empty."
        )

    if not managed_id:
        raise ValueError(
            "Managed team ID must not be empty."
        )

    if not managed_name:
        raise ValueError(
            "Managed team name must not be empty."
        )

    player_by_id: dict[str, Player] = {}

    for player in players:
        player_id = str(
            player.provider_player_id
        ).strip()

        if not player_id:
            raise FleaflickerOwnershipError(
                "Player contained blank provider ID."
            )

        if player_id in player_by_id:
            raise FleaflickerOwnershipError(
                "Duplicate Fleaflicker player ID "
                f"{player_id!r}."
            )

        player_by_id[player_id] = player

    roster_ids: set[str] = set()

    for row in roster:
        player_id = str(
            row.provider_player_id
        ).strip()

        if player_id in roster_ids:
            raise FleaflickerOwnershipError(
                "Duplicate managed-roster player ID "
                f"{player_id!r}."
            )

        if player_id not in player_by_id:
            raise FleaflickerOwnershipError(
                "Managed-roster player was absent "
                "from full Fleaflicker universe: "
                f"{player_id!r}."
            )

        roster_ids.add(player_id)

    result: list[PlayerMarketState] = []

    for player in players:
        player_id = player.provider_player_id

        if player_id in roster_ids:
            result.append(
                PlayerMarketState(
                    provider="fleaflicker",
                    provider_league_key=league,
                    provider_player_key=(
                        player.provider_player_key
                    ),
                    market_state="rostered",
                    provider_ownership_type="team",
                    owner_team_key=managed_id,
                    owner_team_name=managed_name,
                )
            )
        else:
            # Deliberately does NOT infer free-agent or waiver
            # state. The current provider evidence only proves
            # that this player is not on the managed roster.
            result.append(
                PlayerMarketState(
                    provider="fleaflicker",
                    provider_league_key=league,
                    provider_player_key=(
                        player.provider_player_key
                    ),
                    market_state=(
                        MARKET_STATE_OWNERSHIP_UNKNOWN
                    ),
                    provider_ownership_type="unknown",
                    owner_team_key=None,
                    owner_team_name=None,
                )
            )

    return tuple(result)
