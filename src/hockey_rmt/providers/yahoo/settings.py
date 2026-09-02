from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from hockey_rmt.domain.league import (
    LeagueDefinition,
    RosterPosition,
    ScoringRule,
)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value

    return str(value or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _to_optional_int(value: object) -> int | None:
    if value is None or str(value).strip() == "":
        return None

    return int(value)


def _canonical_scoring_format(
    yahoo_scoring_type: object,
) -> str:
    value = str(
        yahoo_scoring_type or ""
    ).strip().lower()

    known = {
        "headpoint": "h2h_points",
    }

    return known.get(
        value,
        value or "unknown",
    )


def _canonical_roster_period(
    yahoo_roster_type: object,
) -> str:
    value = str(
        yahoo_roster_type or ""
    ).strip().lower()

    known = {
        "date": "daily",
    }

    return known.get(
        value,
        value or "unknown",
    )


def _canonical_waiver_type(
    yahoo_waiver_type: object,
) -> str:
    value = str(
        yahoo_waiver_type or ""
    ).strip()

    known = {
        "R": "rolling",
    }

    return known.get(
        value,
        value.lower() or "unknown",
    )


def parse_league_settings(
    payload: Mapping[str, Any],
) -> LeagueDefinition:
    fantasy_content = payload[
        "fantasy_content"
    ]

    league = fantasy_content["league"]

    identity = league[0]
    settings = league[1]["settings"][0]

    roster_positions: list[
        RosterPosition
    ] = []

    for entry in settings.get(
        "roster_positions",
        [],
    ):
        row = entry["roster_position"]

        roster_positions.append(
            RosterPosition(
                position=str(
                    row["position"]
                ),
                count=int(
                    row["count"]
                ),
                is_starting=_to_bool(
                    row.get(
                        "is_starting_position"
                    )
                ),
                position_type=(
                    str(row["position_type"])
                    if row.get(
                        "position_type"
                    )
                    is not None
                    else None
                ),
            )
        )

    categories_by_id: dict[
        int,
        Mapping[str, Any],
    ] = {}

    stat_categories = settings.get(
        "stat_categories",
        {},
    )

    for entry in stat_categories.get(
        "stats",
        [],
    ):
        stat = entry["stat"]

        categories_by_id[
            int(stat["stat_id"])
        ] = stat

    scoring_rules: list[
        ScoringRule
    ] = []

    stat_modifiers = settings.get(
        "stat_modifiers",
        {},
    )

    for entry in stat_modifiers.get(
        "stats",
        [],
    ):
        modifier = entry["stat"]
        stat_id = int(
            modifier["stat_id"]
        )

        category = categories_by_id.get(
            stat_id
        )

        if category is None:
            raise ValueError(
                "Yahoo scoring modifier "
                f"{stat_id} has no matching "
                "stat category."
            )

        scoring_rules.append(
            ScoringRule(
                source_stat_id=stat_id,
                name=str(
                    category.get("name")
                    or ""
                ),
                abbreviation=str(
                    category.get("abbr")
                    or category.get(
                        "display_name"
                    )
                    or ""
                ),
                group=str(
                    category.get("group")
                    or ""
                ),
                position_type=str(
                    category.get(
                        "position_type"
                    )
                    or ""
                ),
                points=float(
                    modifier["value"]
                ),
            )
        )

    return LeagueDefinition(
        provider="yahoo",
        provider_league_key=str(
            identity["league_key"]
        ),
        league_name=str(
            identity["name"]
        ),
        sport=str(
            identity["game_code"]
        ),
        season_year=int(
            identity["season"]
        ),
        max_teams=int(
            settings["max_teams"]
        ),
        scoring_format=(
            _canonical_scoring_format(
                settings.get(
                    "scoring_type"
                )
            )
        ),
        roster_period=(
            _canonical_roster_period(
                identity.get(
                    "roster_type"
                )
            )
        ),
        lineup_deadline=str(
            identity.get(
                "weekly_deadline"
            )
            or ""
        ),
        start_date=date.fromisoformat(
            str(identity["start_date"])
        ),
        end_date=date.fromisoformat(
            str(identity["end_date"])
        ),
        max_weekly_adds=(
            _to_optional_int(
                settings.get(
                    "max_weekly_adds"
                )
            )
        ),
        waiver_type=(
            _canonical_waiver_type(
                settings.get(
                    "waiver_type"
                )
            )
        ),
        waiver_rule=str(
            settings.get(
                "waiver_rule"
            )
            or ""
        ),
        waiver_days=(
            _to_optional_int(
                settings.get(
                    "waiver_time"
                )
            )
        ),
        uses_faab=_to_bool(
            settings.get(
                "uses_faab"
            )
        ),
        playoff_teams=(
            _to_optional_int(
                settings.get(
                    "num_playoff_teams"
                )
            )
        ),
        playoff_start_week=(
            _to_optional_int(
                settings.get(
                    "playoff_start_week"
                )
            )
        ),
        roster_positions=tuple(
            roster_positions
        ),
        scoring_rules=tuple(
            scoring_rules
        ),
    )
