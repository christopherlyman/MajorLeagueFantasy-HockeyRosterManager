from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from hockey_rmt.domain.market import (
    PlayerMarketState,
)
from hockey_rmt.providers.yahoo.client import (
    YahooClient,
)
from hockey_rmt.providers.yahoo.parsing import (
    indexed_collection,
    merge_metadata_fragments,
)


class YahooOwnershipError(RuntimeError):
    """Yahoo ownership acquisition failed."""


def _canonical_market_state(
    ownership_type: str,
) -> str:
    known = {
        "freeagents": "free_agent",
        "waivers": "waiver",
        "team": "rostered",
    }

    return known.get(
        ownership_type.strip().lower(),
        "unknown",
    )


def parse_player_market_states(
    payload: Mapping[str, Any],
    league_key: str,
) -> tuple[PlayerMarketState, ...]:
    league = payload[
        "fantasy_content"
    ]["league"]

    collection = league[1]["players"]

    if isinstance(collection, list):
        if not collection:
            return ()

        raise YahooOwnershipError(
            "Yahoo returned an unexpected "
            "list-shaped ownership collection."
        )

    states: list[PlayerMarketState] = []

    for entry in indexed_collection(
        collection
    ):
        row = merge_metadata_fragments(
            entry["player"]
        )

        player_key = str(
            row["player_key"]
        )

        ownership = row.get(
            "ownership"
        )

        if not isinstance(
            ownership,
            Mapping,
        ):
            raise YahooOwnershipError(
                "Yahoo player "
                f"{player_key!r} did not include "
                "an ownership object."
            )

        ownership_type = str(
            ownership.get(
                "ownership_type"
            )
            or ""
        )

        if not ownership_type:
            raise YahooOwnershipError(
                "Yahoo player "
                f"{player_key!r} has no "
                "ownership_type."
            )

        states.append(
            PlayerMarketState(
                provider="yahoo",
                provider_league_key=(
                    league_key
                ),
                provider_player_key=(
                    player_key
                ),
                market_state=(
                    _canonical_market_state(
                        ownership_type
                    )
                ),
                provider_ownership_type=(
                    ownership_type
                ),
                owner_team_key=(
                    str(
                        ownership[
                            "owner_team_key"
                        ]
                    )
                    if ownership.get(
                        "owner_team_key"
                    )
                    else None
                ),
                owner_team_name=(
                    str(
                        ownership[
                            "owner_team_name"
                        ]
                    )
                    if ownership.get(
                        "owner_team_name"
                    )
                    else None
                ),
            )
        )

    return tuple(states)


def fetch_player_market_states(
    client: YahooClient,
    league_key: str,
    player_keys: Sequence[str],
) -> tuple[PlayerMarketState, ...]:
    key = league_key.strip()

    if not key:
        raise ValueError(
            "Yahoo league key must not be empty."
        )

    requested = tuple(
        player_key.strip()
        for player_key in player_keys
        if player_key.strip()
    )

    if not requested:
        raise ValueError(
            "At least one Yahoo player key "
            "is required."
        )

    if len(requested) != len(set(requested)):
        raise ValueError(
            "Yahoo player keys must be unique."
        )

    joined = ",".join(requested)

    payload = client.get_json(
        f"/league/{key}/"
        f"players;player_keys={joined}/ownership"
    )

    states = parse_player_market_states(
        payload,
        key,
    )

    returned = {
        state.provider_player_key
        for state in states
    }

    expected = set(requested)

    if returned != expected:
        raise YahooOwnershipError(
            "Yahoo ownership response keys "
            "did not match requested player keys. "
            f"requested={sorted(expected)!r} "
            f"returned={sorted(returned)!r}"
        )

    return states



def fetch_all_player_market_states(
    client: YahooClient,
    league_key: str,
    player_keys: Sequence[str],
    *,
    batch_size: int = 25,
) -> tuple[PlayerMarketState, ...]:
    if batch_size <= 0:
        raise ValueError(
            "Ownership batch size must be positive."
        )

    requested = tuple(
        player_key.strip()
        for player_key in player_keys
        if player_key.strip()
    )

    if not requested:
        return ()

    if len(requested) != len(set(requested)):
        raise ValueError(
            "Yahoo player keys must be unique."
        )

    states: list[PlayerMarketState] = []
    seen: set[str] = set()

    for start in range(
        0,
        len(requested),
        batch_size,
    ):
        batch = requested[
            start:start + batch_size
        ]

        batch_states = (
            fetch_player_market_states(
                client,
                league_key,
                batch,
            )
        )

        for state in batch_states:
            player_key = (
                state.provider_player_key
            )

            if player_key in seen:
                raise YahooOwnershipError(
                    "Yahoo returned duplicate "
                    "ownership state for player "
                    f"{player_key!r}."
                )

            seen.add(player_key)

        states.extend(batch_states)

    expected = set(requested)

    if seen != expected:
        raise YahooOwnershipError(
            "Complete Yahoo ownership result "
            "did not match requested players. "
            f"missing={sorted(expected - seen)!r} "
            f"unexpected={sorted(seen - expected)!r}"
        )

    return tuple(states)
