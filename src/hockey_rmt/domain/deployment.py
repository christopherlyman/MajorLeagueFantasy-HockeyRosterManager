from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


DEPLOYMENT_SOURCE_DAILY_FACEOFF = "daily_faceoff"

CATEGORY_EVEN_STRENGTH = "ev"
CATEGORY_POWER_PLAY = "pp"
CATEGORY_PENALTY_KILL = "pk"


@dataclass(frozen=True)
class DeploymentAssignment:
    category_identifier: str
    category_name: str
    group_identifier: str
    group_name: str
    position_identifier: str
    position_name: str


@dataclass(frozen=True)
class SourcePlayerDeployment:
    source: str

    source_player_id: str
    full_name: str
    team_abbreviation: str

    injury_status: str | None
    game_time_decision: bool

    assignments: tuple[
        DeploymentAssignment,
        ...,
    ]


@dataclass(frozen=True)
class SourceTeamDeploymentSnapshot:
    source: str

    team_abbreviation: str
    team_name: str
    team_slug: str

    source_name: str
    source_updated_at: datetime
    source_url: str

    players: tuple[
        SourcePlayerDeployment,
        ...,
    ]
