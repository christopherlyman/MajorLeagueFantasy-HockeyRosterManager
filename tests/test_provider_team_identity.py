import pytest

from hockey_rmt.domain.hockey_team import HockeyTeam
from hockey_rmt.domain.player import Player
from hockey_rmt.services.team_identity import (
    TeamIdentityError,
    build_provider_nhl_crosswalk,
)


def _player(
    *,
    provider: str,
    key: str,
) -> Player:
    return Player(
        provider=provider,
        provider_player_key=key,
        provider_player_id=key,
        full_name="Test Player",
        nhl_team_key="BOS",
        nhl_team_name="Boston Bruins",
        nhl_team_abbr="BOS",
        position_type="P",
        primary_position="C",
        eligible_positions=("C",),
        status=None,
        status_full=None,
        is_undroppable=False,
    )


def _nhl_team() -> HockeyTeam:
    return HockeyTeam(
        provider="nhl",
        provider_team_key=None,
        name="Boston Bruins",
        abbreviation="BOS",
    )


def test_fleaflicker_crosswalk_preserves_provider():
    result = build_provider_nhl_crosswalk(
        (
            _player(
                provider="fleaflicker",
                key="123",
            ),
        ),
        (
            _nhl_team(),
        ),
    )

    assert len(result) == 1
    assert (
        result[0].source_provider
        == "fleaflicker"
    )
    assert (
        result[0].canonical_team_abbr
        == "BOS"
    )


def test_yahoo_crosswalk_is_supported():
    result = build_provider_nhl_crosswalk(
        (
            _player(
                provider="yahoo",
                key="123",
            ),
        ),
        (
            _nhl_team(),
        ),
    )

    assert result[0].source_provider == "yahoo"


def test_mixed_provider_universe_fails_closed():
    with pytest.raises(
        TeamIdentityError,
        match="Conflicting provider team identity",
    ):
        build_provider_nhl_crosswalk(
            (
                _player(
                    provider="yahoo",
                    key="1",
                ),
                _player(
                    provider="fleaflicker",
                    key="2",
                ),
            ),
            (
                _nhl_team(),
            ),
        )
