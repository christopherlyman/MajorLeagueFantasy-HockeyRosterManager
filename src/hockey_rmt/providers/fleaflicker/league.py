from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from hockey_rmt.domain.league import (
    LeagueDefinition,
    RosterPosition,
    ScoringRule,
)
from hockey_rmt.league_instances import (
    LeagueOperationalConfig,
)
from hockey_rmt.providers.fleaflicker.client import (
    FleaflickerClient,
)


class FleaflickerLeagueError(RuntimeError):
    """Fleaflicker league metadata could not be normalized."""


_ABBREVIATION_MAP = {
    "AST": "A",
    "HIT": "HIT",
    "BLK": "BLK",
    "SO": "SHO",
}


def _mapping(
    value: object,
    *,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FleaflickerLeagueError(
            f"{label} must be an object."
        )
    return value


def _sequence(
    value: object,
    *,
    label: str,
) -> Sequence[Any]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
    ):
        raise FleaflickerLeagueError(
            f"{label} must be a collection."
        )
    return value


def _text(
    value: object,
    *,
    label: str,
) -> str:
    cleaned = str(value or "").strip()

    if not cleaned:
        raise FleaflickerLeagueError(
            f"{label} must not be blank."
        )

    return cleaned


def _integer(
    value: object,
    *,
    label: str,
) -> int:
    if isinstance(value, bool):
        raise FleaflickerLeagueError(
            f"{label} must be an integer."
        )

    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise FleaflickerLeagueError(
            f"{label} must be an integer."
        ) from exc

    return result


