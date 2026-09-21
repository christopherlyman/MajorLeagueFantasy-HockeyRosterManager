from __future__ import annotations

import unittest
from datetime import (
    date,
    datetime,
    timezone,
)
from types import SimpleNamespace

from hockey_rmt.domain.goalie_start import (
    GOALIE_START_CONFIRMED,
    GOALIE_START_SOURCE_DAILY_FACEOFF,
    DailyGoalieStartEvidence,
)
from hockey_rmt.services.goalie_start_identity import (
    GoalieStartIdentityError,
    build_goalie_starts_by_nhl_id,
    resolve_goalie_start_identities,
)


GAME_DATE = date(
    2026,
    3,
    14,
)


def _team(
    name: str,
    abbreviation: str,
):
    return SimpleNamespace(
        name=name,
        abbreviation=abbreviation,
    )


def _nhl_player(
    *,
    nhl_player_id: int,
    full_name: str,
    team_abbr: str,
    position: str = "G",
):
    return SimpleNamespace(
        nhl_player_id=nhl_player_id,
        full_name=full_name,
        team_abbr=team_abbr,
        position=position,
    )


def _start(
    *,
    provider_goalie_id: int = 2413,
    goalie_name: str = "Andrei Vasilevskiy",
    team_name: str = "Tampa Bay Lightning",
    opponent_team_name: str = "Carolina Hurricanes",
    game_date: date = GAME_DATE,
):
    return DailyGoalieStartEvidence(
        source=(
            GOALIE_START_SOURCE_DAILY_FACEOFF
        ),
        game_date=game_date,
        game_time_utc=datetime(
            2026,
            3,
            14,
            23,
            0,
            tzinfo=timezone.utc,
        ),
        is_home=True,
        provider_goalie_id=(
            provider_goalie_id
        ),
        goalie_name=goalie_name,
        provider_team_id=27,
        team_name=team_name,
        provider_opponent_team_id=6,
        opponent_team_name=(
            opponent_team_name
        ),
        start_state=(
            GOALIE_START_CONFIRMED
        ),
        evidence_created_at_utc=None,
        evidence_source_name=None,
        evidence_source_url=None,
    )


TEAMS = (
    _team(
        "Tampa Bay Lightning",
        "TBL",
    ),
    _team(
        "Carolina Hurricanes",
        "CAR",
    ),
    _team(
        "Boston Bruins",
        "BOS",
    ),
)


class GoalieStartIdentityTests(
    unittest.TestCase
):
    def test_exact_name_and_team_resolves(
        self,
    ):
        resolutions = (
            resolve_goalie_start_identities(
                goalie_starts=(
                    _start(),
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=8476883,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="TBL",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
            )
        )

        self.assertEqual(
            len(resolutions),
            1,
        )

        row = resolutions[0]

        self.assertEqual(
            row.resolution_state,
            "resolved",
        )
        self.assertEqual(
            row.resolution_method,
            "exact_name_team",
        )
        self.assertEqual(
            row.nhl_player_id,
            8476883,
        )
        self.assertEqual(
            row.nhl_team_abbr,
            "TBL",
        )

    def test_exact_name_wrong_team_is_unresolved(
        self,
    ):
        row = (
            resolve_goalie_start_identities(
                goalie_starts=(
                    _start(),
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=8476883,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="BOS",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
            )[0]
        )

        self.assertEqual(
            row.resolution_state,
            "unresolved",
        )
        self.assertIsNone(
            row.nhl_player_id
        )

    def test_non_goalie_exact_match_is_unresolved(
        self,
    ):
        row = (
            resolve_goalie_start_identities(
                goalie_starts=(
                    _start(),
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=1,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="TBL",
                        position="C",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
            )[0]
        )

        self.assertEqual(
            row.resolution_state,
            "unresolved",
        )

    def test_explicit_override_resolves_display_name_difference(
        self,
    ):
        row = (
            resolve_goalie_start_identities(
                goalie_starts=(
                    _start(
                        provider_goalie_id=99999,
                        goalie_name=(
                            "Provider Display Name"
                        ),
                    ),
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=8476883,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="TBL",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
                explicit_nhl_player_ids={
                    "99999": 8476883,
                },
            )[0]
        )

        self.assertEqual(
            row.resolution_state,
            "resolved",
        )
        self.assertEqual(
            row.resolution_method,
            "explicit_override",
        )
        self.assertEqual(
            row.nhl_player_id,
            8476883,
        )

    def test_override_team_mismatch_fails(
        self,
    ):
        with self.assertRaisesRegex(
            GoalieStartIdentityError,
            "override team did not match",
        ):
            resolve_goalie_start_identities(
                goalie_starts=(
                    _start(
                        provider_goalie_id=99999,
                    ),
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=8476883,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="BOS",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
                explicit_nhl_player_ids={
                    "99999": 8476883,
                },
            )

    def test_unknown_source_team_fails(
        self,
    ):
        with self.assertRaisesRegex(
            GoalieStartIdentityError,
            "could not be resolved",
        ):
            resolve_goalie_start_identities(
                goalie_starts=(
                    _start(
                        team_name=(
                            "Unknown Hockey Club"
                        ),
                    ),
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=8476883,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="TBL",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
            )

    def test_wrong_date_fails(
        self,
    ):
        with self.assertRaisesRegex(
            GoalieStartIdentityError,
            "did not match requested date",
        ):
            resolve_goalie_start_identities(
                goalie_starts=(
                    _start(
                        game_date=date(
                            2026,
                            3,
                            15,
                        ),
                    ),
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=8476883,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="TBL",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
            )

    def test_mapping_contains_only_resolved_rows(
        self,
    ):
        resolved = _start()

        unresolved = _start(
            provider_goalie_id=77777,
            goalie_name="Unknown Goalie",
            team_name=(
                "Carolina Hurricanes"
            ),
            opponent_team_name=(
                "Tampa Bay Lightning"
            ),
        )

        result = (
            build_goalie_starts_by_nhl_id(
                goalie_starts=(
                    resolved,
                    unresolved,
                ),
                nhl_players=(
                    _nhl_player(
                        nhl_player_id=8476883,
                        full_name=(
                            "Andrei Vasilevskiy"
                        ),
                        team_abbr="TBL",
                    ),
                ),
                nhl_teams=TEAMS,
                game_date=GAME_DATE,
            )
        )

        self.assertEqual(
            set(result),
            {
                8476883,
            },
        )
        self.assertIs(
            result[
                8476883
            ],
            resolved,
        )


if __name__ == "__main__":
    unittest.main()
