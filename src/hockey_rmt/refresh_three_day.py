from __future__ import annotations

import argparse
import os

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from hockey_rmt.domain.performance_trend import (
    WINDOW_LAST_10,
    WINDOW_LAST_20,
    WINDOW_SEASON,
)
from hockey_rmt.providers.daily_faceoff.deployment import (
    DailyFaceoffDeploymentError,
    fetch_team_deployment,
    team_slug_for_nhl_abbr,
)
from hockey_rmt.providers.daily_faceoff.starting_goalies import (
    DailyFaceoffStartingGoaliesError,
    fetch_starting_goalies,
)
from hockey_rmt.providers.moneypuck.skater_trends import (
    MoneyPuckSkaterTrendError,
    fetch_skater_performance_trends,
)
from hockey_rmt.providers.nhl.client import NhlClient
from hockey_rmt.providers.nhl.player_search import (
    fetch_player_registry,
)
from hockey_rmt.providers.nhl.stats import (
    fetch_skater_season_stats,
)
from hockey_rmt.providers.nhl.schedule import (
    fetch_schedule,
)
from hockey_rmt.providers.nhl.teams import (
    fetch_current_teams,
)
from hockey_rmt.providers.yahoo.auth import (
    get_access_token,
)
from hockey_rmt.providers.yahoo.client import (
    YahooClient,
)
from hockey_rmt.providers.yahoo.league import (
    fetch_league_definition,
)
from hockey_rmt.providers.yahoo.ownership import (
    fetch_all_player_market_states,
)
from hockey_rmt.providers.yahoo.percent_rostered import (
    fetch_all_player_percent_rostered,
)
from hockey_rmt.providers.yahoo.player_pool import (
    fetch_all_players,
)
from hockey_rmt.services.current_state_evidence import (
    build_current_state_projection_adjustments,
)
from hockey_rmt.services.goalie_start_identity import (
    build_goalie_starts_by_nhl_id,
)
from hockey_rmt.providers.yahoo.teams import (
    fetch_league_teams,
)
from hockey_rmt.services.market_decision import (
    build_market_decisions,
    market_decision_result_payload,
)
from hockey_rmt.services.lineup_optimizer import (
    build_roster_position_snapshot,
)
from hockey_rmt.services.daily_refresh import (
    build_three_day_refresh_payload,
)
from hockey_rmt.services.fantasy_value import (
    score_historical_season,
)
from hockey_rmt.services.player_strength_snapshot import (
    load_player_strength_snapshot,
)
from hockey_rmt.ui.three_day_snapshot import (
    load_three_day_snapshot,
    write_three_day_snapshot,
)


LEAGUE_KEY = "477.l.10961"
MANAGED_TEAM_KEY = "477.l.10961.t.1"
TEAM_NAME = "Drop The Gloves"

PROJECTION_SEASON_ID = 20262027

SEASON_START = date(
    2026,
    9,
    29,
)

MODEL_LABEL = (
    "CANONICAL 2026-27 — "
    "established-skater historical/age calibration; "
    "rookie age/draft-capital model; "
    "long-absence population prior; "
    "goalie historical quality/workload. "
    "Yahoo availability applied. "
    "Bounded skater current-state adjustments "
    "use Daily Faceoff deployment, official NHL "
    "current-season production, and MoneyPuck "
    "role/process trends when available. "
    "Daily Faceoff confirmed starting-goalie "
    "evidence gates goalie daily value. "
    "Matchup adjustment is not yet applied."
)


def _project_root() -> Path:
    return (
        Path(
            __file__
        )
        .resolve()
        .parents[
            2
        ]
    )


def _default_base_date() -> date:
    today = (
        datetime.now(
            ZoneInfo(
                "America/New_York"
            )
        )
        .date()
    )

    return max(
        today,
        SEASON_START,
    )


def _parse_date(
    value: str,
) -> date:
    try:
        return date.fromisoformat(
            value
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "base date must be YYYY-MM-DD"
        ) from exc


def _schedule_union(
    client: NhlClient,
    *,
    base_date: date,
) -> tuple[
    object,
    ...,
]:
    games_by_id = {}

    for offset in range(
        3
    ):
        anchor = (
            base_date
            + timedelta(
                days=offset
            )
        )

        games = fetch_schedule(
            client,
            anchor,
        )

        for game in games:
            key = str(
                game.provider_game_id
            )

            existing = games_by_id.get(
                key
            )

            if (
                existing is not None
                and existing != game
            ):
                raise RuntimeError(
                    "NHL schedule returned "
                    "conflicting records for "
                    f"{key!r}."
                )

            games_by_id[
                key
            ] = game

    return tuple(
        games_by_id.values()
    )



