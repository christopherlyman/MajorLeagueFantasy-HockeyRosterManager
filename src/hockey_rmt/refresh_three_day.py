from __future__ import annotations

import argparse
import os

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from hockey_rmt.providers.nhl.client import NhlClient
from hockey_rmt.providers.nhl.schedule import (
    fetch_schedule,
)
from hockey_rmt.providers.nhl.teams import (
    fetch_current_teams,
)
from hockey_rmt.providers.yahoo.auth import (
    get_access_token,
)
from hockey_rmt.providers.yahoo.client import (
    YahooClient,
)
from hockey_rmt.providers.yahoo.league import (
    fetch_league_definition,
)
from hockey_rmt.providers.yahoo.ownership import (
    fetch_all_player_market_states,
)
from hockey_rmt.providers.yahoo.percent_rostered import (
    fetch_all_player_percent_rostered,
)
from hockey_rmt.providers.yahoo.player_pool import (
    fetch_all_players,
)
from hockey_rmt.services.daily_refresh import (
    build_three_day_refresh_payload,
)
from hockey_rmt.services.player_strength_snapshot import (
    load_player_strength_snapshot,
)
from hockey_rmt.ui.three_day_snapshot import (
    load_three_day_snapshot,
    write_three_day_snapshot,
)


LEAGUE_KEY = "477.l.10961"
MANAGED_TEAM_KEY = "477.l.10961.t.1"
TEAM_NAME = "Drop The Gloves"

PROJECTION_SEASON_ID = 20262027

SEASON_START = date(
    2026,
    9,
    29,
)

MODEL_LABEL = (
    "CANONICAL 2026-27 PRESEASON — "
    "established-skater historical/age calibration; "
    "rookie age/draft-capital model; "
    "long-absence population prior; "
    "goalie historical quality/workload. "
    "Yahoo availability applied; "
    "current-role, recent-form, and matchup "
    "adjustments are not yet applied."
)


def _project_root() -> Path:
    return (
        Path(
            __file__
        )
        .resolve()
        .parents[
            2
        ]
    )


def _default_base_date() -> date:
    today = (
        datetime.now(
            ZoneInfo(
                "America/New_York"
            )
        )
        .date()
    )

    return max(
        today,
        SEASON_START,
    )


def _parse_date(
    value: str,
) -> date:
    try:
        return date.fromisoformat(
            value
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "base date must be YYYY-MM-DD"
        ) from exc


def _schedule_union(
    client: NhlClient,
    *,
    base_date: date,
) -> tuple[
    object,
    ...,
]:
    games_by_id = {}

    for offset in range(
        3
    ):
        anchor = (
            base_date
            + timedelta(
                days=offset
            )
        )

        games = fetch_schedule(
            client,
            anchor,
        )

        for game in games:
            key = str(
                game.provider_game_id
            )

            existing = games_by_id.get(
                key
            )

            if (
                existing is not None
                and existing != game
            ):
                raise RuntimeError(
                    "NHL schedule returned "
                    "conflicting records for "
                    f"{key!r}."
                )

            games_by_id[
                key
            ] = game

    return tuple(
        games_by_id.values()
    )


def main() -> int:
    root = _project_root()

    parser = argparse.ArgumentParser(
        description=(
            "Refresh the NFHL availability-aware "
            "three-day decision snapshot."
        )
    )

    parser.add_argument(
        "--base-date",
        type=_parse_date,
        default=_default_base_date(),
    )

    parser.add_argument(
        "--strength-artifact",
        type=Path,
        default=(
            root
            / "data/runtime/"
              "player_strengths_20262027.json"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            root
            / "data/runtime/"
              "three_day_rankings.json"
        ),
    )

    args = parser.parse_args()

    required_env = (
        "POSTGRES_DSN",
        "YAHOO_CLIENT_ID",
        "YAHOO_CLIENT_SECRET",
    )

    missing = [
        name
        for name in required_env
        if not str(
            os.environ.get(
                name,
                ""
            )
        ).strip()
    ]

    if missing:
        raise RuntimeError(
            "Missing required environment "
            "variables: "
            + ", ".join(
                missing
            )
        )

    strengths = (
        load_player_strength_snapshot(
            args.strength_artifact,
            expected_projection_season_id=(
                PROJECTION_SEASON_ID
            ),
        )
    )

    token = get_access_token(
        dsn=os.environ[
            "POSTGRES_DSN"
        ],
        client_id=os.environ[
            "YAHOO_CLIENT_ID"
        ],
        client_secret=os.environ[
            "YAHOO_CLIENT_SECRET"
        ],
        token_key="mlf_tools",
    )

    yahoo = YahooClient(
        token
    )

    league = (
        fetch_league_definition(
            yahoo,
            LEAGUE_KEY,
        )
    )

    players = (
        fetch_all_players(
            yahoo,
            LEAGUE_KEY,
        )
    )

    player_keys = tuple(
        row.provider_player_key
        for row in players
    )

    market_states = (
        fetch_all_player_market_states(
            yahoo,
            LEAGUE_KEY,
            player_keys,
        )
    )

    percent_rostered = (
        fetch_all_player_percent_rostered(
            yahoo,
            LEAGUE_KEY,
            player_keys,
        )
    )

    nhl = NhlClient()

    nhl_teams = (
        fetch_current_teams(
            nhl
        )
    )

    games = _schedule_union(
        nhl,
        base_date=(
            args.base_date
        ),
    )

    payload = (
        build_three_day_refresh_payload(
            players=players,
            player_strengths=(
                strengths
            ),
            nhl_teams=nhl_teams,
            games=games,
            market_states=(
                market_states
            ),
            percent_rostered_by_player_key=(
                percent_rostered
            ),
            projection_season_id=(
                PROJECTION_SEASON_ID
            ),
            base_date=(
                args.base_date
            ),
            managed_team_key=(
                MANAGED_TEAM_KEY
            ),
            league_name=(
                league.league_name
            ),
            team_name=(
                TEAM_NAME
            ),
            model_label=(
                MODEL_LABEL
            ),
        )
    )

    written = (
        write_three_day_snapshot(
            payload=payload,
            path=args.output,
        )
    )

    loaded = (
        load_three_day_snapshot(
            written
        )
    )

    print(
        f"BASE_DATE={args.base_date}"
    )
    print(
        f"YAHOO_PLAYERS={len(players)}"
    )
    print(
        f"CANONICAL_STRENGTHS={len(strengths)}"
    )
    print(
        f"NHL_TEAMS={len(nhl_teams)}"
    )
    print(
        f"SCHEDULE_UNION_GAMES={len(games)}"
    )
    print(
        f"MARKET_ROWS={len(market_states)}"
    )
    print(
        "PERCENT_ROSTERED_ROWS="
        f"{len(percent_rostered)}"
    )
    print(
        "SNAPSHOT_ROWS="
        f"{len(loaded['rows'])}"
    )
    print(
        f"OUTPUT={written}"
    )
    print(
        "NFHL_THREE_DAY_REFRESH=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
