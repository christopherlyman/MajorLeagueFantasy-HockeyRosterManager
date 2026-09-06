from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

import requests

from hockey_rmt.domain.deployment import (
    DEPLOYMENT_SOURCE_DAILY_FACEOFF,
    DeploymentAssignment,
    SourcePlayerDeployment,
    SourceTeamDeploymentSnapshot,
)


DAILY_FACEOFF_BASE_URL = (
    "https://www.dailyfaceoff.com"
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/152.0 Safari/537.36"
    )
}


class DailyFaceoffDeploymentError(
    RuntimeError
):
    """Daily Faceoff deployment data was invalid."""


class _NextDataParser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__()
        self._in_target = False
        self._chunks: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:
        if tag.casefold() != "script":
            return

        values = dict(
            attrs
        )

        if values.get("id") == "__NEXT_DATA__":
            self._in_target = True

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._in_target:
            self._chunks.append(
                data
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag.casefold() == "script"
            and self._in_target
        ):
            self._in_target = False

    @property
    def payload_text(
        self,
    ) -> str:
        return "".join(
            self._chunks
        ).strip()


def _required_text(
    value: Any,
    *,
    field: str,
) -> str:
    result = str(
        value
        if value is not None
        else ""
    ).strip()

    if not result:
        raise DailyFaceoffDeploymentError(
            f"Daily Faceoff field {field!r} "
            "was empty."
        )

    return result


def _required_int(
    value: Any,
    *,
    field: str,
) -> int:
    try:
        result = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise DailyFaceoffDeploymentError(
            f"Daily Faceoff field {field!r} "
            "was not an integer."
        ) from exc

    return result


def _parse_timestamp(
    value: Any,
) -> datetime:
    text = _required_text(
        value,
        field="updatedAt",
    )

    if text.endswith("Z"):
        text = (
            text[:-1]
            + "+00:00"
        )

    try:
        result = (
            datetime.fromisoformat(
                text
            )
        )
    except ValueError as exc:
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff updatedAt was "
            "not valid ISO-8601."
        ) from exc

    if result.tzinfo is None:
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff updatedAt must "
            "include a timezone."
        )

    return result


def deployment_url(
    team_slug: str,
) -> str:
    slug = _required_text(
        team_slug,
        field="team_slug",
    )

    return (
        f"{DAILY_FACEOFF_BASE_URL}/"
        f"teams/{slug}/line-combinations"
    )


