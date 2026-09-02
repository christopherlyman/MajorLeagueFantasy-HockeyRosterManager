from __future__ import annotations

from typing import Any, Mapping


def merge_metadata_fragments(
    value: object,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    def visit(item: object) -> None:
        if isinstance(item, Mapping):
            result.update(item)
            return

        if isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)

    return result


def indexed_collection(
    value: Mapping[str, Any],
) -> list[Any]:
    numeric_keys = sorted(
        (
            key
            for key in value
            if str(key).isdigit()
        ),
        key=lambda key: int(key),
    )

    return [
        value[key]
        for key in numeric_keys
    ]


def optional_int(
    value: object,
) -> int | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return int(text)


def yahoo_bool(
    value: object,
) -> bool:
    if isinstance(value, bool):
        return value

    return str(value or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
