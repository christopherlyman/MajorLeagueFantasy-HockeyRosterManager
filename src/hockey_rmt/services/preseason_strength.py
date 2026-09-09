from __future__ import annotations

import math

from collections.abc import (
    Mapping,
    Sequence,
)

from hockey_rmt.domain.goalie_workload import (
    GoalieWorkloadProjection,
)
from hockey_rmt.domain.nhl_roster import (
    CurrentNhlGoalie,
)
from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    PlayerIdentityResolution,
)
from hockey_rmt.domain.player_profile import (
    NhlPlayerProfile,
)
from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)
from hockey_rmt.domain.player_strength import (
    PlayerStrengthProjection,
)
from hockey_rmt.domain.skater_bio import (
    SkaterBio,
)

from hockey_rmt.services.goalie_projection import (
    build_preseason_goalie_projections,
)
from hockey_rmt.services.historical_projection import (
    build_historical_rate_projections,
)
from hockey_rmt.services.player_strength import (
    build_player_strength_projections,
)
from hockey_rmt.services.returner_projection import (
    project_long_absence_skater,
)
from hockey_rmt.services.rookie_projection import (
    fit_rookie_skater_projection_model,
    project_rookie_skater,
)
from hockey_rmt.services.skater_projection import (
    calibrate_skater_projection,
    fit_skater_projection_calibration,
)


class PreseasonStrengthAssemblyError(
    ValueError
):
    """Preseason canonical-strength assembly failed."""


HISTORICAL_BASELINE_SEASONS = 3
DEFAULT_ROOKIE_TRAINING_SEASONS = 4


def _season_years(
    season_id: int,
) -> tuple[int, int]:
    value = int(
        season_id
    )

    text = str(
        value
    )

    if len(text) != 8:
        raise PreseasonStrengthAssemblyError(
            "NHL season id must contain eight digits: "
            f"{season_id!r}."
        )

    start = int(
        text[:4]
    )
    end = int(
        text[4:]
    )

    if end != start + 1:
        raise PreseasonStrengthAssemblyError(
            "NHL season id must represent consecutive "
            f"years: {season_id!r}."
        )

    return (
        start,
        end,
    )


def _shift_season(
    season_id: int,
    years: int,
) -> int:
    start, end = _season_years(
        season_id
    )

    shift = int(
        years
    )

    return int(
        f"{start + shift:04d}"
        f"{end + shift:04d}"
    )


def _prior_seasons(
    projection_season_id: int,
    count: int,
) -> tuple[int, ...]:
    count = int(
        count
    )

    if count <= 0:
        raise PreseasonStrengthAssemblyError(
            "Prior-season count must be positive."
        )

    return tuple(
        _shift_season(
            projection_season_id,
            -offset,
        )
        for offset in range(
            count,
            0,
            -1,
        )
    )


def _validate_player_identity_coverage(
    *,
    players: Sequence[Player],
    identity_resolutions: Sequence[
        PlayerIdentityResolution
    ],
) -> dict[
    str,
    PlayerIdentityResolution,
]:
    player_keys = [
        player.provider_player_key
        for player in players
    ]

    if len(player_keys) != len(set(player_keys)):
        raise PreseasonStrengthAssemblyError(
            "Player universe contained duplicate "
            "provider player keys."
        )

    identity_by_key = {}

    for identity in identity_resolutions:
        key = (
            identity.provider_player_key
        )

        if key in identity_by_key:
            raise PreseasonStrengthAssemblyError(
                "Identity resolutions contained "
                f"duplicate player key {key!r}."
            )

        identity_by_key[key] = identity

    if set(identity_by_key) != set(player_keys):
        raise PreseasonStrengthAssemblyError(
            "Identity coverage did not exactly "
            "match the player universe."
        )

    return identity_by_key


