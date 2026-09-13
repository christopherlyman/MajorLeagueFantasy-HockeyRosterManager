from __future__ import annotations

import json
import math
import os

from pathlib import Path
from typing import Any, Sequence

from hockey_rmt.domain.player_strength import (
    PlayerStrengthProjection,
)


PLAYER_STRENGTH_SNAPSHOT_SCHEMA_VERSION = 1


class PlayerStrengthSnapshotError(
    ValueError
):
    """Canonical player-strength persistence failed."""


def _nonblank_string(
    value: object,
    *,
    field: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise PlayerStrengthSnapshotError(
            f"{field} must be a string."
        )

    cleaned = value.strip()

    if not cleaned:
        raise PlayerStrengthSnapshotError(
            f"{field} must not be blank."
        )

    return cleaned


def _optional_nonblank_string(
    value: object,
    *,
    field: str,
) -> str | None:
    if value is None:
        return None

    return _nonblank_string(
        value,
        field=field,
    )


def _season_id(
    value: object,
    *,
    field: str,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise PlayerStrengthSnapshotError(
            f"{field} must be an integer."
        )

    if value <= 0:
        raise PlayerStrengthSnapshotError(
            f"{field} must be positive."
        )

    return value


def _optional_nhl_player_id(
    value: object,
) -> int | None:
    if value is None:
        return None

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value <= 0
    ):
        raise PlayerStrengthSnapshotError(
            "nhl_player_id must be a positive "
            "integer or null."
        )

    return value


def _optional_finite_float(
    value: object,
) -> float | None:
    if value is None:
        return None

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise PlayerStrengthSnapshotError(
            "projected_fantasy_points_per_game "
            "must be numeric or null."
        )

    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        raise PlayerStrengthSnapshotError(
            "projected_fantasy_points_per_game "
            "must be finite."
        )

    return result


def build_player_strength_snapshot_payload(
    *,
    rows: Sequence[
        PlayerStrengthProjection
    ],
    projection_season_id: int,
) -> dict[str, Any]:
    requested_season = _season_id(
        projection_season_id,
        field="projection_season_id",
    )

    payload_rows = []
    seen_keys = set()

    for row in rows:
        key = _nonblank_string(
            row.provider_player_key,
            field="provider_player_key",
        )

        if key in seen_keys:
            raise PlayerStrengthSnapshotError(
                "Duplicate provider player key "
                f"{key!r}."
            )

        seen_keys.add(
            key
        )

        row_season = _season_id(
            row.projection_season_id,
            field="row.projection_season_id",
        )

        if row_season != requested_season:
            raise PlayerStrengthSnapshotError(
                "Player-strength season mismatch "
                f"for {key!r}: "
                f"{row_season} != "
                f"{requested_season}."
            )

        payload_rows.append(
            {
                "provider_player_key": key,
                "full_name": (
                    _nonblank_string(
                        row.full_name,
                        field="full_name",
                    )
                ),
                "projection_season_id": (
                    row_season
                ),
                "player_type": (
                    _nonblank_string(
                        row.player_type,
                        field="player_type",
                    )
                ),
                "nhl_player_id": (
                    _optional_nhl_player_id(
                        row.nhl_player_id
                    )
                ),
                "strength_state": (
                    _nonblank_string(
                        row.strength_state,
                        field="strength_state",
                    )
                ),
                "projection_source": (
                    _optional_nonblank_string(
                        row.projection_source,
                        field="projection_source",
                    )
                ),
                "source_state": (
                    _optional_nonblank_string(
                        row.source_state,
                        field="source_state",
                    )
                ),
                "projected_fantasy_points_per_game": (
                    _optional_finite_float(
                        row
                        .projected_fantasy_points_per_game
                    )
                ),
            }
        )

    return {
        "schema_version": (
            PLAYER_STRENGTH_SNAPSHOT_SCHEMA_VERSION
        ),
        "projection_season_id": (
            requested_season
        ),
        "rows": payload_rows,
    }


def write_player_strength_snapshot(
    *,
    rows: Sequence[
        PlayerStrengthProjection
    ],
    projection_season_id: int,
    path: str | Path,
) -> Path:
    payload = (
        build_player_strength_snapshot_payload(
            rows=rows,
            projection_season_id=(
                projection_season_id
            ),
        )
    )

    target = Path(
        path
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = target.with_name(
        target.name
        + ".tmp"
    )

    serialized = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )

    temporary.write_text(
        serialized,
        encoding="utf-8",
    )

    os.replace(
        temporary,
        target,
    )

    return target


def load_player_strength_snapshot(
    path: str | Path,
    *,
    expected_projection_season_id: (
        int | None
    ) = None,
) -> tuple[
    PlayerStrengthProjection,
    ...,
]:
    source = Path(
        path
    )

    if not source.is_file():
        raise PlayerStrengthSnapshotError(
            "Player-strength snapshot does not "
            f"exist: {source}"
        )

    try:
        payload = json.loads(
            source.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise PlayerStrengthSnapshotError(
            "Unable to read player-strength "
            "snapshot."
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise PlayerStrengthSnapshotError(
            "Player-strength snapshot root "
            "must be an object."
        )

    if (
        payload.get(
            "schema_version"
        )
        != PLAYER_STRENGTH_SNAPSHOT_SCHEMA_VERSION
    ):
        raise PlayerStrengthSnapshotError(
            "Unsupported player-strength "
            "snapshot schema version."
        )

    projection_season_id = _season_id(
        payload.get(
            "projection_season_id"
        ),
        field="projection_season_id",
    )

    if (
        expected_projection_season_id
        is not None
    ):
        expected = _season_id(
            expected_projection_season_id,
            field=(
                "expected_projection_season_id"
            ),
        )

        if projection_season_id != expected:
            raise PlayerStrengthSnapshotError(
                "Player-strength snapshot season "
                f"{projection_season_id} != "
                f"expected {expected}."
            )

    raw_rows = payload.get(
        "rows"
    )

    if not isinstance(
        raw_rows,
        list,
    ):
        raise PlayerStrengthSnapshotError(
            "Player-strength snapshot rows "
            "must be a list."
        )

    result = []
    seen_keys = set()

    required_fields = (
        "provider_player_key",
        "full_name",
        "projection_season_id",
        "player_type",
        "nhl_player_id",
        "strength_state",
        "projection_source",
        "source_state",
        "projected_fantasy_points_per_game",
    )

    for raw in raw_rows:
        if not isinstance(
            raw,
            dict,
        ):
            raise PlayerStrengthSnapshotError(
                "Player-strength row must "
                "be an object."
            )

        for field in required_fields:
            if field not in raw:
                raise PlayerStrengthSnapshotError(
                    "Player-strength row missing "
                    f"{field!r}."
                )

        key = _nonblank_string(
            raw[
                "provider_player_key"
            ],
            field="provider_player_key",
        )

        if key in seen_keys:
            raise PlayerStrengthSnapshotError(
                "Duplicate provider player key "
                f"{key!r}."
            )

        seen_keys.add(
            key
        )

        row_season = _season_id(
            raw[
                "projection_season_id"
            ],
            field=(
                "row.projection_season_id"
            ),
        )

        if (
            row_season
            != projection_season_id
        ):
            raise PlayerStrengthSnapshotError(
                "Player-strength row season "
                f"mismatch for {key!r}."
            )

        result.append(
            PlayerStrengthProjection(
                provider_player_key=key,
                full_name=(
                    _nonblank_string(
                        raw[
                            "full_name"
                        ],
                        field="full_name",
                    )
                ),
                projection_season_id=(
                    row_season
                ),
                player_type=(
                    _nonblank_string(
                        raw[
                            "player_type"
                        ],
                        field="player_type",
                    )
                ),
                nhl_player_id=(
                    _optional_nhl_player_id(
                        raw[
                            "nhl_player_id"
                        ]
                    )
                ),
                strength_state=(
                    _nonblank_string(
                        raw[
                            "strength_state"
                        ],
                        field="strength_state",
                    )
                ),
                projection_source=(
                    _optional_nonblank_string(
                        raw[
                            "projection_source"
                        ],
                        field="projection_source",
                    )
                ),
                source_state=(
                    _optional_nonblank_string(
                        raw[
                            "source_state"
                        ],
                        field="source_state",
                    )
                ),
                projected_fantasy_points_per_game=(
                    _optional_finite_float(
                        raw[
                            "projected_fantasy_points_per_game"
                        ]
                    )
                ),
            )
        )

    return tuple(
        result
    )