def _today_new_york() -> date:
    return (
        datetime.now(
            ZoneInfo(
                "America/New_York"
            )
        )
        .date()
    )


def _fetch_current_season_values(
    *,
    league,
    actual_date: date,
):
    if actual_date < SEASON_START:
        return (
            (),
            "preseason_no_sample",
            0,
        )

    skaters = fetch_skater_season_stats(
        season_id=PROJECTION_SEASON_ID,
    )

    values = score_historical_season(
        skaters=skaters,
        goalies=(),
        league=league,
    )

    return (
        values,
        "available",
        len(skaters),
    )


def _fetch_current_moneypuck_trends(
    *,
    actual_date: date,
):
    if actual_date < SEASON_START:
        return (
            (),
            "preseason_no_sample",
        )

    rows = []

    for window in (
        WINDOW_SEASON,
        WINDOW_LAST_20,
        WINDOW_LAST_10,
    ):
        try:
            rows.extend(
                fetch_skater_performance_trends(
                    season_id=(
                        PROJECTION_SEASON_ID
                    ),
                    window=window,
                )
            )
        except MoneyPuckSkaterTrendError:
            return (
                (),
                f"unavailable:{window}",
            )

    return (
        tuple(rows),
        "available",
    )


def _fetch_deployment_snapshots(
    *,
    nhl_teams,
):
    snapshots = []
    failed_teams = []

    abbreviations = [
        str(
            team.abbreviation
        ).strip().upper()
        for team in nhl_teams
    ]

    if any(
        not abbreviation
        for abbreviation in abbreviations
    ):
        raise RuntimeError(
            "Current NHL team had an empty "
            "abbreviation."
        )

    if len(abbreviations) != len(
        set(abbreviations)
    ):
        raise RuntimeError(
            "Current NHL team universe contained "
            "duplicate abbreviations."
        )

    for abbreviation in sorted(
        abbreviations
    ):
        slug = team_slug_for_nhl_abbr(
            abbreviation
        )

        try:
            snapshot = fetch_team_deployment(
                slug
            )
        except DailyFaceoffDeploymentError:
            failed_teams.append(
                abbreviation
            )
            continue

        source_team = str(
            snapshot.team_abbreviation
        ).strip().upper()

        if source_team != abbreviation:
            raise RuntimeError(
                "Daily Faceoff deployment response "
                "team did not match requested NHL "
                f"team: requested={abbreviation!r}, "
                f"returned={source_team!r}."
            )

        snapshots.append(
            snapshot
        )

    return (
        tuple(snapshots),
        tuple(failed_teams),
    )


def _fetch_goalie_start_mappings(
    *,
    base_date: date,
    nhl_player_registry,
    nhl_teams,
):
    result = {}

    for offset in range(
        3
    ):
        game_date = (
            base_date
            + timedelta(
                days=offset
            )
        )

        try:
            evidence = (
                fetch_starting_goalies(
                    game_date
                )
            )
        except DailyFaceoffStartingGoaliesError as exc:
            raise RuntimeError(
                "Daily Faceoff starting-goalie "
                "evidence failed for required "
                f"date {game_date.isoformat()}."
            ) from exc

        resolved = (
            build_goalie_starts_by_nhl_id(
                goalie_starts=evidence,
                nhl_players=(
                    nhl_player_registry
                ),
                nhl_teams=nhl_teams,
                game_date=game_date,
            )
        )

        result[
            game_date
        ] = resolved

    expected_dates = {
        base_date
        + timedelta(
            days=offset
        )
        for offset in range(
            3
        )
    }

    if set(result) != expected_dates:
        raise RuntimeError(
            "Starting-goalie refresh did not "
            "produce exact three-day coverage."
        )

    return result


