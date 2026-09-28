from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeagueInstanceConfig:
    """Season-specific provider binding for a stable league."""

    logical_key: str
    display_name: str
    provider: str
    season_year: int
    provider_league_key: str
    managed_team_key: str
    competition_level: str | None = None


_LEAGUE_INSTANCES = {
    "nfhl_redraft": LeagueInstanceConfig(
        logical_key="nfhl_redraft",
        display_name="NFHL Redraft",
        provider="yahoo",
        season_year=2026,
        provider_league_key="477.l.10961",
        managed_team_key="477.l.10961.t.1",
    ),
    "oth_redraft": LeagueInstanceConfig(
        logical_key="oth_redraft",
        display_name="OTH Redraft",
        provider="fleaflicker",
        season_year=2026,
        provider_league_key="12090",
        managed_team_key="63197",
        competition_level="D3",
    ),
}


def get_league_instance(
    logical_key: str,
) -> LeagueInstanceConfig:
    key = logical_key.strip()

    if not key:
        raise ValueError(
            "Logical league key must not be empty."
        )

    try:
        return _LEAGUE_INSTANCES[key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown logical league key {key!r}."
        ) from exc


def league_instance_keys() -> tuple[str, ...]:
    return tuple(_LEAGUE_INSTANCES)
