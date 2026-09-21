from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date

from hockey_rmt.domain.goalie_start import (
    GOALIE_START_SOURCE_DAILY_FACEOFF,
    DailyGoalieStartEvidence,
)
from hockey_rmt.domain.player_identity import (
    NhlPlayerIdentity,
    PlayerIdentityResolution,
)
from hockey_rmt.providers.daily_faceoff.player_identity_overrides import (
    REVIEWED_NHL_PLAYER_ID_OVERRIDES,
)
from hockey_rmt.services.player_identity import (
    normalize_player_name,
)
from hockey_rmt.services.team_identity import (
    normalize_team_name,
)


class GoalieStartIdentityError(RuntimeError):
    """Daily goalie-start identity resolution failed."""


def _team_abbreviation_by_name(
    nhl_teams: Sequence[object],
) -> dict[str, str]:
    result: dict[str, str] = {}

    for team in nhl_teams:
        team_name = str(
            getattr(
                team,
                "name",
                "",
            )
            or ""
        ).strip()

        team_abbr = str(
            getattr(
                team,
                "abbreviation",
                "",
            )
            or ""
        ).strip().upper()

        if not team_name:
            raise GoalieStartIdentityError(
                "NHL team registry contained "
                "an empty team name."
            )

        if not team_abbr:
            raise GoalieStartIdentityError(
                "NHL team registry contained "
                f"an empty abbreviation for "
                f"{team_name!r}."
            )

        normalized = normalize_team_name(
            team_name
        )

        if not normalized:
            raise GoalieStartIdentityError(
                "NHL team registry contained "
                "an empty normalized team name "
                f"for {team_name!r}."
            )

        if normalized in result:
            raise GoalieStartIdentityError(
                "NHL team registry contained "
                "duplicate normalized team name "
                f"{normalized!r}."
            )

        result[normalized] = team_abbr

    return result


def _resolve_team_abbreviation(
    team_name: str,
    *,
    team_abbreviation_by_name: Mapping[
        str,
        str,
    ],
) -> str:
    normalized = normalize_team_name(
        str(
            team_name
        ).strip()
    )

    if not normalized:
        raise GoalieStartIdentityError(
            "Daily Faceoff goalie-start team "
            "name normalized to empty."
        )

    try:
        return team_abbreviation_by_name[
            normalized
        ]
    except KeyError as exc:
        raise GoalieStartIdentityError(
            "Daily Faceoff goalie-start team "
            "could not be resolved against "
            "the NHL team registry: "
            f"{team_name!r}."
        ) from exc


def _identity_indexes(
    nhl_players: Sequence[
        NhlPlayerIdentity
    ],
) -> tuple[
    dict[int, NhlPlayerIdentity],
    dict[str, list[NhlPlayerIdentity]],
]:
    by_id: dict[
        int,
        NhlPlayerIdentity,
    ] = {}

    by_name: dict[
        str,
        list[NhlPlayerIdentity],
    ] = defaultdict(
        list
    )

    for player in nhl_players:
        nhl_player_id = int(
            player.nhl_player_id
        )

        if nhl_player_id in by_id:
            raise GoalieStartIdentityError(
                "NHL identity registry contained "
                "duplicate playerId "
                f"{nhl_player_id}."
            )

        by_id[
            nhl_player_id
        ] = player

        normalized_name = normalize_player_name(
            player.full_name
        )

        if not normalized_name:
            raise GoalieStartIdentityError(
                "NHL identity registry contained "
                "an empty normalized player name "
                f"for playerId {nhl_player_id}."
            )

        by_name[
            normalized_name
        ].append(
            player
        )

    return by_id, by_name


def _merged_overrides(
    explicit_nhl_player_ids: Mapping[
        str,
        int,
    ]
    | None,
) -> dict[str, int]:
    result = {
        str(
            source_player_id
        ): int(
            nhl_player_id
        )
        for (
            source_player_id,
            nhl_player_id,
        ) in (
            REVIEWED_NHL_PLAYER_ID_OVERRIDES
            .items()
        )
    }

    for (
        source_player_id,
        nhl_player_id,
    ) in (
        explicit_nhl_player_ids
        or {}
    ).items():
        source_key = str(
            source_player_id
        )

        target_id = int(
            nhl_player_id
        )

        existing = result.get(
            source_key
        )

        if (
            existing is not None
            and existing != target_id
        ):
            raise GoalieStartIdentityError(
                "Explicit goalie-start identity "
                "override conflicted with "
                "reviewed Daily Faceoff override "
                f"for source playerId "
                f"{source_key!r}."
            )

        result[
            source_key
        ] = target_id

    return result


