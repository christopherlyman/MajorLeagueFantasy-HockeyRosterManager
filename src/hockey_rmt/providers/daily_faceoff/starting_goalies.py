from __future__ import annotations

import json
from datetime import date, datetime, timezone
from html.parser import HTMLParser

from hockey_rmt.domain.goalie_start import (
    GOALIE_START_CONFIRMED,
    GOALIE_START_LIKELY,
    GOALIE_START_SOURCE_DAILY_FACEOFF,
    GOALIE_START_UNCONFIRMED,
    DailyGoalieStartEvidence,
)


DAILY_FACEOFF_STARTING_GOALIES_BASE_URL = (
    "https://www.dailyfaceoff.com/starting-goalies"
)


class DailyFaceoffStartingGoaliesError(
    RuntimeError
):
    """Daily Faceoff starting-goalie input was invalid."""


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()

        self._in_next_data = False
        self.next_data_count = 0
        self.parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        if tag.casefold() != "script":
            return

        attributes = dict(attrs)

        if attributes.get("id") == "__NEXT_DATA__":
            self._in_next_data = True
            self.next_data_count += 1

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag.casefold() == "script"
            and self._in_next_data
        ):
            self._in_next_data = False

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._in_next_data:
            self.parts.append(data)


def starting_goalies_url(
    game_date: date,
) -> str:
    return (
        f"{DAILY_FACEOFF_STARTING_GOALIES_BASE_URL}/"
        f"{game_date.isoformat()}"
    )


def _required_text(
    value,
    *,
    label: str,
) -> str:
    text = " ".join(
        str(
            value
            if value is not None
            else ""
        ).split()
    )

    if not text:
        raise DailyFaceoffStartingGoaliesError(
            f"{label} was empty."
        )

    return text


def _optional_text(
    value,
) -> str | None:
    if value is None:
        return None

    text = " ".join(
        str(value).split()
    )

    return text or None