def parse_team_deployment_page(
    html_text: str,
) -> SourceTeamDeploymentSnapshot:
    parser = _NextDataParser()
    parser.feed(
        html_text
    )

    raw = parser.payload_text

    if not raw:
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff __NEXT_DATA__ "
            "payload was missing."
        )

    try:
        payload = json.loads(
            raw
        )
    except json.JSONDecodeError as exc:
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff __NEXT_DATA__ "
            "was not valid JSON."
        ) from exc

    try:
        combinations = (
            payload[
                "props"
            ][
                "pageProps"
            ][
                "combinations"
            ]
        )
    except (
        KeyError,
        TypeError,
    ) as exc:
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff combinations "
            "payload was missing."
        ) from exc

    if not isinstance(
        combinations,
        dict,
    ):
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff combinations "
            "payload was not an object."
        )

    team_abbreviation = _required_text(
        combinations.get(
            "teamAbbreviation"
        ),
        field="teamAbbreviation",
    )

    team_name = _required_text(
        combinations.get(
            "teamName"
        ),
        field="teamName",
    )

    team_slug = _required_text(
        combinations.get(
            "teamSlug"
        ),
        field="teamSlug",
    )

    source_name = _required_text(
        combinations.get(
            "sourceName"
        ),
        field="sourceName",
    )

    source_url = _required_text(
        combinations.get(
            "source"
        ),
        field="source",
    )

    updated_at = _parse_timestamp(
        combinations.get(
            "updatedAt"
        )
    )

    source_rows = combinations.get(
        "players"
    )

    if not isinstance(
        source_rows,
        list,
    ):
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff players payload "
            "was not a list."
        )

    if not source_rows:
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff players payload "
            "was empty."
        )

    identity_by_id: dict[
        int,
        str,
    ] = {}

    injury_statuses_by_id: dict[
        int,
        set[str],
    ] = defaultdict(
        set
    )

    game_time_decision_by_id: dict[
        int,
        bool,
    ] = defaultdict(
        bool
    )

    assignments_by_id: dict[
        int,
        list[
            DeploymentAssignment
        ],
    ] = defaultdict(
        list
    )

    assignment_keys_by_id: dict[
        int,
        set[
            tuple[
                str,
                str,
                str,
            ]
        ],
    ] = defaultdict(
        set
    )

    for row in source_rows:
        if not isinstance(
            row,
            dict,
        ):
            raise DailyFaceoffDeploymentError(
                "Daily Faceoff player row "
                "was not an object."
            )

        player_id = _required_int(
            row.get(
                "playerId"
            ),
            field="playerId",
        )

        full_name = _required_text(
            row.get(
                "name"
            ),
            field="name",
        )

        injury_raw = row.get(
            "injuryStatus"
        )

        if injury_raw in (
            None,
            "",
        ):
            injury_status = None
        else:
            injury_status = str(
                injury_raw
            ).strip()

        gtd_raw = row.get(
            "gameTimeDecision",
            False,
        )

        if not isinstance(
            gtd_raw,
            bool,
        ):
            raise DailyFaceoffDeploymentError(
                "Daily Faceoff "
                "gameTimeDecision was not "
                "boolean."
            )

        previous_name = (
            identity_by_id.get(
                player_id
            )
        )

        if (
            previous_name is not None
            and previous_name
            != full_name
        ):
            raise DailyFaceoffDeploymentError(
                "Daily Faceoff repeated player "
                "rows disagreed on name for "
                f"playerId {player_id}."
            )

        identity_by_id[
            player_id
        ] = full_name

        if injury_status is not None:
            injury_statuses_by_id[
                player_id
            ].add(
                injury_status
            )

            if (
                len(
                    injury_statuses_by_id[
                        player_id
                    ]
                )
                > 1
            ):
                raise DailyFaceoffDeploymentError(
                    "Daily Faceoff repeated player "
                    "rows contained conflicting "
                    "non-null injury statuses for "
                    f"playerId {player_id}: "
                    f"{sorted(injury_statuses_by_id[player_id])!r}."
                )

        game_time_decision_by_id[
            player_id
        ] = (
            game_time_decision_by_id[
                player_id
            ]
            or gtd_raw
        )

        category_identifier = (
            _required_text(
                row.get(
                    "categoryIdentifier"
                ),
                field=(
                    "categoryIdentifier"
                ),
            )
        )

        category_name = (
            _required_text(
                row.get(
                    "categoryName"
                ),
                field="categoryName",
            )
        )

        group_identifier = (
            _required_text(
                row.get(
                    "groupIdentifier"
                ),
                field="groupIdentifier",
            )
        )

        group_name = _required_text(
            row.get(
                "groupName"
            ),
            field="groupName",
        )

        position_identifier = (
            _required_text(
                row.get(
                    "positionIdentifier"
                ),
                field=(
                    "positionIdentifier"
                ),
            )
        )

        position_name = (
            _required_text(
                row.get(
                    "positionName"
                ),
                field="positionName",
            )
        )

        assignment_key = (
            category_identifier,
            group_identifier,
            position_identifier,
        )

        if (
            assignment_key
            in assignment_keys_by_id[
                player_id
            ]
        ):
            raise DailyFaceoffDeploymentError(
                "Daily Faceoff contained "
                "duplicate deployment assignment "
                f"for playerId {player_id}: "
                f"{assignment_key!r}."
            )

        assignment_keys_by_id[
            player_id
        ].add(
            assignment_key
        )

        assignments_by_id[
            player_id
        ].append(
            DeploymentAssignment(
                category_identifier=(
                    category_identifier
                ),
                category_name=(
                    category_name
                ),
                group_identifier=(
                    group_identifier
                ),
                group_name=(
                    group_name
                ),
                position_identifier=(
                    position_identifier
                ),
                position_name=(
                    position_name
                ),
            )
        )

    players = []

    for player_id in sorted(
        identity_by_id
    ):
        full_name = identity_by_id[
            player_id
        ]

        injury_values = (
            injury_statuses_by_id[
                player_id
            ]
        )

        if len(injury_values) > 1:
            raise DailyFaceoffDeploymentError(
                "Daily Faceoff player retained "
                "conflicting injury statuses for "
                f"playerId {player_id}."
            )

        injury_status = (
            next(
                iter(
                    injury_values
                )
            )
            if injury_values
            else None
        )

        gtd = (
            game_time_decision_by_id[
                player_id
            ]
        )

        assignments = tuple(
            sorted(
                assignments_by_id[
                    player_id
                ],
                key=lambda assignment: (
                    assignment
                    .category_identifier,
                    assignment
                    .group_identifier,
                    assignment
                    .position_identifier,
                ),
            )
        )

        if not assignments:
            raise DailyFaceoffDeploymentError(
                "Daily Faceoff player had no "
                "deployment assignments: "
                f"{player_id}."
            )

        players.append(
            SourcePlayerDeployment(
                source=(
                    DEPLOYMENT_SOURCE_DAILY_FACEOFF
                ),
                source_player_id=str(
                    player_id
                ),
                full_name=full_name,
                team_abbreviation=(
                    team_abbreviation
                ),
                injury_status=(
                    injury_status
                ),
                game_time_decision=gtd,
                assignments=assignments,
            )
        )

    return SourceTeamDeploymentSnapshot(
        source=(
            DEPLOYMENT_SOURCE_DAILY_FACEOFF
        ),
        team_abbreviation=(
            team_abbreviation
        ),
        team_name=team_name,
        team_slug=team_slug,
        source_name=source_name,
        source_updated_at=(
            updated_at
        ),
        source_url=source_url,
        players=tuple(
            players
        ),
    )


def fetch_team_deployment(
    team_slug: str,
    *,
    session: requests.Session | None = None,
    timeout_seconds: float = 30.0,
) -> SourceTeamDeploymentSnapshot:
    client = (
        session
        if session is not None
        else requests.Session()
    )

    response = client.get(
        deployment_url(
            team_slug
        ),
        timeout=float(
            timeout_seconds
        ),
        headers=(
            _DEFAULT_HEADERS
        ),
    )

    if response.status_code != 200:
        raise DailyFaceoffDeploymentError(
            "Daily Faceoff deployment page "
            "failed with HTTP "
            f"{response.status_code}."
        )

    return parse_team_deployment_page(
        response.text
    )
