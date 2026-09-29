from __future__ import annotations

import unittest

from hockey_rmt.domain.hockey_team import (
    TeamIdentityCrosswalk,
)
from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    NhlPlayerIdentity,
)
from hockey_rmt.services.player_identity import (
    resolve_player_identities,
)


def _player(
    *,
    provider="fleaflicker",
    key,
    name,
    team_key=None,
    team_abbr=None,
    primary="C",
    eligibility=("C",),
):
    return Player(
        provider=provider,
        provider_player_key=key,
        provider_player_id=key,
        full_name=name,
        nhl_team_key=team_key,
        nhl_team_name=None,
        nhl_team_abbr=team_abbr,
        position_type="P",
        primary_position=primary,
        eligible_positions=eligibility,
        status=None,
        status_full=None,
        is_undroppable=None,
    )


def _nhl(
    *,
    player_id,
    name,
    position,
    team=None,
):
    return NhlPlayerIdentity(
        nhl_player_id=player_id,
        full_name=name,
        position=position,
        team_abbr=team,
        active=True,
        last_season_id=20252026,
    )


class ProviderNeutralPlayerIdentityTests(
    unittest.TestCase
):
    def test_unique_name_remains_provider_neutral(
        self,
    ):
        result = resolve_player_identities(
            players=(
                _player(
                    key="ff-1",
                    name="Unique Test",
                    team_abbr="BOS",
                ),
            ),
            nhl_players=(
                _nhl(
                    player_id=1,
                    name="Unique Test",
                    position="C",
                    team="BOS",
                ),
            ),
            team_crosswalk=(),
        )[0]

        self.assertEqual(
            result.resolution_state,
            "resolved",
        )
        self.assertEqual(
            result.resolution_method,
            "unique_name",
        )
        self.assertEqual(
            result.nhl_player_id,
            1,
        )

    def test_fleaflicker_team_abbreviation_disambiguates(
        self,
    ):
        result = resolve_player_identities(
            players=(
                _player(
                    key="ff-2",
                    name="Duplicate Test",
                    team_abbr="BOS",
                ),
            ),
            nhl_players=(
                _nhl(
                    player_id=2,
                    name="Duplicate Test",
                    position="C",
                    team="BOS",
                ),
                _nhl(
                    player_id=3,
                    name="Duplicate Test",
                    position="C",
                    team="TOR",
                ),
            ),
            team_crosswalk=(),
        )[0]

        self.assertEqual(
            result.resolution_state,
            "resolved",
        )
        self.assertEqual(
            result.resolution_method,
            "team_position",
        )
        self.assertEqual(
            result.nhl_player_id,
            2,
        )

    def test_composite_primary_uses_eligibility(
        self,
    ):
        result = resolve_player_identities(
            players=(
                _player(
                    key="ff-3",
                    name="Composite Test",
                    primary="C/LW",
                    eligibility=(
                        "C",
                        "LW",
                    ),
                ),
            ),
            nhl_players=(
                _nhl(
                    player_id=4,
                    name="Composite Test",
                    position="C",
                ),
                _nhl(
                    player_id=5,
                    name="Composite Test",
                    position="D",
                ),
            ),
            team_crosswalk=(),
        )[0]

        self.assertEqual(
            result.resolution_state,
            "resolved",
        )
        self.assertEqual(
            result.resolution_method,
            "position_within_name_group",
        )
        self.assertEqual(
            result.nhl_player_id,
            4,
        )

    def test_generic_w_uses_lw_rw_eligibility(
        self,
    ):
        result = resolve_player_identities(
            players=(
                _player(
                    key="ff-4",
                    name="Wing Test",
                    primary="W",
                    eligibility=(
                        "LW",
                        "RW",
                    ),
                ),
            ),
            nhl_players=(
                _nhl(
                    player_id=6,
                    name="Wing Test",
                    position="L",
                ),
                _nhl(
                    player_id=7,
                    name="Wing Test",
                    position="D",
                ),
            ),
            team_crosswalk=(),
        )[0]

        self.assertEqual(
            result.resolution_state,
            "resolved",
        )
        self.assertEqual(
            result.resolution_method,
            "position_within_name_group",
        )
        self.assertEqual(
            result.nhl_player_id,
            6,
        )

    def test_yahoo_team_crosswalk_still_resolves(
        self,
    ):
        result = resolve_player_identities(
            players=(
                _player(
                    provider="yahoo",
                    key="477.p.test",
                    name="Yahoo Crosswalk Test",
                    team_key="nhl.t.1",
                    team_abbr=None,
                    primary="C",
                    eligibility=(
                        "C",
                        "F",
                        "Util",
                    ),
                ),
            ),
            nhl_players=(
                _nhl(
                    player_id=8,
                    name="Yahoo Crosswalk Test",
                    position="C",
                    team="BOS",
                ),
                _nhl(
                    player_id=9,
                    name="Yahoo Crosswalk Test",
                    position="C",
                    team="TOR",
                ),
            ),
            team_crosswalk=(
                TeamIdentityCrosswalk(
                    source_provider="yahoo",
                    source_team_key="nhl.t.1",
                    source_team_abbr="BOS",
                    canonical_team_name=(
                        "Boston Bruins"
                    ),
                    canonical_team_abbr="BOS",
                ),
            ),
        )[0]

        self.assertEqual(
            result.resolution_state,
            "resolved",
        )
        self.assertEqual(
            result.resolution_method,
            "team_position",
        )
        self.assertEqual(
            result.nhl_player_id,
            8,
        )

    def test_simple_primary_preserves_yahoo_position_preference(
        self,
    ):
        result = resolve_player_identities(
            players=(
                _player(
                    provider="yahoo",
                    key="477.p.test2",
                    name="Yahoo Position Test",
                    primary="C",
                    eligibility=(
                        "C",
                        "LW",
                        "F",
                        "Util",
                    ),
                ),
            ),
            nhl_players=(
                _nhl(
                    player_id=10,
                    name="Yahoo Position Test",
                    position="C",
                ),
                _nhl(
                    player_id=11,
                    name="Yahoo Position Test",
                    position="L",
                ),
            ),
            team_crosswalk=(),
        )[0]

        self.assertEqual(
            result.resolution_state,
            "resolved",
        )
        self.assertEqual(
            result.resolution_method,
            "position_within_name_group",
        )
        self.assertEqual(
            result.nhl_player_id,
            10,
        )


if __name__ == "__main__":
    unittest.main()
