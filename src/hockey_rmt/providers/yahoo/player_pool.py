from __future__ import annotations

from pathlib import Path

from hockey_rmt.domain.player import Player
from hockey_rmt.providers.yahoo.client import (
    YahooClient,
    write_raw_snapshot,
)
from hockey_rmt.providers.yahoo.players import (
    parse_players,
)


class YahooPlayerPoolError(RuntimeError):
    """Yahoo player-pool acquisition failed."""


def fetch_all_players(
    client: YahooClient,
    league_key: str,
    *,
    page_size: int = 25,
    max_pages: int = 100,
    raw_directory: Path | None = None,
) -> tuple[Player, ...]:
    key = league_key.strip()

    if not key:
        raise ValueError(
            "Yahoo league key must not be empty."
        )

    if page_size <= 0:
        raise ValueError(
            "Page size must be positive."
        )

    if max_pages <= 0:
        raise ValueError(
            "Maximum page count must be positive."
        )

    players: list[Player] = []
    seen_keys: set[str] = set()

    for page_number in range(max_pages):
        start = page_number * page_size

        payload = client.get_json(
            f"/league/{key}/"
            f"players;start={start};count={page_size}"
        )

        if raw_directory is not None:
            write_raw_snapshot(
                payload,
                raw_directory
                / (
                    f"players_start_{start:04d}"
                    f"_count_{page_size:04d}.json"
                ),
            )

        page = parse_players(
            payload
        )

        if not page:
            return tuple(players)

        for player in page:
            if (
                player.provider_player_key
                in seen_keys
            ):
                raise YahooPlayerPoolError(
                    "Yahoo returned duplicate player "
                    f"{player.provider_player_key!r} "
                    f"while paging league {key!r}."
                )

            seen_keys.add(
                player.provider_player_key
            )

        players.extend(page)

        if len(page) < page_size:
            return tuple(players)

    raise YahooPlayerPoolError(
        "Yahoo player pagination exceeded "
        f"{max_pages} pages without reaching "
        "a terminal page."
    )
