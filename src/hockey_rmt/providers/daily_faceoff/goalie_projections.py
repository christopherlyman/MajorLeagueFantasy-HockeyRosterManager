from __future__ import annotations

import csv
import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from hockey_rmt.domain.goalie_workload import (
    GoalieWorkloadProjection,
)


DAILY_FACEOFF_SOURCE = (
    "daily_faceoff"
)


class DailyFaceoffGoalieProjectionError(
    RuntimeError
):
    """Daily Faceoff goalie projection input was invalid."""


@dataclass(frozen=True)
class DailyFaceoffGoalieSnapshot:
    path: Path
    projection_season_id: int
    source_snapshot_date: date


_REQUIRED_COLUMNS = frozenset(
    {
        "Player",
        "Team",
        "Pos",
        "GS",
    }
)


# Provider vocabulary only.
#
# This maps the team labels Daily Faceoff
# currently emits to canonical NHL
# abbreviations. It is not a season roster
# or a hard-coded expected NHL team universe.
_TEAM_NAME_TO_NHL_ABBR = {
    "Avalanche": "COL",
    "Blackhawks": "CHI",
    "Blue Jackets": "CBJ",
    "Blues": "STL",
    "Bruins": "BOS",
    "Canadiens": "MTL",
    "Canucks": "VAN",
    "Capitals": "WSH",
    "Devils": "NJD",
    "Ducks": "ANA",
    "Flames": "CGY",
    "Flyers": "PHI",
    "Hurricanes": "CAR",
    "Islanders": "NYI",
    "Jets": "WPG",
    "Kings": "LAK",
    "Knights": "VGK",
    "Kraken": "SEA",
    "Lightning": "TBL",
    "Maple Leafs": "TOR",
    "Mammoth": "UTA",
    "Oilers": "EDM",
    "Panthers": "FLA",
    "Penguins": "PIT",
    "Predators": "NSH",
    "Rangers": "NYR",
    "Red Wings": "DET",
    "Sabres": "BUF",
    "Senators": "OTT",
    "Sharks": "SJS",
    "Stars": "DAL",
    "Utah": "UTA",
    "Wild": "MIN",
}


def discover_latest_goalie_snapshot(
    reference_root: str | Path,
    *,
    projection_season_id: int,
) -> DailyFaceoffGoalieSnapshot:
    root = Path(
        reference_root
    )

    season_directory = (
        root
        / DAILY_FACEOFF_SOURCE
        / str(
            int(
                projection_season_id
            )
        )
    )

    if not season_directory.is_dir():
        raise DailyFaceoffGoalieProjectionError(
            "No Daily Faceoff goalie "
            "projection directory exists "
            "for season "
            f"{projection_season_id}: "
            f"{season_directory}."
        )

    snapshots = []

    for path in sorted(
        season_directory.glob(
            "*.csv"
        )
    ):
        try:
            snapshot_date = (
                date.fromisoformat(
                    path.stem
                )
            )
        except ValueError as exc:
            raise DailyFaceoffGoalieProjectionError(
                "Daily Faceoff snapshot "
                "filename must be an ISO "
                "date such as YYYY-MM-DD.csv: "
                f"{path.name!r}."
            ) from exc

        snapshots.append(
            DailyFaceoffGoalieSnapshot(
                path=path,
                projection_season_id=int(
                    projection_season_id
                ),
                source_snapshot_date=(
                    snapshot_date
                ),
            )
        )

    if not snapshots:
        raise DailyFaceoffGoalieProjectionError(
            "No Daily Faceoff goalie "
            "projection snapshots were found "
            "for season "
            f"{projection_season_id}."
        )

    return max(
        snapshots,
        key=lambda snapshot: (
            snapshot.source_snapshot_date
        ),
    )


def _normalize_name(
    value: str,
) -> str:
    return " ".join(
        str(value).split()
    ).casefold()


