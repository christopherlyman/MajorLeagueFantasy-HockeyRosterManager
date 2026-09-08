from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RankedDayValue:
    game_date: date

    nhl_team_abbr: str | None

    schedule_state: str
    value_state: str

    expected_fantasy_points: float | None
    daily_rank: int | None

    opponent_team_abbr: str | None = None
    home_away: str | None = None
    provider_game_id: str | None = None


@dataclass(frozen=True)
class ThreeDayPlayerRanking:
    provider_player_key: str
    full_name: str

    season_id: int
    player_type: str
    nhl_player_id: int | None

    base_date: date

    today: RankedDayValue
    tomorrow: RankedDayValue
    day_plus_2: RankedDayValue

    scheduled_games: int

    three_day_expected_fantasy_points: (
        float | None
    )

    three_day_rank: int | None
