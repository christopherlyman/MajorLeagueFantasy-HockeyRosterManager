from __future__ import annotations

import os

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from hockey_rmt.services.lineup_optimizer import (
    LineupOptimizerError,
    build_daily_lineup_decisions,
)
from hockey_rmt.ui.three_day_snapshot import (
    load_three_day_snapshot,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

DEFAULT_SNAPSHOT_PATH = (
    PROJECT_ROOT
    / "data"
    / "runtime"
    / "three_day_rankings.json"
)

EASTERN_TIME = ZoneInfo(
    "America/New_York"
)


def _snapshot_path() -> Path:
    value = os.environ.get(
        "HOCKEY_RMT_THREE_DAY_SNAPSHOT"
    )

    if value:
        return Path(
            value
        )

    return DEFAULT_SNAPSHOT_PATH


def _player_name(
    row: dict,
) -> str:
    return str(
        row.get(
            "full_name",
            "",
        )
    )


def _player_type(
    row: dict,
) -> str:
    value = str(
        row.get(
            "player_type",
            "",
        )
    ).strip()

    lowered = value.casefold()

    if lowered in {
        "goalie",
        "g",
    }:
        return "G"

    if lowered in {
        "skater",
        "p",
    }:
        return "P"

    return value or "—"


def _team(
    row: dict,
) -> str:
    for key in (
        "today",
        "tomorrow",
        "day_plus_2",
    ):
        day = (
            row.get(key)
            or {}
        )

        team = (
            day.get(
                "nhl_team_abbr"
            )
            or day.get(
                "team"
            )
        )

        if team:
            return str(
                team
            )

    return "—"



def _eligible_positions(
    row: dict,
) -> str:
    positions = row.get(
        "eligible_positions"
    )

    if not isinstance(
        positions,
        (list, tuple),
    ):
        return "—"

    cleaned = [
        str(position).strip()
        for position in positions
        if str(position).strip()
    ]

    if not cleaned:
        return "—"

    return ", ".join(
        cleaned
    )



def _status(
    row: dict,
) -> str:
    value = row.get(
        "provider_status"
    )

    if value is None:
        return "—"

    cleaned = str(
        value
    ).strip()

    if not cleaned:
        return "—"

    return cleaned


def _percent_rostered(
    row: dict,
) -> str:
    value = row.get(
        "percent_rostered"
    )

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
        or value > 100
    ):
        return "—"

    return f"{value}%"

def _market_bucket(
    row: dict,
) -> str:
    if (
        row.get(
            "is_on_managed_team"
        )
        is True
    ):
        return "My Roster"

    state = str(
        row.get(
            "market_state"
        )
        or ""
    ).strip().casefold()

    if state == "free_agent":
        return "Free Agents"

    if state == "waivers":
        return "Waivers"

    if state:
        return "Other Teams"

    return "Unknown"

def _daily_rank(
    day: dict,
):
    value = day.get(
        "daily_rank"
    )

    if value is None:
        value = day.get(
            "rank"
        )

    return value


def _daily_expected(
    day: dict,
):
    value = day.get(
        "expected_fantasy_points"
    )

    if value is None:
        value = day.get(
            "expected_points"
        )

    return value


def _day_cell(
    day: dict,
) -> str:
    state = str(
        day.get(
            "schedule_state",
            "",
        )
    )

    if state == "off":
        return "OFF"

    rank = _daily_rank(
        day
    )

    expected = _daily_expected(
        day
    )

    if (
        rank is None
        or expected is None
    ):
        return "—"

    return (
        f"{int(rank)} "
        f"({float(expected):.2f})"
    )


def _format_game_time(
    value,
) -> str:
    if value in (
        None,
        "",
    ):
        return ""

    if isinstance(
        value,
        datetime,
    ):
        moment = value

    else:
        text = str(
            value
        ).strip()

        if text.endswith(
            "Z"
        ):
            text = (
                text[:-1]
                + "+00:00"
            )

        try:
            moment = datetime.fromisoformat(
                text
            )
        except ValueError:
            return ""

    if moment.tzinfo is None:
        moment = moment.replace(
            tzinfo=timezone.utc
        )

    eastern = moment.astimezone(
        EASTERN_TIME
    )

    return (
        eastern.strftime(
            "%I:%M %p"
        )
        .lstrip("0")
    )


def _today_game(
    day: dict,
) -> str:
    state = str(
        day.get(
            "schedule_state",
            "",
        )
    )

    if state == "off":
        return "OFF"

    if state != "scheduled":
        return "—"

    opponent = (
        day.get(
            "opponent_team_abbr"
        )
        or day.get(
            "opponent"
        )
    )

    home_away = str(
        day.get(
            "home_away",
            "",
        )
    ).casefold()

    matchup = ""

    if opponent:
        if home_away == "home":
            matchup = (
                f"vs {opponent}"
            )

        elif home_away == "away":
            matchup = (
                f"@ {opponent}"
            )

        else:
            matchup = str(
                opponent
            )

    game_time = (
        _format_game_time(
            day.get(
                "start_time_utc"
            )
        )
    )

    if matchup and game_time:
        return (
            f"{matchup} "
            f"{game_time}"
        )

    if matchup:
        return matchup

    if game_time:
        return game_time

    return "—"


