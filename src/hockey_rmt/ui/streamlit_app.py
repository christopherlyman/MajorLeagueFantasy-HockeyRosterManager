from __future__ import annotations

import os

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from hockey_rmt.league_instances import (
    get_league_instance,
)
from hockey_rmt.providers.fleaflicker.client import (
    FleaflickerClient,
)
from hockey_rmt.providers.fleaflicker.roster import (
    fetch_team_roster,
)
from hockey_rmt.providers.fleaflicker.teams import (
    fetch_league_teams,
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










st.set_page_config(
    page_title="Hockey Roster Manager",
    page_icon="🏒",
    layout="wide",
)

st.title(
    "Hockey Roster Manager"
)


LEAGUE_OPTIONS = (
    "NFHL",
    "OTH Redraft",
    "OTH Keeper",
)

if hasattr(
    st,
    "segmented_control",
):
    league_view = st.segmented_control(
        "League",
        options=LEAGUE_OPTIONS,
        default="NFHL",
        label_visibility="collapsed",
    )
else:
    league_view = st.radio(
        "League",
        options=LEAGUE_OPTIONS,
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )


if league_view == "OTH Keeper":
    st.caption(
        "OTH Keeper ? Fleaflicker"
    )

    st.info(
        "OTH Keeper is reserved in the unified "
        "Hockey Roster Manager. Its current "
        "Fleaflicker league ID and managed-team ID "
        "still need to be configured."
    )

    st.stop()


if league_view == "OTH Redraft":
    instance = get_league_instance(
        "oth_redraft"
    )

    try:
        fleaflicker_client = (
            FleaflickerClient()
        )

        fleaflicker_teams = (
            fetch_league_teams(
                fleaflicker_client,
                instance.provider_league_key,
                managed_team_id=(
                    instance.managed_team_key
                ),
            )
        )

        fleaflicker_team = next(
            team
            for team in fleaflicker_teams
            if team.is_owned_by_current_user
        )

        fleaflicker_roster = (
            fetch_team_roster(
                fleaflicker_client,
                instance.provider_league_key,
                instance.managed_team_key,
                season=instance.season_year,
            )
        )

    except Exception as exc:
        st.error(
            "Fleaflicker live roster refresh "
            f"failed: {exc}"
        )
        st.stop()

    level = (
        f" ? {instance.competition_level}"
        if instance.competition_level
        else ""
    )

    st.caption(
        f"{instance.display_name}"
        f"{level}"
        f" ? {fleaflicker_team.name}"
        " ? Live Fleaflicker"
    )

    st.header(
        "Current Roster"
    )

    summary = st.columns(3)

    summary[0].metric(
        "Rostered",
        len(fleaflicker_roster),
    )

    summary[1].metric(
        "Waiver Priority",
        (
            fleaflicker_team.waiver_priority
            if fleaflicker_team.waiver_priority
            is not None
            else "?"
        ),
    )

    summary[2].metric(
        "Competition",
        (
            instance.competition_level
            or "?"
        ),
    )

    roster_table = []

    for row in fleaflicker_roster:
        roster_table.append(
            {
                "Slot": row.roster_slot,
                "Player": row.full_name,
                "Pos": "/".join(
                    row.eligible_positions
                ),
                "NHL": (
                    row.nhl_team_abbr
                    or "?"
                ),
                "Status": (
                    row.status
                    or ""
                ),
            }
        )

    st.table(
        roster_table
    )

    st.info(
        "Daily projections, START/BENCH/HOLD, "
        "and free-agent rankings will use the "
        "shared hockey analytics pipeline as the "
        "Fleaflicker runtime cutover is completed."
    )

    st.stop()


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
    "3-Day Projections"
)

st.caption(
    "Compare projected fantasy points directly. "
    "This view does not choose an add/drop transaction for you."
)


rows = list(
    snapshot.get(
        "rows",
        [],
    )
)


def _numeric_value(
    value,
) -> float | None:
    if (
        value is None
        or isinstance(
            value,
            bool,
        )
    ):
        return None

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def _day_projection_value(
    row: dict,
    day_key: str,
) -> float | None:
    day = (
        row.get(
            day_key
        )
        or {}
    )

    state = str(
        day.get(
            "schedule_state",
            "",
        )
    ).strip().casefold()

    if state == "off":
        return 0.0

    return _numeric_value(
        _daily_expected(
            day
        )
    )


def _projection_cell(
    row: dict,
    day_key: str,
) -> str:
    day = (
        row.get(
            day_key
        )
        or {}
    )

    state = str(
        day.get(
            "schedule_state",
            "",
        )
    ).strip().casefold()

    if state == "off":
        return "OFF"

    value = _day_projection_value(
        row,
        day_key,
    )

    if value is None:
        return "?"

    return f"{value:.2f}"


def _three_day_value(
    row: dict,
) -> float | None:
    return _numeric_value(
        row.get(
            "three_day_expected_points"
        )
    )


def _three_day_cell(
    row: dict,
) -> str:
    value = _three_day_value(
        row
    )

    if value is None:
        return "?"

    return f"{value:.2f}"


def _position_label(
    row: dict,
) -> str:
    if _player_type(
        row
    ) == "G":
        return "G"

    raw = row.get(
        "eligible_positions"
    )

    if not isinstance(
        raw,
        (
            list,
            tuple,
        ),
    ):
        return "?"

    positions = []

    for value in raw:
        position = str(
            value
        ).strip().upper()

        if (
            position
            in {
                "C",
                "LW",
                "RW",
                "D",
                "G",
                "W",
            }
            and position
            not in positions
        ):
            positions.append(
                position
            )

    if not positions:
        return "?"

    return "/".join(
        positions
    )


