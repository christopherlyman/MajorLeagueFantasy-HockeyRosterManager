from __future__ import annotations


# Manually reviewed Yahoo 2026 player-key -> NHL playerId mappings.
#
# These are used only when deterministic exact-name identity resolution
# cannot reconcile legitimate provider display differences.
#
# Each mapping was verified against NHL search/landing identity evidence.

REVIEWED_NHL_PLAYER_ID_OVERRIDES: dict[str, int] = {
    "477.p.6544": 8478104,   # Samuel Blais -> Sammy Blais
    "477.p.6655": 8477919,   # Freddy Gaudreau -> Frederick Gaudreau
    "477.p.6827": 8478438,   # Thomas Novak -> Tommy Novak
    "477.p.7193": 8479372,   # Josh Mahura -> Joshua Mahura
    "477.p.7928": 8480813,   # Joseph Veleno -> Joe Veleno
    "477.p.8331": 8481582,   # Nicholas Robertson -> Nick Robertson
    "477.p.33674": 8485702,  # Max Shabanov -> Maxim Shabanov
}
