from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from decimal import (
    Decimal,
    InvalidOperation,
)

from hockey_rmt.providers.yahoo.client import (
    YahooClient,
)
from hockey_rmt.providers.yahoo.ownership import (
    indexed_collection,
    merge_metadata_fragments,
)


class YahooPercentRosteredError(
    ValueError
):
    pass


def _percent_value(
    raw_percent_owned: object,
) -> int:
    if isinstance(
        raw_percent_owned,
        Mapping,
    ):
        metadata = dict(
            raw_percent_owned
        )

    elif isinstance(
        raw_percent_owned,
        list,
    ):
        metadata = (
            merge_metadata_fragments(
                raw_percent_owned
            )
        )

    else:
        raise YahooPercentRosteredError(
            "percent_owned must be a mapping "
            "or metadata-fragment list."
        )

    coverage_type = str(
        metadata.get(
            "coverage_type",
            "",
        )
    ).strip()

    if coverage_type != "week":
        raise YahooPercentRosteredError(
            "percent_owned coverage_type must "
            f"be 'week'; found {coverage_type!r}."
        )

    raw_value = metadata.get(
        "value"
    )

    if raw_value is None:
        return 0

    try:
        value = Decimal(
            str(
                raw_value
            )
        )

    except InvalidOperation as exc:
        raise YahooPercentRosteredError(
            "percent_owned value must be "
            f"numeric; found {raw_value!r}."
        ) from exc

    if value != value.to_integral_value():
        raise YahooPercentRosteredError(
            "percent_owned value must be "
            f"an integer; found {value!r}."
        )

    integer_value = int(
        value
    )

    if (
        integer_value < 0
        or integer_value > 100
    ):
        raise YahooPercentRosteredError(
            "percent_owned value must be "
            "between 0 and 100; found "
            f"{integer_value}."
        )

    return integer_value


def parse_player_percent_rostered(
    payload: Mapping[
        str,
        object,
    ],
) -> dict[
    str,
    int,
]:
    try:
        league = payload[
            "fantasy_content"
        ][
            "league"
        ]

        collection = league[
            1
        ][
            "players"
        ]

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise YahooPercentRosteredError(
            "Yahoo percent_owned payload "
            "does not contain the expected "
            "league player collection."
        ) from exc

    result: dict[
        str,
        int,
    ] = {}

    for entry in indexed_collection(
        collection
    ):
        try:
            player = (
                merge_metadata_fragments(
                    entry[
                        "player"
                    ]
                )
            )

        except (
            KeyError,
            TypeError,
        ) as exc:
            raise YahooPercentRosteredError(
                "Yahoo percent_owned player "
                "entry is malformed."
            ) from exc

        player_key = str(
            player.get(
                "player_key",
                "",
            )
        ).strip()

        if not player_key:
            raise YahooPercentRosteredError(
                "Yahoo percent_owned player "
                "entry has no player_key."
            )

        if player_key in result:
            raise YahooPercentRosteredError(
                "Yahoo percent_owned payload "
                "contains duplicate player key "
                f"{player_key!r}."
            )

        if "percent_owned" not in player:
            raise YahooPercentRosteredError(
                "Yahoo player entry does not "
                "contain percent_owned for "
                f"{player_key!r}."
            )

        result[
            player_key
        ] = _percent_value(
            player[
                "percent_owned"
            ]
        )

    return result


def fetch_player_percent_rostered(
    client: YahooClient,
    league_key: str,
    player_keys: Sequence[
        str,
    ],
) -> dict[
    str,
    int,
]:
    keys = tuple(
        str(
            key
        ).strip()
        for key in player_keys
    )

    if any(
        not key
        for key in keys
    ):
        raise YahooPercentRosteredError(
            "player_keys must not contain "
            "blank values."
        )

    if len(keys) != len(
        set(
            keys
        )
    ):
        raise YahooPercentRosteredError(
            "player_keys must not contain "
            "duplicates."
        )

    if not keys:
        return {}

    joined = ",".join(
        keys
    )

    payload = client.get_json(
        f"/league/{league_key}/"
        f"players;player_keys={joined}/"
        "percent_owned"
    )

    result = (
        parse_player_percent_rostered(
            payload
        )
    )

    if set(
        result
    ) != set(
        keys
    ):
        raise YahooPercentRosteredError(
            "Yahoo percent_owned response "
            "did not exactly match requested "
            "player keys."
        )

    return result


def fetch_all_player_percent_rostered(
    client: YahooClient,
    league_key: str,
    player_keys: Sequence[
        str,
    ],
    *,
    batch_size: int = 25,
) -> dict[
    str,
    int,
]:
    if batch_size <= 0:
        raise YahooPercentRosteredError(
            "batch_size must be positive."
        )

    keys = tuple(
        str(
            key
        ).strip()
        for key in player_keys
    )

    if any(
        not key
        for key in keys
    ):
        raise YahooPercentRosteredError(
            "player_keys must not contain "
            "blank values."
        )

    if len(keys) != len(
        set(
            keys
        )
    ):
        raise YahooPercentRosteredError(
            "player_keys must not contain "
            "duplicates."
        )

    result: dict[
        str,
        int,
    ] = {}

    for start in range(
        0,
        len(keys),
        batch_size,
    ):
        batch = keys[
            start:
            start + batch_size
        ]

        fetched = (
            fetch_player_percent_rostered(
                client,
                league_key,
                batch,
            )
        )

        overlap = (
            set(result)
            .intersection(
                fetched
            )
        )

        if overlap:
            raise YahooPercentRosteredError(
                "Yahoo percent_owned batches "
                "returned duplicate keys."
            )

        result.update(
            fetched
        )

    if set(
        result
    ) != set(
        keys
    ):
        raise YahooPercentRosteredError(
            "Yahoo percent_owned full fetch "
            "did not exactly cover requested "
            "player keys."
        )

    return result
