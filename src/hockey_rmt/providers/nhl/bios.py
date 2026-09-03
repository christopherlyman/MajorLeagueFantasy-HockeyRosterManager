from __future__ import annotations

from datetime import date
from typing import Any, Mapping

import requests

from hockey_rmt.domain.skater_bio import SkaterBio


STATS_BASE_URL = "https://api.nhle.com/stats/rest/en"


class NhlBiosError(RuntimeError):
    """Official NHL bios retrieval failed."""


def _required_value(
    row: Mapping[str, Any],
    field: str,
) -> Any:
    if field not in row:
        raise NhlBiosError(
            f"NHL bios row missing required field "
            f"{field!r}."
        )

    value = row[field]

    if value is None:
        raise NhlBiosError(
            f"NHL bios row contained null required "
            f"field {field!r}."
        )

    return value


def _required_int(
    row: Mapping[str, Any],
    field: str,
) -> int:
    value = _required_value(
        row,
        field,
    )

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NhlBiosError(
            f"NHL bios field {field!r} was not "
            f"an integer: {value!r}."
        ) from exc


def _optional_int(
    row: Mapping[str, Any],
    field: str,
) -> int | None:
    value = row.get(field)

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NhlBiosError(
            f"NHL bios field {field!r} was not "
            f"an integer: {value!r}."
        ) from exc


def fetch_skater_bios(
    *,
    season_id: int,
    game_type_id: int = 2,
    timeout_seconds: float = 60.0,
) -> tuple[SkaterBio, ...]:
    response = requests.get(
        f"{STATS_BASE_URL}/skater/bios",
        params={
            "isAggregate": "true",
            "isGame": "false",
            "start": 0,
            "limit": -1,
            "sort": "playerId",
            "dir": "asc",
            "cayenneExp": (
                f"seasonId={season_id} "
                f"and gameTypeId={game_type_id}"
            ),
        },
        timeout=timeout_seconds,
    )

    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise NhlBiosError(
            "NHL bios response was not valid JSON."
        ) from exc

    rows = payload.get("data")

    if not isinstance(rows, list):
        raise NhlBiosError(
            "NHL bios response did not contain "
            "a data list."
        )

    total = payload.get("total")

    try:
        reported_total = int(total)
    except (TypeError, ValueError) as exc:
        raise NhlBiosError(
            "NHL bios response did not contain "
            "a valid total."
        ) from exc

    if len(rows) != reported_total:
        raise NhlBiosError(
            "NHL bios row count did not match "
            "reported total: "
            f"rows={len(rows)}, "
            f"total={reported_total}."
        )

    result = []
    seen_ids = set()
    previous_id = None

    for row in rows:
        if not isinstance(row, Mapping):
            raise NhlBiosError(
                "NHL bios data contained a "
                "non-object row."
            )

        player_id = _required_int(
            row,
            "playerId",
        )

        if player_id in seen_ids:
            raise NhlBiosError(
                "Duplicate NHL playerId in bios "
                f"response: {player_id}."
            )

        if (
            previous_id is not None
            and player_id <= previous_id
        ):
            raise NhlBiosError(
                "NHL bios response was not strictly "
                "sorted by playerId ascending."
            )

        seen_ids.add(player_id)
        previous_id = player_id

        birth_date_text = str(
            _required_value(
                row,
                "birthDate",
            )
        )

        try:
            birth_date = date.fromisoformat(
                birth_date_text
            )
        except ValueError as exc:
            raise NhlBiosError(
                "Invalid NHL bios birthDate for "
                f"playerId {player_id}: "
                f"{birth_date_text!r}."
            ) from exc

        result.append(
            SkaterBio(
                nhl_player_id=player_id,
                full_name=str(
                    _required_value(
                        row,
                        "skaterFullName",
                    )
                ),
                birth_date=birth_date,
                position_code=str(
                    _required_value(
                        row,
                        "positionCode",
                    )
                ),
                shoots_catches=(
                    None
                    if row.get("shootsCatches") is None
                    else str(row["shootsCatches"])
                ),
                height_inches=_required_int(
                    row,
                    "height",
                ),
                weight_pounds=_required_int(
                    row,
                    "weight",
                ),
                nationality_code=str(
                    _required_value(
                        row,
                        "nationalityCode",
                    )
                ),
                first_season_for_game_type=(
                    _required_int(
                        row,
                        "firstSeasonForGameType",
                    )
                ),
                draft_year=_optional_int(
                    row,
                    "draftYear",
                ),
                draft_round=_optional_int(
                    row,
                    "draftRound",
                ),
                draft_overall=_optional_int(
                    row,
                    "draftOverall",
                ),
            )
        )

    return tuple(result)
