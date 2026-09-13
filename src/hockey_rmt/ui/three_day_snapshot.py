from __future__ import annotations

from hockey_rmt.domain.player_availability import (
    classify_player_availability,
)

import copy
from collections.abc import Mapping
import json
import os

from pathlib import Path
from typing import Any

from hockey_rmt.domain.market import (
    PlayerMarketState,
)
from hockey_rmt.domain.player import Player

from hockey_rmt.domain.three_day_ranking import (
    RankedDayValue,
    ThreeDayPlayerRanking,
)


SNAPSHOT_SCHEMA_VERSION = 1


class ThreeDaySnapshotError(
    RuntimeError
):
    """Three-day UI snapshot processing failed."""


def _day_payload(
    row: RankedDayValue,
) -> dict[
    str,
    Any,
]:
    return {
        "date": (
            row.game_date.isoformat()
        ),
        "team": (
            row.nhl_team_abbr
        ),
        "schedule_state": (
            row.schedule_state
        ),
        "value_state": (
            row.value_state
        ),
        "expected_points": (
            row.expected_fantasy_points
        ),
        "rank": (
            row.daily_rank
        ),
        "opponent": (
            row.opponent_team_abbr
        ),
        "home_away": (
            row.home_away
        ),
        "provider_game_id": (
            row.provider_game_id
        ),
        "start_time_utc": (row.start_time_utc.isoformat() if row.start_time_utc is not None else None),
    }



