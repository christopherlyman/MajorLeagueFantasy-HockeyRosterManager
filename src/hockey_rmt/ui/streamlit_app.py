from __future__ import annotations

import os

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

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

EASTERN_TIME = (
    ZoneInfo(
        "America/New_York"
    )
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

    if value.casefold() in {
        "goalie",
        "g",
    }:
        return "G"

    if value.casefold() in {
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

        value = (
            day.get(
                "team"
            )
            or day.get(
                "nhl_team_abbr"
            )
        )

        if value:
            return str(
                value
            )

    return "—"


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


def _three_day_expected(
    row: dict,
):
    value = row.get(
        "three_day_expected_fantasy_points"
    )

    if value is None:
        value = row.get(
            "three_day_expected_points"
        )

    return value


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


def _matchup(
    day: dict,
) -> str:
    if (
        day.get(
            "schedule_state"
        )
        == "off"
    ):
        return "OFF"

    opponent = (
        day.get(
            "opponent_team_abbr"
        )
        or day.get(
            "opponent"
        )
    )

    if not opponent:
        return ""

    home_away = str(
        day.get(
            "home_away",
            "",
        )
    ).casefold()

    if home_away == "home":
        prefix = "vs"
    elif home_away == "away":
        prefix = "@"
    else:
        prefix = ""

    text = (
        f"{prefix} {opponent}"
        .strip()
    )

    game_time = (
        _format_game_time(
            day.get(
                "start_time_utc"
            )
        )
    )

    if game_time:
        text = (
            f"{text} {game_time}"
        )

    return text


def _day_cell(
    day: dict,
) -> str:
    state = day.get(
        "schedule_state"
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
        rank is not None
        and expected is not None
    ):
        result = (
            f"{int(rank)} "
            f"({float(expected):.2f})"
        )

    elif expected is not None:
        result = (
            f"— "
            f"({float(expected):.2f})"
        )

    else:
        result = "—"

    matchup = _matchup(
        day
    )

    if matchup:
        return (
            f"{result} · "
            f"{matchup}"
        )

    return result


def _three_day_cell(
    row: dict,
) -> str:
    rank = row.get(
        "three_day_rank"
    )

    expected = (
        _three_day_expected(
            row
        )
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


def _sort_rank(
    row: dict,
    choice: str,
):
    if choice == "Today Rank":
        value = _daily_rank(
            row.get(
                "today",
                {},
            )
        )

    elif choice == "Tomorrow Rank":
        value = _daily_rank(
            row.get(
                "tomorrow",
                {},
            )
        )

    elif choice == "Day+2 Rank":
        value = _daily_rank(
            row.get(
                "day_plus_2",
                {},
            )
        )

    else:
        value = row.get(
            "three_day_rank"
        )

    if value is None:
        return 10**9

    return int(
        value
    )


st.set_page_config(
    page_title="NFHL Roster Manager",
    page_icon="🏒",
    layout="wide",
)

st.title(
    "NFHL Roster Manager"
)

path = _snapshot_path()

if not path.exists():
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
        path
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


filters = st.columns(
    (
        2,
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
    player_type = st.selectbox(
        "Player type",
        (
            "All",
            "Skaters",
            "Goalies",
        ),
    )

with filters[2]:
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


if player_type == "Skaters":
    filtered = [
        row
        for row in filtered
        if _player_type(
            row
        )
        != "G"
    ]

elif player_type == "Goalies":
    filtered = [
        row
        for row in filtered
        if _player_type(
            row
        )
        == "G"
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
        "3D": (
            _three_day_cell(
                row
            )
        ),
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
        "Games": (
            row.get(
                "scheduled_games"
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
        "3D",
        "Player",
        "Type",
        "Team",
        "Today",
        "Tmr",
        "D+2",
        "Games",
    ),
    column_config={
        "3D": (
            st.column_config.TextColumn(
                "3D",
                width="small",
            )
        ),
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
                width="medium",
            )
        ),
        "Tmr": (
            st.column_config.TextColumn(
                "Tmr",
                width="medium",
            )
        ),
        "D+2": (
            st.column_config.TextColumn(
                "D+2",
                width="medium",
            )
        ),
        "Games": (
            st.column_config.NumberColumn(
                "Games",
                width="small",
                format="%d",
            )
        ),
    },
)

st.caption(
    "Format: rank (expected NFHL points) · "
    "matchup puck-drop time. "
    "Times are Eastern. "
    "OFF = known off-day; "
    "— = unresolved or missing value."
)