def resolve_goalie_start_identities(
    *,
    goalie_starts: Sequence[
        DailyGoalieStartEvidence
    ],
    nhl_players: Sequence[
        NhlPlayerIdentity
    ],
    nhl_teams: Sequence[
        object
    ],
    game_date: date,
    explicit_nhl_player_ids: Mapping[
        str,
        int,
    ]
    | None = None,
) -> tuple[
    PlayerIdentityResolution,
    ...,
]:
    rows = tuple(
        goalie_starts
    )

    if not rows:
        return ()

    registry = tuple(
        nhl_players
    )

    if not registry:
        raise GoalieStartIdentityError(
            "Goalie-start evidence was supplied "
            "without an NHL identity registry."
        )

    teams = tuple(
        nhl_teams
    )

    if not teams:
        raise GoalieStartIdentityError(
            "Goalie-start evidence was supplied "
            "without an NHL team registry."
        )

    team_by_name = (
        _team_abbreviation_by_name(
            teams
        )
    )

    nhl_by_id, nhl_by_name = (
        _identity_indexes(
            registry
        )
    )

    overrides = _merged_overrides(
        explicit_nhl_player_ids
    )

    seen_source_ids = set()
    assigned_nhl_ids = set()

    result = []

    for row in rows:
        if (
            row.source
            != GOALIE_START_SOURCE_DAILY_FACEOFF
        ):
            raise GoalieStartIdentityError(
                "Unsupported goalie-start source "
                f"{row.source!r}."
            )

        if row.game_date != game_date:
            raise GoalieStartIdentityError(
                "Goalie-start evidence date "
                f"{row.game_date.isoformat()} "
                "did not match requested date "
                f"{game_date.isoformat()}."
            )

        source_player_id = str(
            row.provider_goalie_id
        )

        if source_player_id in seen_source_ids:
            raise GoalieStartIdentityError(
                "Goalie-start evidence contained "
                "duplicate source playerId "
                f"{source_player_id!r}."
            )

        seen_source_ids.add(
            source_player_id
        )

        source_team = (
            _resolve_team_abbreviation(
                row.team_name,
                team_abbreviation_by_name=(
                    team_by_name
                ),
            )
        )

        opponent_team = (
            _resolve_team_abbreviation(
                row.opponent_team_name,
                team_abbreviation_by_name=(
                    team_by_name
                ),
            )
        )

        if source_team == opponent_team:
            raise GoalieStartIdentityError(
                "Goalie-start team and opponent "
                "resolved to the same NHL team "
                f"{source_team!r}."
            )

        normalized_name = (
            normalize_player_name(
                row.goalie_name
            )
        )

        if not normalized_name:
            raise GoalieStartIdentityError(
                "Goalie-start player name "
                "normalized to empty for "
                f"source playerId "
                f"{source_player_id!r}."
            )

        explicit_nhl_id = overrides.get(
            source_player_id
        )

        candidate = None
        method = None

        if explicit_nhl_id is not None:
            candidate = nhl_by_id.get(
                explicit_nhl_id
            )

            if candidate is None:
                raise GoalieStartIdentityError(
                    "Goalie-start identity override "
                    "referenced unknown NHL "
                    f"playerId {explicit_nhl_id}."
                )

            candidate_team = str(
                candidate.team_abbr
                or ""
            ).strip().upper()

            if candidate_team != source_team:
                raise GoalieStartIdentityError(
                    "Goalie-start identity override "
                    "team did not match source "
                    "team: source playerId "
                    f"{source_player_id!r}, "
                    f"NHL playerId "
                    f"{explicit_nhl_id}, "
                    f"source team "
                    f"{source_team!r}, "
                    f"NHL team "
                    f"{candidate_team!r}."
                )

            candidate_position = str(
                candidate.position
                or ""
            ).strip().upper()

            if candidate_position != "G":
                raise GoalieStartIdentityError(
                    "Goalie-start identity override "
                    "did not resolve to an NHL "
                    "goalie: NHL playerId "
                    f"{explicit_nhl_id}, "
                    f"position "
                    f"{candidate_position!r}."
                )

            method = "explicit_override"

        else:
            name_candidates = (
                nhl_by_name.get(
                    normalized_name,
                    [],
                )
            )

            team_candidates = [
                player
                for player in name_candidates
                if (
                    str(
                        player.team_abbr
                        or ""
                    )
                    .strip()
                    .upper()
                    == source_team
                    and str(
                        player.position
                        or ""
                    )
                    .strip()
                    .upper()
                    == "G"
                )
            ]

            if len(
                team_candidates
            ) == 1:
                candidate = (
                    team_candidates[0]
                )
                method = (
                    "exact_name_team"
                )

        if candidate is None:
            result.append(
                PlayerIdentityResolution(
                    provider_player_key=(
                        source_player_id
                    ),
                    resolution_state=(
                        "unresolved"
                    ),
                    resolution_method=None,
                    nhl_player_id=None,
                    nhl_full_name=None,
                    nhl_position=None,
                    nhl_team_abbr=None,
                )
            )

            continue

        candidate_id = int(
            candidate.nhl_player_id
        )

        if candidate_id in assigned_nhl_ids:
            raise GoalieStartIdentityError(
                "One NHL playerId resolved from "
                "multiple Daily Faceoff "
                "goalie-start rows: "
                f"{candidate_id}."
            )

        assigned_nhl_ids.add(
            candidate_id
        )

        result.append(
            PlayerIdentityResolution(
                provider_player_key=(
                    source_player_id
                ),
                resolution_state=(
                    "resolved"
                ),
                resolution_method=method,
                nhl_player_id=(
                    candidate_id
                ),
                nhl_full_name=(
                    candidate.full_name
                ),
                nhl_position=(
                    candidate.position
                ),
                nhl_team_abbr=(
                    candidate.team_abbr
                ),
            )
        )

    if len(result) != len(rows):
        raise GoalieStartIdentityError(
            "Goalie-start identity result count "
            "did not match evidence row count."
        )

    return tuple(
        result
    )