def _eligible_slots_label(
    row: dict,
) -> str:
    raw = row.get(
        "eligible_positions"
    )

    if not isinstance(
        raw,
        (
            list,
            tuple,
        ),
    ):
        return "?"

    positions = []

    for value in raw:
        cleaned = str(
            value
        ).strip()

        if not cleaned:
            continue

        if cleaned.casefold() == "util":
            cleaned = "UTIL"
        else:
            cleaned = cleaned.upper()

        if cleaned not in positions:
            positions.append(
                cleaned
            )

    if not positions:
        return "?"

    return " ? ".join(
        positions
    )


def _projection_row(
    row: dict,
    *,
    include_percent: bool,
) -> dict:
    result = {
        "Player": _player_name(
            row
        ),
        "Pos.": _position_label(
            row
        ),
        "Eligible Slots": (
            _eligible_slots_label(
                row
            )
        ),
        "Team": _team(
            row
        ),
        "Status": _status(
            row
        ),
    }

    if include_percent:
        result[
            "% Ros"
        ] = _percent_rostered(
            row
        )

    result.update(
        {
            "Today Game": (
                _today_game(
                    row.get(
                        "today",
                        {},
                    )
                )
            ),
            "Today FP": (
                _projection_cell(
                    row,
                    "today",
                )
            ),
            "Tmr FP": (
                _projection_cell(
                    row,
                    "tomorrow",
                )
            ),
            "D+2 FP": (
                _projection_cell(
                    row,
                    "day_plus_2",
                )
            ),
            "3D Total": (
                _three_day_cell(
                    row
                )
            ),
        }
    )

    return result


POSITION_ORDER = {
    "C": 0,
    "LW": 1,
    "RW": 2,
    "W": 3,
    "D": 4,
    "G": 5,
    "?": 9,
}


def _roster_sort_key(
    row: dict,
):
    position = (
        _position_label(
            row
        )
        .split(
            "/",
            1,
        )[0]
    )

    return (
        POSITION_ORDER.get(
            position,
            8,
        ),
        _player_name(
            row
        ).casefold(),
    )


def _projection_sort_key(
    row: dict,
    choice: str,
):
    if choice == "Today FP":
        value = (
            _day_projection_value(
                row,
                "today",
            )
        )

    elif choice == "Tmr FP":
        value = (
            _day_projection_value(
                row,
                "tomorrow",
            )
        )

    elif choice == "D+2 FP":
        value = (
            _day_projection_value(
                row,
                "day_plus_2",
            )
        )

    else:
        value = _three_day_value(
            row
        )

    return (
        value is None,
        -(
            value
            if value is not None
            else 0.0
        ),
        _player_name(
            row
        ).casefold(),
    )


tab_roster, tab_free_agents = st.tabs(
    [
        "My Roster",
        "Free Agents",
    ]
)


with tab_roster:
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

    managed_rows = sorted(
        managed_rows,
        key=_roster_sort_key,
    )

    st.caption(
        "Pos. shows natural fantasy position(s). "
        "Eligible Slots shows every Yahoo lineup slot "
        "the player can occupy."
    )

    if not managed_rows:
        st.warning(
            "No managed-roster players are present "
            "in the current snapshot."
        )

    else:
        roster_table = [
            _projection_row(
                row,
                include_percent=False,
            )
            for row in managed_rows
        ]

        st.table(
            roster_table
        )


with tab_free_agents:
    free_agents = [
        row
        for row in rows
        if (
            row.get(
                "is_on_managed_team"
            )
            is not True
            and str(
                row.get(
                    "market_state",
                    "",
                )
            ).strip().casefold()
            == "free_agent"
        )
    ]

    controls = st.columns(
        (
            2,
            1,
            1,
            1,
        )
    )

    with controls[0]:
        search_text = st.text_input(
            "Find free agent",
            placeholder="Search player name",
            key="nfhl_fa_search",
        )

    with controls[1]:
        position_filter = st.selectbox(
            "Position",
            (
                "All",
                "C",
                "LW",
                "RW",
                "D",
                "G",
            ),
            key="nfhl_fa_position",
        )

    with controls[2]:
        sort_choice = st.selectbox(
            "Sort by",
            (
                "3-Day Total",
                "Today FP",
                "Tmr FP",
                "D+2 FP",
            ),
            key="nfhl_fa_projection_sort",
        )

    with controls[3]:
        row_limit = st.selectbox(
            "Show",
            (
                25,
                50,
                100,
            ),
            index=0,
            key="nfhl_fa_row_limit",
        )

    if search_text.strip():
        needle = (
            search_text
            .strip()
            .casefold()
        )

        free_agents = [
            row
            for row in free_agents
            if needle
            in _player_name(
                row
            ).casefold()
        ]

    if position_filter != "All":
        free_agents = [
            row
            for row in free_agents
            if position_filter
            in {
                str(position)
                .strip()
                .upper()
                for position
                in (
                    row.get(
                        "eligible_positions"
                    )
                    or []
                )
            }
        ]

    free_agents = sorted(
        free_agents,
        key=lambda row: (
            _projection_sort_key(
                row,
                sort_choice,
            )
        ),
    )

    displayed_free_agents = (
        free_agents[
            :int(
                row_limit
            )
        ]
    )

    st.caption(
        f"Showing {len(displayed_free_agents)} "
        f"of {len(free_agents)} matching true free agents."
    )

    if not displayed_free_agents:
        st.info(
            "No free agents match the current filters."
        )

    else:
        free_agent_table = [
            _projection_row(
                row,
                include_percent=True,
            )
            for row
            in displayed_free_agents
        ]

        st.table(
            free_agent_table
        )


st.caption(
    "Today / Tmr / D+2 are projected fantasy points. "
    "3D Total is the projected sum across those three days. "
    "OFF = no NHL game; ? = projection unavailable or unresolved."
)
