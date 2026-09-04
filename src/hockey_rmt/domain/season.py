from __future__ import annotations


class HockeySeasonError(ValueError):
    """Canonical hockey season value was invalid."""


def nhl_season_id_from_start_year(
    start_year: int,
) -> int:
    year = int(
        start_year
    )

    if year < 1900 or year > 9998:
        raise HockeySeasonError(
            "NHL season start year must be "
            f"a four-digit year: {year!r}."
        )

    return int(
        f"{year:04d}{year + 1:04d}"
    )
