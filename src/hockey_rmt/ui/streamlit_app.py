from __future__ import annotations

import os

from pathlib import Path

import streamlit as st

from hockey_rmt.ui.three_day_snapshot import (
    ThreeDaySnapshotError,
    load_three_day_snapshot,
)


PROJECT_ROOT = (
    Path(
        __file__
    )
    .resolve()
    .parents[3]
)

DEFAULT_SNAPSHOT_PATH = (
    PROJECT_ROOT
    / "data"
    / "runtime"
    / "three_day_rankings.json"
)

MODEL_WARNING = (
    "Baseline model — current-season production, "
    "MoneyPuck trend, Daily Faceoff deployment, "
    "injury/status, goalie-start, and matchup "
    "adjustments are not yet applied."
)


def _snapshot_path() -> Path:
    configured = os.environ.get(
        "HOCKEY_RMT_THREE_DAY_SNAPSHOT"
    )

    if configured:
        return Path(
            configured
        )

    return DEFAULT_SNAPSHOT_PATH


def _fmt_points(
    value,
) -> str:
    if value is None:
        return "—"

    return f"{float(value):.2f}"


def _fmt_rank(
    value,
) -> str:
    if value is None:
        return "—"

    return str(
        int(
            value
        )
    )


def _opponent_text(
    day,
) -> str:
    opponent = day.get(
        "opponent"
    )

    if not opponent:
        schedule_state = day.get(
            "schedule_state"
        )

        if schedule_state == "off":
            return "OFF"

        return "—"

    home_away = day.get(
        "home_away"
    )

    if home_away == "home":
        return f"vs {opponent}"

    if home_away == "away":
        return f"@ {opponent}"

    return str(
        opponent
    )


def _day_column_prefix(
    label,
    day,
):
    return {
        f"{label} Rank": (
            _fmt_rank(
                day.get(
                    "rank"
                )
            )
        ),
        f"{label} Exp": (
            _fmt_points(
                day.get(
                    "expected_points"
                )
            )
        ),
        f"{label} Opp": (
            _opponent_text(
                day
            )
        ),
    }


def _display_rows(
    payload,
):
    result = []

    for row in payload[
        "rows"
    ]:
        today = row[
            "today"
        ]

        tomorrow = row[
            "tomorrow"
        ]

        day_plus_2 = row[
            "day_plus_2"
        ]

        display = {
            "3D Rank": (
                _fmt_rank(
                    row.get(
                        "three_day_rank"
                    )
                )
            ),
            "Player": (
                row[
                    "full_name"
                ]
            ),
            "Type": (
                row[
                    "player_type"
                ]
            ),
            "Team": (
                today.get(
                    "team"
                )
                or tomorrow.get(
                    "team"
                )
                or day_plus_2.get(
                    "team"
                )
                or "—"
            ),
        }

        display.update(
            _day_column_prefix(
                "Today",
                today,
            )
        )

        display.update(
            _day_column_prefix(
                "Tomorrow",
                tomorrow,
            )
        )

        display.update(
            _day_column_prefix(
                "Day+2",
                day_plus_2,
            )
        )

        display[
            "3D Games"
        ] = int(
            row[
                "scheduled_games"
            ]
        )

        display[
            "3D Exp"
        ] = (
            _fmt_points(
                row.get(
                    "three_day_expected_points"
                )
            )
        )

        display[
            "_three_day_rank"
        ] = (
            row.get(
                "three_day_rank"
            )
        )

        display[
            "_today_rank"
        ] = (
            today.get(
                "rank"
            )
        )

        display[
            "_tomorrow_rank"
        ] = (
            tomorrow.get(
                "rank"
            )
        )

        display[
            "_day2_rank"
        ] = (
            day_plus_2.get(
                "rank"
            )
        )

        display[
            "_player_type"
        ] = (
            row[
                "player_type"
            ]
        )

        result.append(
            display
        )

    return result