def _positive_int(
    value,
    *,
    label: str,
) -> int:
    try:
        result = int(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise DailyFaceoffStartingGoaliesError(
            f"{label} was not an integer."
        ) from exc

    if result <= 0:
        raise DailyFaceoffStartingGoaliesError(
            f"{label} must be positive."
        )

    return result


def _parse_datetime_utc(
    value,
    *,
    label: str,
    required: bool,
) -> datetime | None:
    text = _optional_text(
        value
    )

    if text is None:
        if required:
            raise DailyFaceoffStartingGoaliesError(
                f"{label} was empty."
            )

        return None

    normalized = text

    if normalized.endswith("Z"):
        normalized = (
            normalized[:-1]
            + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError as exc:
        raise DailyFaceoffStartingGoaliesError(
            f"{label} was not a valid ISO datetime."
        ) from exc

    if parsed.tzinfo is None:
        raise DailyFaceoffStartingGoaliesError(
            f"{label} did not include a timezone."
        )

    return parsed.astimezone(
        timezone.utc
    )


def _parse_start_state(
    value,
) -> str:
    text = _optional_text(
        value
    )

    if text is None:
        return GOALIE_START_UNCONFIRMED

    normalized = text.casefold()

    if normalized == "confirmed":
        return GOALIE_START_CONFIRMED

    if normalized == "likely":
        return GOALIE_START_LIKELY

    raise DailyFaceoffStartingGoaliesError(
        "Unrecognized Daily Faceoff goalie "
        f"strength/status {text!r}."
    )


def _next_data_payload(
    html_text: str,
) -> dict:
    if not isinstance(
        html_text,
        str,
    ):
        raise DailyFaceoffStartingGoaliesError(
            "Daily Faceoff page input "
            "must be text."
        )

    if not html_text.strip():
        raise DailyFaceoffStartingGoaliesError(
            "Daily Faceoff page input "
            "was empty."
        )

    parser = _NextDataParser()
    parser.feed(
        html_text
    )

    if parser.next_data_count != 1:
        raise DailyFaceoffStartingGoaliesError(
            "Expected exactly one "
            "__NEXT_DATA__ script; found "
            f"{parser.next_data_count}."
        )

    raw_json = "".join(
        parser.parts
    ).strip()

    if not raw_json:
        raise DailyFaceoffStartingGoaliesError(
            "__NEXT_DATA__ was empty."
        )

    try:
        payload = json.loads(
            raw_json
        )
    except json.JSONDecodeError as exc:
        raise DailyFaceoffStartingGoaliesError(
            "__NEXT_DATA__ was not valid JSON."
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise DailyFaceoffStartingGoaliesError(
            "__NEXT_DATA__ root was not "
            "an object."
        )

    return payload


def _game_rows(
    payload: dict,
) -> list:
    props = payload.get(
        "props"
    )

    if not isinstance(
        props,
        dict,
    ):
        raise DailyFaceoffStartingGoaliesError(
            "__NEXT_DATA__.props was not "
            "an object."
        )

    page_props = props.get(
        "pageProps"
    )

    if not isinstance(
        page_props,
        dict,
    ):
        raise DailyFaceoffStartingGoaliesError(
            "__NEXT_DATA__.props.pageProps "
            "was not an object."
        )

    rows = page_props.get(
        "data"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise DailyFaceoffStartingGoaliesError(
            "__NEXT_DATA__.props.pageProps.data "
            "was not a list."
        )

    return rows


def _parse_side(
    row: dict,
    *,
    side: str,
    game_date: date,
    game_time_utc: datetime,
) -> DailyGoalieStartEvidence | None:
    other_side = (
        "away"
        if side == "home"
        else "home"
    )

    goalie_id_value = row.get(
        f"{side}GoalieId"
    )
    goalie_name_value = row.get(
        f"{side}GoalieName"
    )

    goalie_id_missing = (
        goalie_id_value is None
    )
    goalie_name_missing = (
        _optional_text(
            goalie_name_value
        )
        is None
    )

    if (
        goalie_id_missing
        and goalie_name_missing
    ):
        return None

    if (
        goalie_id_missing
        != goalie_name_missing
    ):
        raise DailyFaceoffStartingGoaliesError(
            "Daily Faceoff goalie identity "
            f"was partial for {side} side."
        )

    goalie_id = _positive_int(
        goalie_id_value,
        label=f"{side}GoalieId",
    )

    goalie_name = _required_text(
        goalie_name_value,
        label=f"{side}GoalieName",
    )

    team_id = _positive_int(
        row.get(
            f"{side}TeamId"
        ),
        label=f"{side}TeamId",
    )

    team_name = _required_text(
        row.get(
            f"{side}TeamName"
        ),
        label=f"{side}TeamName",
    )

    opponent_team_id = _positive_int(
        row.get(
            f"{other_side}TeamId"
        ),
        label=f"{other_side}TeamId",
    )

    opponent_team_name = _required_text(
        row.get(
            f"{other_side}TeamName"
        ),
        label=f"{other_side}TeamName",
    )

    start_state = _parse_start_state(
        row.get(
            f"{side}NewsStrengthName"
        )
    )

    evidence_created_at = (
        _parse_datetime_utc(
            row.get(
                f"{side}NewsCreatedAt"
            ),
            label=f"{side}NewsCreatedAt",
            required=False,
        )
    )

    evidence_source_name = (
        _optional_text(
            row.get(
                f"{side}NewsSourceName"
            )
        )
    )

    evidence_source_url = (
        _optional_text(
            row.get(
                f"{side}NewsSourceUrl"
            )
        )
    )

    return DailyGoalieStartEvidence(
        source=(
            GOALIE_START_SOURCE_DAILY_FACEOFF
        ),
        game_date=game_date,
        game_time_utc=game_time_utc,
        is_home=(
            side == "home"
        ),
        provider_goalie_id=goalie_id,
        goalie_name=goalie_name,
        provider_team_id=team_id,
        team_name=team_name,
        provider_opponent_team_id=(
            opponent_team_id
        ),
        opponent_team_name=(
            opponent_team_name
        ),
        start_state=start_state,
        evidence_created_at_utc=(
            evidence_created_at
        ),
        evidence_source_name=(
            evidence_source_name
        ),
        evidence_source_url=(
            evidence_source_url
        ),
    )


def parse_starting_goalies_page(
    html_text: str,
    *,
    expected_date: date,
) -> tuple[
    DailyGoalieStartEvidence,
    ...,
]:
    payload = _next_data_payload(
        html_text
    )

    rows = _game_rows(
        payload
    )

    result = []
    seen_team_ids = set()

    for index, row in enumerate(
        rows,
        start=1,
    ):
        if not isinstance(
            row,
            dict,
        ):
            raise DailyFaceoffStartingGoaliesError(
                "Daily Faceoff game row "
                f"{index} was not an object."
            )

        raw_date = _required_text(
            row.get(
                "date"
            ),
            label=f"game row {index} date",
        )

        try:
            game_date = (
                date.fromisoformat(
                    raw_date
                )
            )
        except ValueError as exc:
            raise DailyFaceoffStartingGoaliesError(
                "Daily Faceoff game row "
                f"{index} had invalid date "
                f"{raw_date!r}."
            ) from exc

        if game_date != expected_date:
            raise DailyFaceoffStartingGoaliesError(
                "Daily Faceoff game row "
                f"{index} date {game_date} "
                "did not match requested date "
                f"{expected_date}."
            )

        game_time_utc = _parse_datetime_utc(
            row.get(
                "dateGmt"
            ),
            label=f"game row {index} dateGmt",
            required=True,
        )

        for side in (
            "home",
            "away",
        ):
            evidence = _parse_side(
                row,
                side=side,
                game_date=game_date,
                game_time_utc=(
                    game_time_utc
                ),
            )

            if evidence is None:
                continue

            team_key = (
                evidence.provider_team_id
            )

            if team_key in seen_team_ids:
                raise DailyFaceoffStartingGoaliesError(
                    "Daily Faceoff returned "
                    "multiple starting-goalie "
                    "records for teamId "
                    f"{team_key} on "
                    f"{expected_date}."
                )

            seen_team_ids.add(
                team_key
            )

            result.append(
                evidence
            )

    return tuple(
        result
    )
