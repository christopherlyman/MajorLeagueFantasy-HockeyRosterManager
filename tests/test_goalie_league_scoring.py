from datetime import date

import pytest

from hockey_rmt.domain.league import (
    LeagueDefinition,
    ScoringRule,
)
from hockey_rmt.domain.player_stats import (
    GoalieSeasonStats,
)
from hockey_rmt.providers.nhl import stats as nhl_stats
from hockey_rmt.services.fantasy_value import (
    FantasyValueError,
    score_goalie,
)


SKATER_ZERO_RULES = (
    ("G", 0.0),
    ("A", 0.0),
    ("PIM", 0.0),
    ("PPP", 0.0),
    ("SHP", 0.0),
    ("SOG", 0.0),
    ("HIT", 0.0),
    ("BLK", 0.0),
)


def _league(
    goalie_rules: tuple[
        tuple[str, float],
        ...,
    ],
) -> LeagueDefinition:
    rules = []

    for index, (
        abbreviation,
        points,
    ) in enumerate(
        SKATER_ZERO_RULES
        + goalie_rules,
        start=1,
    ):
        rules.append(
            ScoringRule(
                source_stat_id=index,
                name=abbreviation,
                abbreviation=abbreviation,
                group=(
                    "goalie"
                    if abbreviation
                    in {
                        "W",
                        "L",
                        "OTL",
                        "GA",
                        "SV",
                        "SO",
                        "SHO",
                    }
                    else "skater"
                ),
                position_type=(
                    "G"
                    if abbreviation
                    in {
                        "W",
                        "L",
                        "OTL",
                        "GA",
                        "SV",
                        "SO",
                        "SHO",
                    }
                    else "P"
                ),
                points=points,
            )
        )

    return LeagueDefinition(
        provider="test",
        provider_league_key="test",
        league_name="Test League",
        sport="NHL",
        season_year=2026,
        max_teams=14,
        scoring_format="points",
        roster_period="daily",
        lineup_deadline="game_time",
        start_date=date(2026, 9, 29),
        end_date=date(2027, 4, 18),
        max_weekly_adds=7,
        waiver_type="test",
        waiver_rule="test",
        waiver_days=None,
        uses_faab=False,
        playoff_teams=None,
        playoff_start_week=None,
        roster_positions=(),
        scoring_rules=tuple(rules),
    )


def _goalie(
    *,
    losses: int | None,
    overtime_losses: int | None,
) -> GoalieSeasonStats:
    return GoalieSeasonStats(
        nhl_player_id=1,
        full_name="Test Goalie",
        season_id=20252026,
        games_played=20,
        wins=10,
        goals_against=40,
        saves=500,
        shutouts=3,
        losses=losses,
        overtime_losses=overtime_losses,
    )


def test_nfhl_goalie_scoring_remains_unchanged_without_l_or_otl():
    league = _league(
        (
            ("W", 3.0),
            ("GA", -1.0),
            ("SV", 0.25),
            ("SHO", 2.5),
        )
    )

    value = score_goalie(
        _goalie(
            losses=None,
            overtime_losses=None,
        ),
        league,
    )

    assert value.fantasy_points == pytest.approx(
        122.5
    )
    assert (
        value.fantasy_points_per_game
        == pytest.approx(6.125)
    )

    components = {
        row.category: row
        for row in value.components
    }

    assert components["L"].points_per_unit == 0.0
    assert components["L"].fantasy_points == 0.0
    assert components["OTL"].points_per_unit == 0.0
    assert components["OTL"].fantasy_points == 0.0


def test_oth_goalie_scoring_supports_l_otl_and_so_alias():
    league = _league(
        (
            ("W", 3.0),
            ("L", -1.5),
            ("OTL", 1.0),
            ("SO", 2.5),
            ("SV", 0.25),
            ("GA", -1.0),
        )
    )

    value = score_goalie(
        _goalie(
            losses=5,
            overtime_losses=2,
        ),
        league,
    )

    assert value.fantasy_points == pytest.approx(
        117.0
    )
    assert (
        value.fantasy_points_per_game
        == pytest.approx(5.85)
    )

    components = {
        row.category: row
        for row in value.components
    }

    assert components["L"].fantasy_points == pytest.approx(
        -7.5
    )
    assert components["OTL"].fantasy_points == pytest.approx(
        2.0
    )
    assert components["SHO"].fantasy_points == pytest.approx(
        7.5
    )
    assert "SO" not in components


def test_scored_missing_goalie_result_evidence_fails_closed():
    league = _league(
        (
            ("W", 3.0),
            ("L", -1.5),
            ("OTL", 1.0),
            ("SO", 2.5),
            ("SV", 0.25),
            ("GA", -1.0),
        )
    )

    with pytest.raises(
        FantasyValueError,
        match="L",
    ):
        score_goalie(
            _goalie(
                losses=None,
                overtime_losses=2,
            ),
            league,
        )


def test_nhl_goalie_summary_ingests_losses_and_ot_losses(
    monkeypatch,
):
    provider_row = {
        "playerId": 8470000,
        "goalieFullName": "Provider Goalie",
        "seasonId": 20252026,
        "gamesPlayed": 59,
        "wins": 28,
        "losses": 22,
        "otLosses": 8,
        "goalsAgainst": 181,
        "saves": 1519,
        "shutouts": 0,
    }

    monkeypatch.setattr(
        nhl_stats,
        "_fetch_report",
        lambda *args, **kwargs: [
            provider_row
        ],
    )

    result = nhl_stats.fetch_goalie_season_stats(
        season_id=20252026,
    )

    assert len(result) == 1
    assert result[0].wins == 28
    assert result[0].losses == 22
    assert result[0].overtime_losses == 8
    assert result[0].shutouts == 0