def _sort_rows(
    rows,
    mode,
):
    field_by_mode = {
        "3-Day Rank": (
            "_three_day_rank"
        ),
        "Today Rank": (
            "_today_rank"
        ),
        "Tomorrow Rank": (
            "_tomorrow_rank"
        ),
        "Day+2 Rank": (
            "_day2_rank"
        ),
    }

    field = field_by_mode[
        mode
    ]

    return sorted(
        rows,
        key=lambda row: (
            row[
                field
            ]
            is None,
            (
                row[
                    field
                ]
                if row[
                    field
                ]
                is not None
                else 10**9
            ),
            row[
                "Player"
            ].casefold(),
        ),
    )


st.set_page_config(
    page_title=(
        "NFHL Roster Manager"
    ),
    page_icon="🏒",
    layout="wide",
)

st.title(
    "NFHL Roster Manager"
)

snapshot_path = (
    _snapshot_path()
)

try:
    payload = (
        load_three_day_snapshot(
            snapshot_path
        )
    )
except ThreeDaySnapshotError as exc:
    st.subheader(
        "3-Day Decision View"
    )

    st.warning(
        "No live three-day ranking snapshot "
        "is available yet."
    )

    st.caption(
        "The UI is installed. The next refresh "
        "step will populate it from Yahoo, NHL "
        "schedule context, and the baseline "
        "daily expected-value model."
    )

    st.code(
        str(
            snapshot_path
        ),
        language=None,
    )

    st.stop()


league_name = payload[
    "league_name"
]

team_name = payload[
    "team_name"
]

base_date = payload[
    "base_date"
]

st.caption(
    f"{league_name} · {team_name} · "
    f"Base date {base_date}"
)

st.info(
    payload.get(
        "model_label"
    )
    or MODEL_WARNING
)

st.subheader(
    "3-Day Decision View"
)

rows = _display_rows(
    payload
)

total_players = len(
    rows
)

today_games = sum(
    1
    for row
    in payload[
        "rows"
    ]
    if (
        row[
            "today"
        ][
            "schedule_state"
        ]
        == "scheduled"
    )
)

tomorrow_games = sum(
    1
    for row
    in payload[
        "rows"
    ]
    if (
        row[
            "tomorrow"
        ][
            "schedule_state"
        ]
        == "scheduled"
    )
)

day2_games = sum(
    1
    for row
    in payload[
        "rows"
    ]
    if (
        row[
            "day_plus_2"
        ][
            "schedule_state"
        ]
        == "scheduled"
    )
)

metric_1, metric_2, metric_3, metric_4 = (
    st.columns(
        4
    )
)

metric_1.metric(
    "Players",
    total_players,
)

metric_2.metric(
    "Playing Today",
    today_games,
)

metric_3.metric(
    "Playing Tomorrow",
    tomorrow_games,
)

metric_4.metric(
    "Playing Day+2",
    day2_games,
)


filter_col, type_col, sort_col = (
    st.columns(
        (
            2,
            1,
            1,
        )
    )
)

with filter_col:
    name_filter = (
        st.text_input(
            "Find player",
            placeholder=(
                "Search by player name"
            ),
        )
        .strip()
        .casefold()
    )

with type_col:
    player_type = (
        st.selectbox(
            "Player type",
            (
                "All",
                "skater",
                "goalie",
            ),
        )
    )

with sort_col:
    sort_mode = (
        st.selectbox(
            "Sort by",
            (
                "3-Day Rank",
                "Today Rank",
                "Tomorrow Rank",
                "Day+2 Rank",
            ),
        )
    )


if name_filter:
    rows = [
        row
        for row
        in rows
        if (
            name_filter
            in row[
                "Player"
            ].casefold()
        )
    ]

if player_type != "All":
    rows = [
        row
        for row
        in rows
        if (
            row[
                "_player_type"
            ]
            == player_type
        )
    ]

rows = _sort_rows(
    rows,
    sort_mode,
)

hidden = {
    "_three_day_rank",
    "_today_rank",
    "_tomorrow_rank",
    "_day2_rank",
    "_player_type",
}

table_rows = [
    {
        key: value
        for key, value
        in row.items()
        if key not in hidden
    }
    for row
    in rows
]

st.dataframe(
    table_rows,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Daily ranks include players with a usable "
    "projection who are scheduled to play that "
    "day. OFF contributes 0.00 expected points "
    "but receives no daily rank. A missing or "
    "unresolved value remains unknown and makes "
    "the 3-day expected total unavailable."
)