def build_goalie_starts_by_nhl_id(
    *,
    goalie_starts: Sequence[
        DailyGoalieStartEvidence
    ],
    nhl_players: Sequence[
        NhlPlayerIdentity
    ],
    nhl_teams: Sequence[
        object
    ],
    game_date: date,
    explicit_nhl_player_ids: Mapping[
        str,
        int,
    ]
    | None = None,
) -> dict[
    int,
    DailyGoalieStartEvidence,
]:
    rows = tuple(
        goalie_starts
    )

    if not rows:
        return {}

    source_by_id = {
        str(
            row.provider_goalie_id
        ): row
        for row in rows
    }

    if len(source_by_id) != len(rows):
        raise GoalieStartIdentityError(
            "Goalie-start evidence contained "
            "duplicate source player IDs."
        )

    resolutions = (
        resolve_goalie_start_identities(
            goalie_starts=rows,
            nhl_players=nhl_players,
            nhl_teams=nhl_teams,
            game_date=game_date,
            explicit_nhl_player_ids=(
                explicit_nhl_player_ids
            ),
        )
    )

    result = {}

    for resolution in resolutions:
        if (
            resolution.resolution_state
            != "resolved"
        ):
            continue

        if resolution.nhl_player_id is None:
            raise GoalieStartIdentityError(
                "Resolved goalie-start identity "
                "was missing NHL playerId."
            )

        source_player_id = str(
            resolution.provider_player_key
        )

        try:
            evidence = source_by_id[
                source_player_id
            ]
        except KeyError as exc:
            raise GoalieStartIdentityError(
                "Goalie-start identity referenced "
                "unknown source playerId."
            ) from exc

        nhl_player_id = int(
            resolution.nhl_player_id
        )

        if nhl_player_id in result:
            raise GoalieStartIdentityError(
                "One NHL playerId resolved from "
                "multiple goalie-start rows."
            )

        result[
            nhl_player_id
        ] = evidence

    return result
