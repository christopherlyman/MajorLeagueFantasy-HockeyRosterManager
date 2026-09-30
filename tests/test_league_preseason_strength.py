from datetime import date

import pytest

from hockey_rmt.domain.league import (
    LeagueDefinition,
    ScoringRule,
)
from hockey_rmt.domain.player_stats import (
    GoalieSeasonStats,
    SkaterSeasonStats,
)
from hockey_rmt.services import (
    preseason_strength,
)


def _league(
    *,
    goal_points: float,
    loss_points: float = 0.0,
    otl_points: float = 0.0,
) -> LeagueDefinition:
    weights = (
        ("G", goal_points),
        ("A", 2.5),
        ("PIM", 0.2),
        ("PPP", 1.0),
        ("SHP", 1.25),
        ("SOG", 0.25),
        ("HIT", 0.5),
        ("BLK", 0.5),
        ("W", 3.0),
        ("L", loss_points),
        ("OTL", otl_points),
        ("GA", -1.0),
        ("SV", 0.25),
        ("SHO", 2.5),
    )

    goalie = {
        "W",
        "L",
        "OTL",
        "GA",
        "SV",
        "SHO",
    }

    rules = tuple(
        ScoringRule(
            source_stat_id=index,
            name=abbr,
            abbreviation=abbr,
            group=(
                "goalie"
                if abbr in goalie
                else "skater"
            ),
            position_type=(
                "G"
                if abbr in goalie
                else "P"
            ),
            points=points,
        )
        for index, (
            abbr,
            points,
        ) in enumerate(
            weights,
            start=1,
        )
    )

    return LeagueDefinition(
        provider="test",
        provider_league_key="test",
        league_name="Test",
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
        scoring_rules=rules,
    )


def _skater(
    season_id: int,
) -> SkaterSeasonStats:
    return SkaterSeasonStats(
        nhl_player_id=1,
        full_name="Test Skater",
        season_id=season_id,
        games_played=1,
        goals=1,
        assists=0,
        penalty_minutes=0,
        power_play_points=0,
        short_handed_points=0,
        shots=0,
        hits=0,
        blocked_shots=0,
    )


def _goalie(
    season_id: int,
) -> GoalieSeasonStats:
    return GoalieSeasonStats(
        nhl_player_id=2,
        full_name="Test Goalie",
        season_id=season_id,
        games_played=1,
        wins=0,
        losses=1,
        overtime_losses=0,
        goals_against=0,
        saves=0,
        shutouts=0,
    )


def _capture_builder(
    monkeypatch,
):
    captured = {}

    def fake_builder(
        **kwargs,
    ):
        captured.update(
            kwargs
        )
        return ()

    monkeypatch.setattr(
        preseason_strength,
        "build_preseason_player_strengths",
        fake_builder,
    )

    return captured


def _invoke(
    *,
    monkeypatch,
    league,
):
    captured = _capture_builder(
        monkeypatch
    )

    season = 20242025

    result = (
        preseason_strength
        .build_league_preseason_player_strengths(
            league=league,
            projection_season_id=20262027,
            players=(),
            identity_resolutions=(),
            historical_skater_stats_by_season={
                season: (
                    _skater(
                        season
                    ),
                ),
            },
            historical_goalie_stats_by_season={
                season: (
                    _goalie(
                        season
                    ),
                ),
            },
            skater_bios_by_season={},
            profiles_by_nhl_id={},
            current_nhl_goalies=(),
        )
    )

    assert result == ()

    return captured


def test_same_raw_stats_use_supplied_league_scoring(
    monkeypatch,
):
    captured = _invoke(
        monkeypatch=monkeypatch,
        league=_league(
            goal_points=4.0,
        ),
    )

    values = {
        row.player_type: row
        for row in captured[
            "historical_values_by_season"
        ][20242025]
    }

    assert (
        values[
            "skater"
        ].fantasy_points
        == pytest.approx(4.0)
    )

    assert (
        values[
            "goalie"
        ].fantasy_points
        == pytest.approx(0.0)
    )


def test_different_league_changes_model_inputs(
    monkeypatch,
):
    captured = _invoke(
        monkeypatch=monkeypatch,
        league=_league(
            goal_points=5.0,
            loss_points=-1.5,
            otl_points=1.0,
        ),
    )

    values = {
        row.player_type: row
        for row in captured[
            "historical_values_by_season"
        ][20242025]
    }

    assert (
        values[
            "skater"
        ].fantasy_points
        == pytest.approx(5.0)
    )

    assert (
        values[
            "goalie"
        ].fantasy_points
        == pytest.approx(-1.5)
    )


def test_raw_stat_season_sets_must_match(
    monkeypatch,
):
    _capture_builder(
        monkeypatch
    )

    with pytest.raises(
        preseason_strength
        .PreseasonStrengthAssemblyError,
        match="season coverage",
    ):
        (
            preseason_strength
            .build_league_preseason_player_strengths(
                league=_league(
                    goal_points=4.0,
                ),
                projection_season_id=20262027,
                players=(),
                identity_resolutions=(),
                historical_skater_stats_by_season={
                    20242025: (
                        _skater(
                            20242025
                        ),
                    ),
                },
                historical_goalie_stats_by_season={},
                skater_bios_by_season={},
                profiles_by_nhl_id={},
                current_nhl_goalies=(),
            )
        )


def test_raw_stat_row_season_matches_mapping_key(
    monkeypatch,
):
    _capture_builder(
        monkeypatch
    )

    with pytest.raises(
        preseason_strength
        .PreseasonStrengthAssemblyError,
        match="mapping key",
    ):
        (
            preseason_strength
            .build_league_preseason_player_strengths(
                league=_league(
                    goal_points=4.0,
                ),
                projection_season_id=20262027,
                players=(),
                identity_resolutions=(),
                historical_skater_stats_by_season={
                    20242025: (
                        _skater(
                            20232024
                        ),
                    ),
                },
                historical_goalie_stats_by_season={
                    20242025: (
                        _goalie(
                            20242025
                        ),
                    ),
                },
                skater_bios_by_season={},
                profiles_by_nhl_id={},
                current_nhl_goalies=(),
            )
        )
