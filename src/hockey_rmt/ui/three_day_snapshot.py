from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any

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
    }


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

    seen_keys = set()

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
