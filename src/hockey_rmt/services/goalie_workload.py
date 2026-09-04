from __future__ import annotations

from collections.abc import Sequence

from hockey_rmt.domain.goalie_workload import (
    GoalieSeasonWorkload,
)
from hockey_rmt.domain.nhl_roster import (
    CurrentNhlGoalie,
)


class GoalieWorkloadError(RuntimeError):
    """Goalie workload projection construction failed."""


def build_prior_season_starts_fallback(
    *,
    current_nhl_goalies: Sequence[
        CurrentNhlGoalie
    ],
    prior_season_workload: Sequence[
        GoalieSeasonWorkload
    ],
    expected_prior_season_id: int,
) -> dict[int, float]:
    current_ids = set()

    for goalie in current_nhl_goalies:
        if goalie.nhl_player_id in current_ids:
            raise GoalieWorkloadError(
                "Current NHL goalie appeared "
                "more than once: "
                f"{goalie.nhl_player_id}."
            )

        current_ids.add(
            goalie.nhl_player_id
        )

    prior_by_id = {}

    for row in prior_season_workload:
        if (
            row.season_id
            != int(
                expected_prior_season_id
            )
        ):
            raise GoalieWorkloadError(
                "Goalie workload season did not "
                "match expected prior season."
            )

        if (
            row.nhl_player_id
            in prior_by_id
        ):
            raise GoalieWorkloadError(
                "Prior-season workload contained "
                "duplicate NHL playerId "
                f"{row.nhl_player_id}."
            )

        if row.games_started < 0:
            raise GoalieWorkloadError(
                "Prior-season games started "
                "cannot be negative."
            )

        prior_by_id[
            row.nhl_player_id
        ] = float(
            row.games_started
        )

    return {
        goalie.nhl_player_id: (
            prior_by_id.get(
                goalie.nhl_player_id,
                0.0,
            )
        )
        for goalie in current_nhl_goalies
    }