def _sort_rank(
    row: dict,
    choice: str,
):
    if choice == "Today Rank":
        rank = _daily_rank(
            row.get(
                "today",
                {},
            )
        )

    elif choice == "Tomorrow Rank":
        rank = _daily_rank(
            row.get(
                "tomorrow",
                {},
            )
        )

    elif choice == "Day+2 Rank":
        rank = _daily_rank(
            row.get(
                "day_plus_2",
                {},
            )
        )

    else:
        rank = row.get(
            "three_day_rank"
        )

    if rank is None:
        return 10**9

    return int(
        rank
    )



def _decision_reason_label(
    reason: str,
) -> str:
    labels = {
        "optimal_daily_lineup": (
            "Best legal lineup"
        ),
        (
            "optimal_daily_lineup_"
            "availability_uncertain"
        ): (
            "Best legal lineup; "
            "availability uncertain"
        ),
        "slot_congestion": (
            "Better option fills available slot"
        ),
        "off_day": "No game",
        "player_unavailable": (
            "Unavailable"
        ),
        "schedule_unresolved": (
            "Schedule unresolved"
        ),
        "no_positive_projection": (
            "No usable positive projection"
        ),
        "goalie_start_model_pending": (
            "Goalie start model pending"
        ),
        "no_same_day_action": (
            "No same-day action"
        ),
    }

    return labels.get(
        reason,
        reason.replace(
            "_",
            " ",
        ).capitalize(),
    )


st.set_page_config(
    page_title="NFHL Roster Manager",
    page_icon="🏒",
    layout="wide",
)

st.title(
    "NFHL Roster Manager"
)


snapshot_path = (
    _snapshot_path()
)

if not snapshot_path.exists():
    st.subheader(
        "3-Day Decision View"
    )

    st.warning(
        "No live three-day ranking "
        "snapshot is available yet."
    )

    st.stop()


snapshot = (
    load_three_day_snapshot(
        snapshot_path
    )
)


st.caption(
    f"{snapshot.get('league_name', 'NFHL')}"
    f" · {snapshot.get('team_name', '')}"
    f" · Base date "
    f"{snapshot.get('base_date', '')}"
)


model_label = snapshot.get(
    "model_label"
)

if model_label:
    st.info(
        model_label
    )


st.subheader(
    "3-Day Decision View"
)


rows = list(
    snapshot.get(
        "rows",
        []
    )
)


st.subheader(
    "Lineup Recommendations"
)

roster_positions = snapshot.get(
    "roster_positions"
)

managed_rows = [
    row
    for row in rows
    if (
        row.get(
            "is_on_managed_team"
        )
        is True
    )
]

if (
    not isinstance(
        roster_positions,
        list,
    )
    or not roster_positions
):
    st.caption(
        "Lineup recommendations will activate "
        "after the next live refresh writes "
        "Yahoo roster-slot metadata."
    )

elif not managed_rows:
    st.info(
        "Yahoo has not populated Drop The Gloves "
        "with a managed roster yet. "
        "Lineup recommendations will activate "
        "automatically when roster ownership "
        "appears in the Yahoo feed."
    )

else:
    recommendation_day = st.selectbox(
        "Recommendation day",
        (
            "Today",
            "Tomorrow",
            "Day+2",
        ),
        key=(
            "lineup_recommendation_day"
        ),
    )

    day_key = {
        "Today": "today",
        "Tomorrow": "tomorrow",
        "Day+2": "day_plus_2",
    }[
        recommendation_day
    ]

    try:
        lineup_decisions = (
            build_daily_lineup_decisions(
                rows=rows,
                roster_positions=(
                    roster_positions
                ),
                day_key=day_key,
            )
        )

    except LineupOptimizerError as exc:
        st.error(
            "Unable to build lineup "
            f"recommendations: {exc}"
        )

    else:
        source_by_key = {
            str(
                row.get(
                    "provider_player_key",
                    "",
                )
            ): row
            for row in managed_rows
        }

        lineup_table = []

        for decision in lineup_decisions:
            source = source_by_key[
                decision.provider_player_key
            ]

            lineup_table.append(
                {
                    "Player": (
                        decision.full_name
                    ),
                    "Action": (
                        decision.action
                    ),
                    "Slot": (
                        decision.assigned_position
                        or "—"
                    ),
                    "Eligible Pos.": (
                        _eligible_positions(
                            source
                        )
                    ),
                    "Status": (
                        _status(
                            source
                        )
                    ),
                    "Projected": (
                        (
                            f"{decision.expected_points:.2f}"
                        )
                        if (
                            decision.expected_points
                            is not None
                        )
                        else "—"
                    ),
                    "Why": (
                        _decision_reason_label(
                            decision.reason
                        )
                    ),
                }
            )

        st.dataframe(
            lineup_table,
            hide_index=True,
            use_container_width=True,
            column_order=(
                "Player",
                "Action",
                "Slot",
                "Eligible Pos.",
                "Status",
                "Projected",
                "Why",
            ),
        )

        st.caption(
            "START/BENCH currently optimizes "
            "skaters only. Scheduled goalies "
            "remain HOLD until the separate "
            "goalie-start model is connected."
        )