def _split_historical_values(
    *,
    historical_values_by_season: Mapping[
        int,
        Sequence[
            HistoricalFantasyValue
        ],
    ],
    required_seasons: Sequence[int],
) -> tuple[
    dict[
        int,
        tuple[
            HistoricalFantasyValue,
            ...,
        ],
    ],
    dict[
        int,
        tuple[
            HistoricalFantasyValue,
            ...,
        ],
    ],
]:
    skaters = {}
    goalies = {}

    for season_id in required_seasons:
        season = int(
            season_id
        )

        values = (
            historical_values_by_season.get(
                season
            )
        )

        if values is None:
            raise PreseasonStrengthAssemblyError(
                "Historical fantasy values were "
                "missing required season "
                f"{season}."
            )

        skater_rows = []
        goalie_rows = []
        seen_ids = set()

        for value in values:
            if int(value.season_id) != season:
                raise PreseasonStrengthAssemblyError(
                    "Historical fantasy value season "
                    "did not match mapping key."
                )

            player_id = int(
                value.nhl_player_id
            )

            if player_id in seen_ids:
                raise PreseasonStrengthAssemblyError(
                    "Historical fantasy values contained "
                    "duplicate NHL playerId "
                    f"{player_id} in season {season}."
                )

            seen_ids.add(
                player_id
            )

            if value.player_type == "skater":
                skater_rows.append(
                    value
                )

            elif value.player_type == "goalie":
                goalie_rows.append(
                    value
                )

            else:
                raise PreseasonStrengthAssemblyError(
                    "Historical fantasy value contained "
                    "unsupported player type "
                    f"{value.player_type!r}."
                )

        skaters[season] = tuple(
            skater_rows
        )

        goalies[season] = tuple(
            goalie_rows
        )

    return (
        skaters,
        goalies,
    )


def _validate_bios(
    *,
    skater_bios_by_season: Mapping[
        int,
        Sequence[
            SkaterBio
        ],
    ],
    required_seasons: Sequence[int],
) -> dict[
    int,
    tuple[
        SkaterBio,
        ...,
    ],
]:
    result = {}

    for season_id in required_seasons:
        season = int(
            season_id
        )

        bios = (
            skater_bios_by_season.get(
                season
            )
        )

        if bios is None:
            raise PreseasonStrengthAssemblyError(
                "Skater bios were missing required "
                f"season {season}."
            )

        seen_ids = set()

        for bio in bios:
            player_id = int(
                bio.nhl_player_id
            )

            if player_id in seen_ids:
                raise PreseasonStrengthAssemblyError(
                    "Skater bios contained duplicate "
                    f"NHL playerId {player_id} "
                    f"in season {season}."
                )

            seen_ids.add(
                player_id
            )

        result[season] = tuple(
            bios
        )

    return result


def _latest_bio_by_id(
    bios_by_season: Mapping[
        int,
        Sequence[
            SkaterBio
        ],
    ],
) -> dict[
    int,
    SkaterBio,
]:
    result = {}

    for season_id in sorted(
        bios_by_season
    ):
        for bio in bios_by_season[
            season_id
        ]:
            result[
                int(
                    bio.nhl_player_id
                )
            ] = bio

    return result


def _profile_map(
    profiles_by_nhl_id: Mapping[
        int,
        NhlPlayerProfile,
    ],
) -> dict[
    int,
    NhlPlayerProfile,
]:
    result = {}

    for raw_id, profile in (
        profiles_by_nhl_id.items()
    ):
        player_id = int(
            raw_id
        )

        if int(profile.nhl_player_id) != player_id:
            raise PreseasonStrengthAssemblyError(
                "Player profile mapping key did "
                "not match profile NHL playerId."
            )

        result[player_id] = profile

    return result


def _completed_skater_population_fppg(
    *,
    season_id: int,
    values: Sequence[
        HistoricalFantasyValue
    ],
) -> float:
    fantasy_points = 0.0
    games_played = 0

    for value in values:
        if value.player_type != "skater":
            continue

        if int(value.season_id) != int(season_id):
            raise PreseasonStrengthAssemblyError(
                "Population-prior historical "
                "season mismatch."
            )

        if value.games_played <= 0:
            continue

        points = float(
            value.fantasy_points
        )

        if not math.isfinite(
            points
        ):
            raise PreseasonStrengthAssemblyError(
                "Population-prior fantasy points "
                "were not finite."
            )

        fantasy_points += points
        games_played += int(
            value.games_played
        )

    if games_played <= 0:
        raise PreseasonStrengthAssemblyError(
            "No completed-season skater games "
            "were available for the population prior."
        )

    rate = (
        fantasy_points
        / games_played
    )

    if (
        not math.isfinite(rate)
        or rate <= 0
    ):
        raise PreseasonStrengthAssemblyError(
            "Completed-season skater population "
            "FPPG was invalid."
        )

    return rate