def _parse_projected_starts(
    value: object,
    *,
    player_name: str,
) -> float:
    try:
        result = float(
            str(value).strip()
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise DailyFaceoffGoalieProjectionError(
            "Projected games started was "
            "not numeric for "
            f"{player_name!r}: {value!r}."
        ) from exc

    if not math.isfinite(
        result
    ):
        raise DailyFaceoffGoalieProjectionError(
            "Projected games started was "
            "not finite for "
            f"{player_name!r}."
        )

    if result < 0:
        raise DailyFaceoffGoalieProjectionError(
            "Projected games started was "
            "negative for "
            f"{player_name!r}: {result}."
        )

    return result


def load_goalie_workload_projections(
    snapshot: DailyFaceoffGoalieSnapshot,
    *,
    expected_team_games: Mapping[
        str,
        int,
    ],
) -> tuple[
    GoalieWorkloadProjection,
    ...,
]:
    if not (
        snapshot.path.is_file()
    ):
        raise DailyFaceoffGoalieProjectionError(
            "Daily Faceoff goalie projection "
            "file does not exist: "
            f"{snapshot.path}."
        )

    if not expected_team_games:
        raise DailyFaceoffGoalieProjectionError(
            "Expected NHL team schedule "
            "counts were not supplied."
        )

    canonical_expected_games = {}

    for (
        team_abbr,
        game_count,
    ) in expected_team_games.items():
        abbreviation = str(
            team_abbr
        ).strip().upper()

        if not abbreviation:
            raise DailyFaceoffGoalieProjectionError(
                "Expected NHL team "
                "abbreviation was empty."
            )

        count = int(
            game_count
        )

        if count <= 0:
            raise DailyFaceoffGoalieProjectionError(
                "Expected NHL regular-season "
                "game count must be positive "
                f"for {abbreviation}."
            )

        canonical_expected_games[
            abbreviation
        ] = count

    with snapshot.path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        if reader.fieldnames is None:
            raise DailyFaceoffGoalieProjectionError(
                "Daily Faceoff CSV had "
                "no header."
            )

        missing_columns = (
            _REQUIRED_COLUMNS
            - set(
                reader.fieldnames
            )
        )

        if missing_columns:
            raise DailyFaceoffGoalieProjectionError(
                "Daily Faceoff CSV was "
                "missing required columns: "
                + ", ".join(
                    sorted(
                        missing_columns
                    )
                )
            )

        rows = list(
            reader
        )

    if not rows:
        raise DailyFaceoffGoalieProjectionError(
            "Daily Faceoff CSV contained "
            "no goalie rows."
        )

    projections = []

    seen_players = set()

    starts_by_team = defaultdict(
        float
    )

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        full_name = " ".join(
            str(
                row.get("Player")
                or ""
            ).split()
        )

        if not full_name:
            raise DailyFaceoffGoalieProjectionError(
                "Daily Faceoff CSV row "
                f"{row_number} had no "
                "player name."
            )

        position = str(
            row.get("Pos")
            or ""
        ).strip()

        if position != "G":
            raise DailyFaceoffGoalieProjectionError(
                "Daily Faceoff goalie CSV "
                f"row {row_number} had "
                f"position {position!r}, "
                "expected 'G'."
            )

        source_team_name = " ".join(
            str(
                row.get("Team")
                or ""
            ).split()
        )

        try:
            nhl_team_abbr = (
                _TEAM_NAME_TO_NHL_ABBR[
                    source_team_name
                ]
            )
        except KeyError as exc:
            raise DailyFaceoffGoalieProjectionError(
                "Unrecognized Daily Faceoff "
                "team label on row "
                f"{row_number}: "
                f"{source_team_name!r}."
            ) from exc

        if (
            nhl_team_abbr
            not in canonical_expected_games
        ):
            raise DailyFaceoffGoalieProjectionError(
                "Daily Faceoff team "
                f"{nhl_team_abbr} is not in "
                "the canonical NHL team "
                "schedule for projection "
                f"season "
                f"{snapshot.projection_season_id}."
            )

        player_key = (
            _normalize_name(
                full_name
            )
        )

        if player_key in seen_players:
            raise DailyFaceoffGoalieProjectionError(
                "Duplicate Daily Faceoff "
                "goalie name: "
                f"{full_name!r}."
            )

        seen_players.add(
            player_key
        )

        projected_starts = (
            _parse_projected_starts(
                row.get("GS"),
                player_name=full_name,
            )
        )

        team_game_count = (
            canonical_expected_games[
                nhl_team_abbr
            ]
        )

        if (
            projected_starts
            > team_game_count
        ):
            raise DailyFaceoffGoalieProjectionError(
                "Projected games started "
                "exceeded the team's "
                "regular-season schedule for "
                f"{full_name!r}: "
                f"{projected_starts} > "
                f"{team_game_count}."
            )

        starts_by_team[
            nhl_team_abbr
        ] += projected_starts

        projections.append(
            GoalieWorkloadProjection(
                source=(
                    DAILY_FACEOFF_SOURCE
                ),
                source_snapshot_date=(
                    snapshot
                    .source_snapshot_date
                ),
                projection_season_id=(
                    snapshot
                    .projection_season_id
                ),
                full_name=full_name,
                nhl_team_abbr=(
                    nhl_team_abbr
                ),
                projected_games_started=(
                    projected_starts
                ),
            )
        )

    expected_teams = set(
        canonical_expected_games
    )

    actual_teams = set(
        starts_by_team
    )

    if actual_teams != expected_teams:
        raise DailyFaceoffGoalieProjectionError(
            "Daily Faceoff team coverage "
            "did not match the canonical "
            "NHL season schedule. "
            f"Missing="
            f"{sorted(expected_teams - actual_teams)}; "
            f"Extra="
            f"{sorted(actual_teams - expected_teams)}."
        )

    for team in sorted(
        expected_teams
    ):
        projected_starts = (
            starts_by_team[
                team
            ]
        )

        expected_games = float(
            canonical_expected_games[
                team
            ]
        )

        if not math.isclose(
            projected_starts,
            expected_games,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise DailyFaceoffGoalieProjectionError(
                "Daily Faceoff projected "
                "starts did not equal the "
                "official NHL regular-season "
                "schedule for "
                f"{team}: "
                f"{projected_starts} != "
                f"{expected_games}."
            )

    return tuple(
        sorted(
            projections,
            key=lambda projection: (
                projection.nhl_team_abbr,
                -projection
                .projected_games_started,
                projection.full_name,
            ),
        )
    )