metrics = st.columns(
    4
)

metrics[0].metric(
    "Players",
    len(rows),
)


for index, (
    label,
    key,
) in enumerate(
    (
        (
            "Playing Today",
            "today",
        ),
        (
            "Playing Tomorrow",
            "tomorrow",
        ),
        (
            "Playing Day+2",
            "day_plus_2",
        ),
    ),
    start=1,
):
    count = sum(
        1
        for row in rows
        if (
            row.get(
                key,
                {},
            ).get(
                "schedule_state"
            )
            == "scheduled"
        )
    )

    metrics[
        index
    ].metric(
        label,
        count,
    )


market_buckets = {
    _market_bucket(row)
    for row in rows
}

market_options = [
    "All"
]

for market_label in (
    "My Roster",
    "Free Agents",
    "Waivers",
    "Other Teams",
):
    if market_label in market_buckets:
        market_options.append(
            market_label
        )


filters = st.columns(
    (
        2,
        1,
        1,
        1,
    )
)


with filters[0]:
    search_text = st.text_input(
        "Find player",
        placeholder=(
            "Search by player name"
        ),
    )


with filters[1]:
    player_type_filter = (
        st.selectbox(
            "Player type",
            (
                "All",
                "Skaters",
                "Goalies",
            ),
        )
    )


with filters[2]:
    market_filter = st.selectbox(
        "Market",
        tuple(
            market_options
        ),
    )


with filters[3]:
    sort_by = st.selectbox(
        "Sort by",
        (
            "3-Day Rank",
            "Today Rank",
            "Tomorrow Rank",
            "Day+2 Rank",
        ),
    )


filtered = rows


if search_text.strip():
    needle = (
        search_text
        .strip()
        .casefold()
    )

    filtered = [
        row
        for row in filtered
        if needle
        in _player_name(
            row
        ).casefold()
    ]


if (
    player_type_filter
    == "Skaters"
):
    filtered = [
        row
        for row in filtered
        if _player_type(
            row
        )
        != "G"
    ]

elif (
    player_type_filter
    == "Goalies"
):
    filtered = [
        row
        for row in filtered
        if _player_type(
            row
        )
        == "G"
    ]


if market_filter != "All":
    filtered = [
        row
        for row in filtered
        if (
            _market_bucket(row)
            == market_filter
        )
    ]


filtered = sorted(
    filtered,
    key=lambda row: (
        _sort_rank(
            row,
            sort_by,
        ),
        _player_name(
            row
        ).casefold(),
        str(
            row.get(
                "provider_player_key",
                "",
            )
        ),
    ),
)


table_rows = [
    {
        "Player": (
            _player_name(
                row
            )
        ),
        "Type": (
            _player_type(
                row
            )
        ),
        "Team": (
            _team(
                row
            )
        ),
        "Eligible Pos.": (
            _eligible_positions(
                row
            )
        ),
        "Status": (
            _status(
                row
            )
        ),
        "% Ros": (
            _percent_rostered(
                row
            )
        ),
        "Today": (
            _day_cell(
                row.get(
                    "today",
                    {},
                )
            )
        ),
        "Tmr": (
            _day_cell(
                row.get(
                    "tomorrow",
                    {},
                )
            )
        ),
        "D+2": (
            _day_cell(
                row.get(
                    "day_plus_2",
                    {},
                )
            )
        ),
        "Game": (
            _today_game(
                row.get(
                    "today",
                    {},
                )
            )
        ),
    }
    for row in filtered
]


st.dataframe(
    table_rows,
    hide_index=True,
    use_container_width=True,
    column_order=(
        "Player",
        "Type",
        "Team",
        "Eligible Pos.",
        "Status",
        "% Ros",
        "Today",
        "Tmr",
        "D+2",
        "Game",
    ),
    column_config={
        "Player": (
            st.column_config.TextColumn(
                "Player",
                width="medium",
            )
        ),
        "Type": (
            st.column_config.TextColumn(
                "Type",
                width="small",
            )
        ),
        "Team": (
            st.column_config.TextColumn(
                "Team",
                width="small",
            )
        ),
        "Today": (
            st.column_config.TextColumn(
                "Today",
                width="small",
            )
        ),
        "Tmr": (
            st.column_config.TextColumn(
                "Tmr",
                width="small",
            )
        ),
        "D+2": (
            st.column_config.TextColumn(
                "D+2",
                width="small",
            )
        ),
        "Game": (
            st.column_config.TextColumn(
                "Game",
                width="medium",
            )
        ),
    },
)


st.caption(
    "Today / Tmr / D+2 = "
    "rank (expected NFHL points). "
    "Game = today's matchup and puck-drop time only. "
    "Times are Eastern. "
    "OFF = known off-day; "
    "— = unresolved or missing."
)
