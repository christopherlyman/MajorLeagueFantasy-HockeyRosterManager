from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class NhlPlayerProfile:
    nhl_player_id: int
    birth_date: date

    draft_year: int | None
    draft_round: int | None
    draft_overall: int | None

    nhl_regular_season_ids: tuple[int, ...]

    @property
    def has_nhl_regular_season_history(
        self,
    ) -> bool:
        return bool(
            self.nhl_regular_season_ids
        )
