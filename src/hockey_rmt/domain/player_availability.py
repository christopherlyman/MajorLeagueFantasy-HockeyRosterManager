from __future__ import annotations


PLAYER_AVAILABILITY_AVAILABLE = (
    "available"
)

PLAYER_AVAILABILITY_UNCERTAIN = (
    "uncertain"
)

PLAYER_AVAILABILITY_UNAVAILABLE = (
    "unavailable"
)

VALID_PLAYER_AVAILABILITY_STATES = frozenset(
    {
        PLAYER_AVAILABILITY_AVAILABLE,
        PLAYER_AVAILABILITY_UNCERTAIN,
        PLAYER_AVAILABILITY_UNAVAILABLE,
    }
)


YAHOO_HARD_UNAVAILABLE_STATUSES = frozenset(
    {
        "NA",
        "O",
        "IR",
        "IR-LT",
        "IR-NR",
    }
)

YAHOO_UNCERTAIN_STATUSES = frozenset(
    {
        "DTD",
    }
)


def classify_player_availability(
    *,
    provider: str,
    status: str | None,
) -> str:
    normalized_status = str(
        status
        or ""
    ).strip().upper()

    if not normalized_status:
        return (
            PLAYER_AVAILABILITY_AVAILABLE
        )

    normalized_provider = str(
        provider
        or ""
    ).strip().casefold()

    if normalized_provider == "yahoo":
        if (
            normalized_status
            in YAHOO_HARD_UNAVAILABLE_STATUSES
        ):
            return (
                PLAYER_AVAILABILITY_UNAVAILABLE
            )

        if (
            normalized_status
            in YAHOO_UNCERTAIN_STATUSES
        ):
            return (
                PLAYER_AVAILABILITY_UNCERTAIN
            )

    return (
        PLAYER_AVAILABILITY_UNCERTAIN
    )