def build_preseason_player_strengths(
    *,
    projection_season_id: int,
    players: Sequence[
        Player
    ],
    identity_resolutions: Sequence[
        PlayerIdentityResolution
    ],
    historical_values_by_season: Mapping[
        int,
        Sequence[
            HistoricalFantasyValue
        ],
    ],
    skater_bios_by_season: Mapping[
        int,
        Sequence[
            SkaterBio
        ],
    ],
    profiles_by_nhl_id: Mapping[
        int,
        NhlPlayerProfile,
    ],
    current_nhl_goalies: Sequence[
        CurrentNhlGoalie
    ],
    external_goalie_workload: Sequence[
        GoalieWorkloadProjection
    ] | None = None,
    fallback_goalie_starts_by_nhl_id: (
        Mapping[int, float]
        | None
    ) = None,
    rookie_training_season_ids: (
        Sequence[int]
        | None
    ) = None,
) -> tuple[
    PlayerStrengthProjection,
    ...,
]:
    """
    Assemble canonical preseason strength from
    the existing Phase-3 projection families.

    Provider retrieval and historical fantasy
    scoring deliberately remain outside this
    service.
    """

    projection_season = int(
        projection_season_id
    )

    _season_years(
        projection_season
    )

    identity_by_key = (
        _validate_player_identity_coverage(
            players=players,
            identity_resolutions=(
                identity_resolutions
            ),
        )
    )

    projection_baseline_seasons = (
        _prior_seasons(
            projection_season,
            HISTORICAL_BASELINE_SEASONS,
        )
    )

    calibration_target_season = (
        _shift_season(
            projection_season,
            -1,
        )
    )

    calibration_baseline_seasons = (
        _prior_seasons(
            calibration_target_season,
            HISTORICAL_BASELINE_SEASONS,
        )
    )

    if rookie_training_season_ids is None:
        rookie_training_seasons = (
            _prior_seasons(
                projection_season,
                DEFAULT_ROOKIE_TRAINING_SEASONS,
            )
        )
    else:
        rookie_training_seasons = tuple(
            int(season)
            for season
            in rookie_training_season_ids
        )

        if not rookie_training_seasons:
            raise PreseasonStrengthAssemblyError(
                "Rookie training season set "
                "must not be empty."
            )

        if len(
            rookie_training_seasons
        ) != len(
            set(
                rookie_training_seasons
            )
        ):
            raise PreseasonStrengthAssemblyError(
                "Rookie training seasons "
                "contained duplicates."
            )

        if tuple(
            sorted(
                rookie_training_seasons
            )
        ) != rookie_training_seasons:
            raise PreseasonStrengthAssemblyError(
                "Rookie training seasons must "
                "be oldest to newest."
            )

    required_historical_seasons = tuple(
        sorted(
            set(
                projection_baseline_seasons
            )
            | set(
                calibration_baseline_seasons
            )
            | {
                calibration_target_season
            }
            | set(
                rookie_training_seasons
            )
        )
    )

    (
        skater_values,
        goalie_values,
    ) = _split_historical_values(
        historical_values_by_season=(
            historical_values_by_season
        ),
        required_seasons=(
            required_historical_seasons
        ),
    )

    required_bio_seasons = tuple(
        sorted(
            set(
                required_historical_seasons
            )
            | set(
                rookie_training_seasons
            )
        )
    )

    bios_by_season = (
        _validate_bios(
            skater_bios_by_season=(
                skater_bios_by_season
            ),
            required_seasons=(
                required_bio_seasons
            ),
        )
    )

    latest_bio = (
        _latest_bio_by_id(
            bios_by_season
        )
    )

    profiles = (
        _profile_map(
            profiles_by_nhl_id
        )
    )

    current_skater_ids = set()

    player_name_by_nhl_id = {}

    for player in players:
        if (
            str(
                player.position_type
            )
            .strip()
            .upper()
            == "G"
        ):
            continue

        identity = identity_by_key[
            player.provider_player_key
        ]

        if (
            identity.resolution_state
            == "resolved"
            and identity.nhl_player_id
            is not None
        ):
            player_id = int(
                identity.nhl_player_id
            )

            current_skater_ids.add(
                player_id
            )

            player_name_by_nhl_id[
                player_id
            ] = player.full_name

    training_baselines = (
        build_historical_rate_projections(
            player_type="skater",
            seasons=(
                calibration_baseline_seasons
            ),
            historical_values_by_season=(
                skater_values
            ),
        )
    )

    calibration = (
        fit_skater_projection_calibration(
            training_target_season_id=(
                calibration_target_season
            ),
            actual_values=(
                skater_values[
                    calibration_target_season
                ]
            ),
            baseline_projections=(
                training_baselines
            ),
            bios=(
                bios_by_season[
                    calibration_target_season
                ]
            ),
        )
    )

    projection_baselines = (
        build_historical_rate_projections(
            player_type="skater",
            seasons=(
                projection_baseline_seasons
            ),
            historical_values_by_season=(
                skater_values
            ),
        )
    )

    established_skater_projections = []

    for baseline in projection_baselines:
        player_id = int(
            baseline.nhl_player_id
        )

        if player_id not in current_skater_ids:
            continue

        bio = latest_bio.get(
            player_id
        )

        if bio is None:
            continue

        established_skater_projections.append(
            calibrate_skater_projection(
                baseline=baseline,
                bio=bio,
                calibration=calibration,
                projection_season_id=(
                    projection_season
                ),
            )
        )

    established_ids = {
        int(
            projection.nhl_player_id
        )
        for projection
        in established_skater_projections
    }

    unprojected_current_skater_ids = (
        current_skater_ids
        - established_ids
    )

    rookie_candidate_ids = []
    long_absence_candidate_ids = []

    for player_id in sorted(
        unprojected_current_skater_ids
    ):
        profile = profiles.get(
            player_id
        )

        if profile is None:
            continue

        if (
            profile
            .has_nhl_regular_season_history
        ):
            long_absence_candidate_ids.append(
                player_id
            )
        else:
            rookie_candidate_ids.append(
                player_id
            )

    rookie_skater_projections = []

    if rookie_candidate_ids:
        rookie_model = (
            fit_rookie_skater_projection_model(
                training_season_ids=(
                    rookie_training_seasons
                ),
                actual_values_by_season=(
                    skater_values
                ),
                bios_by_season=(
                    bios_by_season
                ),
            )
        )

        for player_id in (
            rookie_candidate_ids
        ):
            profile = profiles[
                player_id
            ]

            rookie_skater_projections.append(
                project_rookie_skater(
                    nhl_player_id=(
                        player_id
                    ),
                    full_name=(
                        player_name_by_nhl_id[
                            player_id
                        ]
                    ),
                    birth_date=(
                        profile.birth_date
                    ),
                    draft_overall=(
                        profile.draft_overall
                    ),
                    projection_season_id=(
                        projection_season
                    ),
                    model=rookie_model,
                )
            )

    long_absence_skater_projections = []

    if long_absence_candidate_ids:
        population_source_season = (
            _shift_season(
                projection_season,
                -1,
            )
        )

        population_mean = (
            _completed_skater_population_fppg(
                season_id=(
                    population_source_season
                ),
                values=(
                    skater_values[
                        population_source_season
                    ]
                ),
            )
        )

        for player_id in (
            long_absence_candidate_ids
        ):
            long_absence_skater_projections.append(
                project_long_absence_skater(
                    nhl_player_id=(
                        player_id
                    ),
                    full_name=(
                        player_name_by_nhl_id[
                            player_id
                        ]
                    ),
                    profile=(
                        profiles[
                            player_id
                        ]
                    ),
                    projection_season_id=(
                        projection_season
                    ),
                    population_source_season_id=(
                        population_source_season
                    ),
                    population_mean_fppg=(
                        population_mean
                    ),
                )
            )

    goalie_quality = (
        build_historical_rate_projections(
            player_type="goalie",
            seasons=(
                projection_baseline_seasons
            ),
            historical_values_by_season=(
                goalie_values
            ),
        )
    )

    goalie_projections = (
        build_preseason_goalie_projections(
            projection_season_id=(
                projection_season
            ),
            players=players,
            identity_resolutions=(
                identity_resolutions
            ),
            current_nhl_goalies=(
                current_nhl_goalies
            ),
            historical_quality=(
                goalie_quality
            ),
            external_workload=(
                external_goalie_workload
            ),
            fallback_projected_starts_by_nhl_id=(
                fallback_goalie_starts_by_nhl_id
            ),
        )
    )

    return build_player_strength_projections(
        projection_season_id=(
            projection_season
        ),
        players=players,
        identity_resolutions=(
            identity_resolutions
        ),
        established_skater_projections=tuple(
            established_skater_projections
        ),
        rookie_skater_projections=tuple(
            rookie_skater_projections
        ),
        long_absence_skater_projections=tuple(
            long_absence_skater_projections
        ),
        goalie_projections=(
            goalie_projections
        ),
    )
