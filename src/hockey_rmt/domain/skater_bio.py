from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SkaterBio:
    nhl_player_id: int
    full_name: str
    birth_date: date
    position_code: str
    shoots_catches: str | None
    height_inches: int
    weight_pounds: int
    nationality_code: str
    first_season_for_game_type: int
    draft_year: int | None
    draft_round: int | None
    draft_overall: int | None