def main() -> int:
    root = _project_root()

    parser = argparse.ArgumentParser(
        description=(
            "Refresh the NFHL availability-aware "
            "three-day decision snapshot."
        )
    )

    parser.add_argument(
        "--base-date",
        type=_parse_date,
        default=_default_base_date(),
    )

    parser.add_argument(
        "--strength-artifact",
        type=Path,
        default=(
            root
            / "data/runtime/"
              "player_strengths_20262027.json"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            root
            / "data/runtime/"
              "three_day_rankings.json"
        ),
    )

    args = parser.parse_args()

    required_env = (
        "POSTGRES_DSN",
        "YAHOO_CLIENT_ID",
        "YAHOO_CLIENT_SECRET",
    )

    missing = [
        name
        for name in required_env
        if not str(
            os.environ.get(
                name,
                ""
            )
        ).strip()
    ]

    if missing:
        raise RuntimeError(
            "Missing required environment "
            "variables: "
            + ", ".join(
                missing
            )
        )

    strengths = (
        load_player_strength_snapshot(
            args.strength_artifact,
            expected_projection_season_id=(
                PROJECTION_SEASON_ID
            ),
        )
    )

    token = get_access_token(
        dsn=os.environ[
            "POSTGRES_DSN"
        ],
        client_id=os.environ[
            "YAHOO_CLIENT_ID"
        ],
        client_secret=os.environ[
            "YAHOO_CLIENT_SECRET"
        ],
        token_key="mlf_tools",
    )

    yahoo = YahooClient(
        token
    )

    league = (
        fetch_league_definition(
            yahoo,
            LEAGUE_KEY,
        )
    )

    fantasy_teams = (
        fetch_league_teams(
            yahoo,
            LEAGUE_KEY,
        )
    )

    managed_team_matches = [
        row
        for row in fantasy_teams
        if (
            row.provider_team_key
            == MANAGED_TEAM_KEY
        )
    ]

    if len(
        managed_team_matches
    ) != 1:
        raise RuntimeError(
            "Expected exactly one managed "
            "Yahoo fantasy team for "
            f"{MANAGED_TEAM_KEY!r}; "
            f"found {len(managed_team_matches)}."
        )

    managed_team = (
        managed_team_matches[
            0
        ]
    )

    players = (
        fetch_all_players(
            yahoo,
            LEAGUE_KEY,
        )
    )

    player_keys = tuple(
        row.provider_player_key
        for row in players
    )

    market_states = (
        fetch_all_player_market_states(
            yahoo,
            LEAGUE_KEY,
            player_keys,
        )
    )

    percent_rostered = (
        fetch_all_player_percent_rostered(
            yahoo,
            LEAGUE_KEY,
            player_keys,
        )
    )

    nhl = NhlClient()

    nhl_teams = (
        fetch_current_teams(
            nhl
        )
    )

    games = _schedule_union(
        nhl,
        base_date=(
            args.base_date
        ),
    )

    actual_date = (
        _today_new_york()
    )

    (
        current_season_values,
        current_production_source_state,
        current_skater_stat_rows,
    ) = _fetch_current_season_values(
        league=league,
        actual_date=actual_date,
    )

    (
        performance_trends,
        moneypuck_source_state,
    ) = _fetch_current_moneypuck_trends(
        actual_date=actual_date,
    )

    (
        deployment_snapshots,
        deployment_failed_teams,
    ) = _fetch_deployment_snapshots(
        nhl_teams=nhl_teams,
    )

    nhl_player_registry = (
        fetch_player_registry()
    )

    goalie_starts_by_date = (
        _fetch_goalie_start_mappings(
            base_date=args.base_date,
            nhl_player_registry=(
                nhl_player_registry
            ),
            nhl_teams=nhl_teams,
        )
    )

    projection_adjustments = (
        build_current_state_projection_adjustments(
            player_strengths=strengths,
            projection_season_id=(
                PROJECTION_SEASON_ID
            ),
            season_values=(
                current_season_values
            ),
            performance_trends=(
                performance_trends
            ),
            deployment_snapshots=(
                deployment_snapshots
            ),
            nhl_players=(
                nhl_player_registry
            ),
        )
    )

    payload = (
        build_three_day_refresh_payload(
            players=players,
            player_strengths=(
                strengths
            ),
            nhl_teams=nhl_teams,
            games=games,
            market_states=(
                market_states
            ),
            percent_rostered_by_player_key=(
                percent_rostered
            ),
            projection_season_id=(
                PROJECTION_SEASON_ID
            ),
            base_date=(
                args.base_date
            ),
            managed_team_key=(
                MANAGED_TEAM_KEY
            ),
            league_name=(
                league.league_name
            ),
            team_name=(
                TEAM_NAME
            ),
            model_label=(
                MODEL_LABEL
            ),
            projection_adjustments=(
                projection_adjustments
            ),
            goalie_starts_by_date=(
                goalie_starts_by_date
            ),
        )
    )

    roster_position_payload = (
        build_roster_position_snapshot(
            league.roster_positions
        )
    )

    payload[
        "roster_positions"
    ] = list(
        roster_position_payload
    )

    market_result = (
        build_market_decisions(
            rows=payload[
                "rows"
            ],
            roster_positions=(
                league.roster_positions
            ),
            is_undroppable_by_player_key={
                row.provider_player_key: (
                    row.is_undroppable
                )
                for row in players
            },
            max_weekly_adds=(
                league.max_weekly_adds
            ),
            weekly_adds_used=(
                managed_team.weekly_adds_used
            ),
        )
    )

    (
        transaction_context,
        market_recommendations,
    ) = market_decision_result_payload(
        market_result
    )

    transaction_context.update(
        {
            "managed_team_key": (
                managed_team
                .provider_team_key
            ),
            "managed_team_name": (
                managed_team.name
            ),
            "weekly_adds_used": (
                managed_team
                .weekly_adds_used
            ),
            "max_weekly_adds": (
                league.max_weekly_adds
            ),
            "waiver_priority": (
                managed_team
                .waiver_priority
            ),
            "waiver_type": (
                league.waiver_type
            ),
            "waiver_rule": (
                league.waiver_rule
            ),
            "waiver_days": (
                league.waiver_days
            ),
            "uses_faab": (
                league.uses_faab
            ),
        }
    )

    payload[
        "transaction_context"
    ] = transaction_context

    payload[
        "market_recommendations"
    ] = market_recommendations

    written = (
        write_three_day_snapshot(
            payload=payload,
            path=args.output,
        )
    )

    loaded = (
        load_three_day_snapshot(
            written
        )
    )

    print(
        f"BASE_DATE={args.base_date}"
    )
    print(
        f"YAHOO_PLAYERS={len(players)}"
    )
    print(
        f"YAHOO_FANTASY_TEAMS={len(fantasy_teams)}"
    )
    print(
        "MANAGED_TEAM_WEEKLY_ADDS_USED="
        f"{managed_team.weekly_adds_used}"
    )
    print(
        "MARKET_DECISION_STATE="
        f"{market_result.state}"
    )
    print(
        "MARKET_RECOMMENDATIONS="
        f"{len(market_result.recommendations)}"
    )
    print(
        f"CANONICAL_STRENGTHS={len(strengths)}"
    )
    print(
        f"NHL_TEAMS={len(nhl_teams)}"
    )
    print(
        f"ACTUAL_DATE={actual_date}"
    )
    print(
        "CURRENT_PRODUCTION_SOURCE_STATE="
        f"{current_production_source_state}"
    )
    print(
        "CURRENT_SKATER_STAT_ROWS="
        f"{current_skater_stat_rows}"
    )
    print(
        "MONEYPUCK_SOURCE_STATE="
        f"{moneypuck_source_state}"
    )
    print(
        "MONEYPUCK_TREND_ROWS="
        f"{len(performance_trends)}"
    )
    print(
        "DFO_DEPLOYMENT_SNAPSHOTS="
        f"{len(deployment_snapshots)}"
    )
    print(
        "DFO_DEPLOYMENT_FAILED_TEAMS="
        f"{len(deployment_failed_teams)}"
    )
    print(
        "DFO_FAILED_TEAM_ABBRS="
        + (
            ",".join(
                deployment_failed_teams
            )
            if deployment_failed_teams
            else "NONE"
        )
    )
    print(
        "NHL_PLAYER_REGISTRY_ROWS="
        f"{len(nhl_player_registry)}"
    )
    print(
        "DFO_GOALIE_START_DATES="
        f"{len(goalie_starts_by_date)}"
    )
    print(
        "DFO_GOALIE_START_RESOLVED_ROWS="
        f"{sum(len(rows) for rows in goalie_starts_by_date.values())}"
    )
    print(
        "PROJECTION_ADJUSTMENT_ROWS="
        f"{len(projection_adjustments)}"
    )
    print(
        f"SCHEDULE_UNION_GAMES={len(games)}"
    )
    print(
        f"MARKET_ROWS={len(market_states)}"
    )
    print(
        "PERCENT_ROSTERED_ROWS="
        f"{len(percent_rostered)}"
    )
    print(
        "SNAPSHOT_ROWS="
        f"{len(loaded['rows'])}"
    )
    print(
        f"OUTPUT={written}"
    )
    print(
        "NFHL_THREE_DAY_REFRESH=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
