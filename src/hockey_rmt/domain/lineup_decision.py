from __future__ import annotations

from dataclasses import dataclass


ACTION_START = "START"
ACTION_BENCH = "BENCH"
ACTION_HOLD = "HOLD"


@dataclass(frozen=True)
class DailyLineupDecision:
    provider_player_key: str
    full_name: str
    day_key: str

    action: str
    assigned_position: str | None
    expected_points: float | None
    reason: str
