from __future__ import annotations


# Manually reviewed Daily Faceoff playerId -> NHL playerId mappings.
#
# These are used only when the normal deterministic exact-name + exact-team
# resolver cannot reconcile a legitimate provider display-name difference.
#
# Every mapping must be verified against official NHL identity evidence.
REVIEWED_NHL_PLAYER_ID_OVERRIDES: dict[
    str,
    int,
] = {
    # Daily Faceoff "Matthew Savoie" -> official NHL "Matt Savoie".
    # Verified on 2026-09-06 against:
    # - official NHL player landing data;
    # - official NHL current Edmonton roster.
    "31504": 8483512,
}