def enrich_three_day_snapshot_availability(
    payload: dict[
        str,
        Any,
    ],
    *,
    players: tuple[
        Player,
        ...,
    ],
) -> dict[
    str,
    Any,
]:
    enriched = copy.deepcopy(
        payload
    )

    rows = enriched.get(
        "rows"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise ThreeDaySnapshotError(
            "Snapshot rows must be a list."
        )

    players_by_key = {}

    for player in players:
        key = str(
            player.provider_player_key
        ).strip()

        if not key:
            raise ThreeDaySnapshotError(
                "Yahoo player key was blank."
            )

        if key in players_by_key:
            raise ThreeDaySnapshotError(
                "Duplicate Yahoo player key "
                f"{key!r}."
            )

        players_by_key[
            key
        ] = player

    snapshot_keys = []

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            raise ThreeDaySnapshotError(
                "Snapshot player row must "
                "be an object."
            )

        key = str(
            row.get(
                "provider_player_key",
                "",
            )
        ).strip()

        if not key:
            raise ThreeDaySnapshotError(
                "Snapshot player row had no "
                "provider player key."
            )

        snapshot_keys.append(
            key
        )

    if (
        len(
            snapshot_keys
        )
        != len(
            set(
                snapshot_keys
            )
        )
    ):
        raise ThreeDaySnapshotError(
            "Snapshot contained duplicate "
            "provider player keys."
        )

    if (
        set(
            snapshot_keys
        )
        != set(
            players_by_key
        )
    ):
        raise ThreeDaySnapshotError(
            "Yahoo player universe did not "
            "exactly match snapshot universe."
        )

    for row in rows:
        key = str(
            row[
                "provider_player_key"
            ]
        )

        player = players_by_key[
            key
        ]

        row[
            "availability_state"
        ] = classify_player_availability(
            provider=player.provider,
            status=player.status,
        )

        row[
            "provider_status"
        ] = player.status

        row[
            "provider_status_full"
        ] = player.status_full

    return enriched


def enrich_three_day_snapshot_market(
    payload: dict[
        str,
        Any,
    ],
    *,
    players: tuple[
        Player,
        ...,
    ],
    market_states: tuple[
        PlayerMarketState,
        ...,
    ],
    managed_team_key: str,
) -> dict[
    str,
    Any,
]:
    team_key = managed_team_key.strip()

    if not team_key:
        raise ThreeDaySnapshotError(
            "managed_team_key must not be blank."
        )

    rows = payload.get(
        "rows"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise ThreeDaySnapshotError(
            "Snapshot rows must be a list "
            "before market enrichment."
        )

    row_keys = [
        str(
            row.get(
                "provider_player_key",
                "",
            )
        )
        for row in rows
    ]

    if any(
        not key
        for key in row_keys
    ):
        raise ThreeDaySnapshotError(
            "Snapshot contains blank "
            "provider player keys."
        )

    if len(row_keys) != len(
        set(row_keys)
    ):
        raise ThreeDaySnapshotError(
            "Snapshot contains duplicate "
            "provider player keys."
        )

    player_by_key = {
        player.provider_player_key: player
        for player in players
    }

    market_by_key = {
        state.provider_player_key: state
        for state in market_states
    }

    if len(player_by_key) != len(
        players
    ):
        raise ThreeDaySnapshotError(
            "Player metadata contains duplicate "
            "provider player keys."
        )

    if len(market_by_key) != len(
        market_states
    ):
        raise ThreeDaySnapshotError(
            "Market metadata contains duplicate "
            "provider player keys."
        )

    expected = set(
        row_keys
    )

    if set(player_by_key) != expected:
        raise ThreeDaySnapshotError(
            "Player metadata universe does not "
            "match snapshot rows."
        )

    if set(market_by_key) != expected:
        raise ThreeDaySnapshotError(
            "Market metadata universe does not "
            "match snapshot rows."
        )

    enriched = copy.deepcopy(
        payload
    )

    for row in enriched[
        "rows"
    ]:
        key = str(
            row[
                "provider_player_key"
            ]
        )

        player = player_by_key[
            key
        ]

        market = market_by_key[
            key
        ]

        positions = [
            str(position).strip()
            for position
            in player.eligible_positions
            if str(position).strip()
        ]

        if len(positions) != len(
            set(positions)
        ):
            raise ThreeDaySnapshotError(
                "Yahoo eligibility contains "
                f"duplicates for {key!r}."
            )

        market_state = str(
            market.market_state
            or ""
        ).strip()

        if not market_state:
            raise ThreeDaySnapshotError(
                "Market state must not be blank "
                f"for {key!r}."
            )

        on_managed_team = (
            market.owner_team_key
            == team_key
        )

        if (
            on_managed_team
            and market_state
            in {
                "free_agent",
                "waivers",
            }
        ):
            raise ThreeDaySnapshotError(
                "Managed-team player cannot "
                "also be available on market: "
                f"{key!r}."
            )

        row[
            "eligible_positions"
        ] = positions

        row[
            "market_state"
        ] = market_state

        row[
            "is_on_managed_team"
        ] = on_managed_team

    return enriched


def enrich_three_day_snapshot_percent_rostered(
    payload: dict[
        str,
        Any,
    ],
    *,
    percent_rostered_by_player_key: Mapping[
        str,
        int,
    ],
) -> dict[
    str,
    Any,
]:
    rows = payload.get(
        "rows"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise ThreeDaySnapshotError(
            "Snapshot rows must be a list "
            "before percent-rostered enrichment."
        )

    row_keys = [
        str(
            row.get(
                "provider_player_key",
                "",
            )
        )
        for row in rows
    ]

    if any(
        not key
        for key in row_keys
    ):
        raise ThreeDaySnapshotError(
            "Snapshot contains blank "
            "provider player keys."
        )

    if len(row_keys) != len(
        set(
            row_keys
        )
    ):
        raise ThreeDaySnapshotError(
            "Snapshot contains duplicate "
            "provider player keys."
        )

    percent_keys = {
        str(
            key
        )
        for key
        in percent_rostered_by_player_key
    }

    if percent_keys != set(
        row_keys
    ):
        raise ThreeDaySnapshotError(
            "Percent-rostered universe does not "
            "match snapshot rows."
        )

    enriched = copy.deepcopy(
        payload
    )

    for row in enriched[
        "rows"
    ]:
        key = str(
            row[
                "provider_player_key"
            ]
        )

        value = (
            percent_rostered_by_player_key[
                key
            ]
        )

        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                int,
            )
            or value < 0
            or value > 100
        ):
            raise ThreeDaySnapshotError(
                "percent_rostered must be an "
                "integer from 0 through 100 "
                f"for {key!r}."
            )

        row[
            "percent_rostered"
        ] = value

    return enriched

def build_three_day_snapshot_payload(
    *,
    rows: tuple[
        ThreeDayPlayerRanking,
        ...,
    ],
    league_name: str,
    team_name: str,
    model_label: str,
) -> dict[
    str,
    Any,
]:
    if not league_name.strip():
        raise ThreeDaySnapshotError(
            "league_name must not be blank."
        )

    if not team_name.strip():
        raise ThreeDaySnapshotError(
            "team_name must not be blank."
        )

    if not model_label.strip():
        raise ThreeDaySnapshotError(
            "model_label must not be blank."
        )

    if rows:
        base_date = (
            rows[0]
            .base_date
        )

        season_id = (
            rows[0]
            .season_id
        )

        for row in rows:
            if (
                row.base_date
                != base_date
            ):
                raise ThreeDaySnapshotError(
                    "Snapshot rows contained "
                    "different base dates."
                )

            if (
                row.season_id
                != season_id
            ):
                raise ThreeDaySnapshotError(
                    "Snapshot rows contained "
                    "different season IDs."
                )

        base_date_text = (
            base_date.isoformat()
        )

    else:
        base_date_text = None
        season_id = None

    payload_rows = []

    for row in rows:
        payload_rows.append(
            {
                "provider_player_key": (
                    row.provider_player_key
                ),
                "full_name": (
                    row.full_name
                ),
                "player_type": (
                    row.player_type
                ),
                "nhl_player_id": (
                    row.nhl_player_id
                ),
                "scheduled_games": (
                    row.scheduled_games
                ),
                "three_day_expected_points": (
                    row
                    .three_day_expected_fantasy_points
                ),
                "three_day_rank": (
                    row.three_day_rank
                ),
                "today": (
                    _day_payload(
                        row.today
                    )
                ),
                "tomorrow": (
                    _day_payload(
                        row.tomorrow
                    )
                ),
                "day_plus_2": (
                    _day_payload(
                        row.day_plus_2
                    )
                ),
            }
        )

    return {
        "schema_version": (
            SNAPSHOT_SCHEMA_VERSION
        ),
        "league_name": (
            league_name
        ),
        "team_name": (
            team_name
        ),
        "model_label": (
            model_label
        ),
        "base_date": (
            base_date_text
        ),
        "season_id": (
            season_id
        ),
        "rows": (
            payload_rows
        ),
    }


def write_three_day_snapshot(
    *,
    payload: dict[
        str,
        Any,
    ],
    path: str | Path,
) -> Path:
    target = Path(
        path
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = (
        target.with_suffix(
            target.suffix
            + ".tmp"
        )
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        target,
    )

    return target


def load_three_day_snapshot(
    path: str | Path,
) -> dict[
    str,
    Any,
]:
    source = Path(
        path
    )

    if not source.is_file():
        raise ThreeDaySnapshotError(
            "Three-day ranking snapshot "
            f"does not exist: {source}"
        )

    try:
        payload = json.loads(
            source.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise ThreeDaySnapshotError(
            "Unable to read three-day "
            "ranking snapshot."
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise ThreeDaySnapshotError(
            "Three-day ranking snapshot "
            "root must be an object."
        )

    if (
        payload.get(
            "schema_version"
        )
        != SNAPSHOT_SCHEMA_VERSION
    ):
        raise ThreeDaySnapshotError(
            "Unsupported three-day snapshot "
            "schema version."
        )

    rows = payload.get(
        "rows"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise ThreeDaySnapshotError(
            "Three-day ranking snapshot "
            "rows must be a list."
        )

    required_root = (
        "league_name",
        "team_name",
        "model_label",
        "base_date",
        "season_id",
    )

    for field in required_root:
        if field not in payload:
            raise ThreeDaySnapshotError(
                "Three-day ranking snapshot "
                f"missing root field {field!r}."
            )

    required_row = (
        "provider_player_key",
        "full_name",
        "player_type",
        "scheduled_games",
        "three_day_expected_points",
        "three_day_rank",
        "today",
        "tomorrow",
        "day_plus_2",
    )

    required_day = (
        "date",
        "team",
        "schedule_state",
        "value_state",
        "expected_points",
        "rank",
        "opponent",
        "home_away",
    )

    optional_market_fields = (
        "eligible_positions",
        "market_state",
        "is_on_managed_team",
    )

    optional_availability_fields = (
        "availability_state",
        "provider_status",
        "provider_status_full",
    )

    seen_keys = set()
    market_metadata_mode = None
    availability_metadata_mode = None
    percent_rostered_mode = None

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            raise ThreeDaySnapshotError(
                "Snapshot player row must "
                "be an object."
            )

        for field in required_row:
            if field not in row:
                raise ThreeDaySnapshotError(
                    "Snapshot player row "
                    f"missing {field!r}."
                )

        market_presence = tuple(
            field in row
            for field in optional_market_fields
        )

        if (
            any(market_presence)
            and not all(market_presence)
        ):
            raise ThreeDaySnapshotError(
                "Snapshot player row contains "
                "partial market metadata."
            )

        row_has_market = all(
            market_presence
        )

        if market_metadata_mode is None:
            market_metadata_mode = (
                row_has_market
            )

        elif (
            row_has_market
            != market_metadata_mode
        ):
            raise ThreeDaySnapshotError(
                "Snapshot rows contain mixed "
                "market metadata coverage."
            )

        if row_has_market:
            positions = row[
                "eligible_positions"
            ]

            if not isinstance(
                positions,
                list,
            ):
                raise ThreeDaySnapshotError(
                    "eligible_positions must "
                    "be a list."
                )

            if any(
                (
                    not isinstance(
                        position,
                        str,
                    )
                    or not position.strip()
                )
                for position in positions
            ):
                raise ThreeDaySnapshotError(
                    "eligible_positions must "
                    "contain nonblank strings."
                )

            if len(positions) != len(
                set(positions)
            ):
                raise ThreeDaySnapshotError(
                    "eligible_positions must "
                    "not contain duplicates."
                )

            market_state = row[
                "market_state"
            ]

            if (
                not isinstance(
                    market_state,
                    str,
                )
                or not market_state.strip()
            ):
                raise ThreeDaySnapshotError(
                    "market_state must be "
                    "a nonblank string."
                )

            if not isinstance(
                row[
                    "is_on_managed_team"
                ],
                bool,
            ):
                raise ThreeDaySnapshotError(
                    "is_on_managed_team must "
                    "be boolean."
                )

        availability_presence = tuple(
            field in row
            for field in optional_availability_fields
        )

        if (
            any(
                availability_presence
            )
            and not all(
                availability_presence
            )
        ):
            raise ThreeDaySnapshotError(
                "Snapshot player row contains "
                "partial availability metadata."
            )

        row_has_availability = all(
            availability_presence
        )

        if availability_metadata_mode is None:
            availability_metadata_mode = (
                row_has_availability
            )

        elif (
            row_has_availability
            != availability_metadata_mode
        ):
            raise ThreeDaySnapshotError(
                "Snapshot rows contain mixed "
                "availability metadata coverage."
            )

        if row_has_availability:
            availability_state = row[
                "availability_state"
            ]

            if availability_state not in {
                "available",
                "uncertain",
                "unavailable",
            }:
                raise ThreeDaySnapshotError(
                    "availability_state must be "
                    "available, uncertain, or "
                    "unavailable."
                )

            for status_field in (
                "provider_status",
                "provider_status_full",
            ):
                value = row[
                    status_field
                ]

                if (
                    value is not None
                    and not isinstance(
                        value,
                        str,
                    )
                ):
                    raise ThreeDaySnapshotError(
                        f"{status_field} must be "
                        "a string or null."
                    )

        has_percent_rostered = (
            "percent_rostered"
            in row
        )

        if percent_rostered_mode is None:
            percent_rostered_mode = (
                has_percent_rostered
            )

        elif (
            has_percent_rostered
            != percent_rostered_mode
        ):
            raise ThreeDaySnapshotError(
                "Snapshot rows contain mixed "
                "percent_rostered coverage."
            )

        if has_percent_rostered:
            percent_rostered = row[
                "percent_rostered"
            ]

            if (
                isinstance(
                    percent_rostered,
                    bool,
                )
                or not isinstance(
                    percent_rostered,
                    int,
                )
                or percent_rostered < 0
                or percent_rostered > 100
            ):
                raise ThreeDaySnapshotError(
                    "percent_rostered must be "
                    "an integer from 0 through 100."
                )

        key = str(
            row[
                "provider_player_key"
            ]
        )

        if key in seen_keys:
            raise ThreeDaySnapshotError(
                "Snapshot contained duplicate "
                "provider player key "
                f"{key!r}."
            )

        seen_keys.add(
            key
        )

        for day_name in (
            "today",
            "tomorrow",
            "day_plus_2",
        ):
            day = row[
                day_name
            ]

            if not isinstance(
                day,
                dict,
            ):
                raise ThreeDaySnapshotError(
                    f"{day_name} must be an object."
                )

            for field in required_day:
                if field not in day:
                    raise ThreeDaySnapshotError(
                        f"{day_name} missing "
                        f"{field!r}."
                    )

    return payload
