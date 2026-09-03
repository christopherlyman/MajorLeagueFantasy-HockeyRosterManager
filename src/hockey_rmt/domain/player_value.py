from __future__ import annotations

from dataclasses import dataclass

from hockey_rmt.domain.player import Player
from hockey_rmt.domain.player_identity import (
    PlayerIdentityResolution,
)
from hockey_rmt.domain.player_stats import (
    HistoricalFantasyValue,
)


HISTORICAL_VALUE_AVAILABLE = (
    "historical_value_available"
)

RESOLVED_NO_HISTORY = (
    "resolved_no_history"
)

IDENTITY_UNRESOLVED = (
    "identity_unresolved"
)


@dataclass(frozen=True)
class PlayerHistoricalBaseline:
    player: Player
    identity: PlayerIdentityResolution
    coverage_state: str
    historical_value: HistoricalFantasyValue | None