def _number(
    value: object,
    *,
    label: str,
) -> float:
    if isinstance(value, bool):
        raise FleaflickerLeagueError(
            f"{label} must be numeric."
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise FleaflickerLeagueError(
            f"{label} must be numeric."
        ) from exc


def _canonical_abbreviation(
    value: object,
) -> str:
    raw = _text(
        value,
        label="scoring abbreviation",
    ).upper()

    return _ABBREVIATION_MAP.get(
        raw,
        raw,
    )


def _roster_positions(
    standings_payload: Mapping[str, Any],
    rules_payload: Mapping[str, Any],
) -> tuple[RosterPosition, ...]:
    league = _mapping(
        standings_payload.get("league"),
        label="standings league",
    )

    requirements = _mapping(
        league.get("rosterRequirements"),
        label="roster requirements",
    )

    raw_positions = _sequence(
        requirements.get("positions"),
        label="roster positions",
    )

    result: list[RosterPosition] = []

    for raw in raw_positions:
        row = _mapping(
            raw,
            label="roster position",
        )

        label = _text(
            row.get("label"),
            label="roster position label",
        )

        group = str(
            row.get("group")
            or ""
        ).strip().upper()

        if group == "START":
            count = _integer(
                row.get("start", 0),
                label=f"{label} starter count",
            )
            is_starting = True
        elif group == "INJURED":
            count = _integer(
                row.get("start", 0),
                label=f"{label} reserve count",
            )
            is_starting = False
        else:
            count = _integer(
                row.get("max", 0),
                label=f"{label} bench count",
            )
            is_starting = False

        if count <= 0:
            continue

        eligibility = tuple(
            str(value).strip().upper()
            for value in (
                row.get("eligibility")
                or ()
            )
            if str(value).strip()
        )

        if is_starting:
            if eligibility == ("G",):
                position_type = "G"
            else:
                position_type = "P"
        else:
            position_type = None

        result.append(
            RosterPosition(
                position=label,
                count=count,
                is_starting=is_starting,
                position_type=position_type,
            )
        )

    starter_count = sum(
        row.count
        for row in result
        if row.is_starting
    )

    expected_starters = _integer(
        requirements.get("starterCount"),
        label="standings starterCount",
    )

    rules_starters = _integer(
        rules_payload.get("numStarters"),
        label="rules numStarters",
    )

    if (
        starter_count != expected_starters
        or starter_count != rules_starters
    ):
        raise FleaflickerLeagueError(
            "Fleaflicker starter counts disagree."
        )

    bench_count = sum(
        row.count
        for row in result
        if (
            not row.is_starting
            and row.position == "BN"
        )
    )

    expected_bench = _integer(
        requirements.get("benchCount"),
        label="standings benchCount",
    )

    rules_bench = _integer(
        rules_payload.get("numBench"),
        label="rules numBench",
    )

    if (
        bench_count != expected_bench
        or bench_count != rules_bench
    ):
        raise FleaflickerLeagueError(
            "Fleaflicker bench counts disagree."
        )

    return tuple(result)


def _scoring_rules(
    rules_payload: Mapping[str, Any],
) -> tuple[ScoringRule, ...]:
    groups = _sequence(
        rules_payload.get("groups"),
        label="scoring groups",
    )

    result: list[ScoringRule] = []
    seen: set[tuple[str, str]] = set()

    for raw_group in groups:
        group = _mapping(
            raw_group,
            label="scoring group",
        )

        group_name = _text(
            group.get("label"),
            label="scoring group label",
        )

        raw_rules = group.get("scoringRules")

        if raw_rules is None:
            continue

        for raw_rule in _sequence(
            raw_rules,
            label=f"{group_name} scoring rules",
        ):
            rule = _mapping(
                raw_rule,
                label="scoring rule",
            )

            category = _mapping(
                rule.get("category"),
                label="scoring category",
            )

            stat_id = _integer(
                category.get("id"),
                label="scoring category id",
            )

            abbreviation = (
                _canonical_abbreviation(
                    category.get("abbreviation")
                )
            )

            name = _text(
                category.get("nameSingular"),
                label="scoring category name",
            )

            points_per = rule.get("pointsPer")

            if isinstance(points_per, Mapping):
                points = _number(
                    points_per.get("value"),
                    label="pointsPer value",
                )
            else:
                points_obj = _mapping(
                    rule.get("points"),
                    label="points",
                )

                raw_points = _number(
                    points_obj.get("value"),
                    label="points value",
                )

                for_every = _number(
                    rule.get("forEvery", 1),
                    label="forEvery",
                )

                if for_every == 0:
                    raise FleaflickerLeagueError(
                        "forEvery must not be zero."
                    )

                points = (
                    raw_points
                    / for_every
                )

            position_type = (
                "G"
                if group_name.strip().lower()
                == "goaltending"
                else "P"
            )

            key = (
                position_type,
                abbreviation,
            )

            if key in seen:
                raise FleaflickerLeagueError(
                    "Duplicate normalized scoring rule "
                    f"{key!r}."
                )

            seen.add(key)

            result.append(
                ScoringRule(
                    source_stat_id=stat_id,
                    name=name,
                    abbreviation=abbreviation,
                    group=group_name,
                    position_type=position_type,
                    points=points,
                )
            )

    if not result:
        raise FleaflickerLeagueError(
            "No Fleaflicker scoring rules found."
        )

    return tuple(result)


def parse_league_definition(
    rules_payload: Mapping[str, Any],
    standings_payload: Mapping[str, Any],
    *,
    operational: LeagueOperationalConfig,
) -> LeagueDefinition:
    league = _mapping(
        standings_payload.get("league"),
        label="standings league",
    )

    season_year = _integer(
        standings_payload.get("season"),
        label="season",
    )

    league_id = str(
        _integer(
            league.get("id"),
            label="league id",
        )
    )

    max_teams = _integer(
        league.get("size"),
        label="league size",
    )

    if max_teams <= 0:
        raise FleaflickerLeagueError(
            "League size must be positive."
        )

    return LeagueDefinition(
        provider="fleaflicker",
        provider_league_key=league_id,
        league_name=_text(
            league.get("name"),
            label="league name",
        ),
        sport=_text(
            league.get("sport"),
            label="sport",
        ).upper(),
        season_year=season_year,
        max_teams=max_teams,
        scoring_format=operational.scoring_format,
        roster_period=operational.roster_period,
        lineup_deadline=operational.lineup_deadline,
        start_date=operational.start_date,
        end_date=operational.end_date,
        max_weekly_adds=(
            operational.max_weekly_adds
        ),
        waiver_type=operational.waiver_type,
        waiver_rule=operational.waiver_rule,
        waiver_days=operational.waiver_days,
        uses_faab=operational.uses_faab,
        playoff_teams=operational.playoff_teams,
        playoff_start_week=(
            operational.playoff_start_week
        ),
        roster_positions=_roster_positions(
            standings_payload,
            rules_payload,
        ),
        scoring_rules=_scoring_rules(
            rules_payload
        ),
    )


def fetch_league_definition(
    client: FleaflickerClient,
    league_id: str,
    *,
    operational: LeagueOperationalConfig,
    sport: str = "NHL",
) -> LeagueDefinition:
    league = league_id.strip()
    sport_code = sport.strip().upper()

    if not league:
        raise ValueError(
            "Fleaflicker league ID must not be empty."
        )

    rules_payload = client.get_json(
        "FetchLeagueRules",
        params={
            "sport": sport_code,
            "league_id": league,
        },
    )

    standings_payload = client.get_json(
        "FetchLeagueStandings",
        params={
            "sport": sport_code,
            "league_id": league,
        },
    )

    result = parse_league_definition(
        rules_payload,
        standings_payload,
        operational=operational,
    )

    if result.provider_league_key != league:
        raise FleaflickerLeagueError(
            "Requested Fleaflicker league ID "
            f"{league!r} but provider returned "
            f"{result.provider_league_key!r}."
        )

    return result
