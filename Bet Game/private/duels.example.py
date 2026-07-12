"""Template for private/duels.py (git-ignored). Copy this file to
duels.py — without the .example — and edit freely; that copy will never be
committed. DUEL minigames (competitive minigames whose loser gets a dare)
live here. The content below is placeholder-only — do not build on top of
it, only the registration pattern.

Each duel is its own block below: a header naming it, and its register()
call listing numbered "# Layout N" text variants in `layouts=`. One is
drawn uniformly at random each time the duel itself is drawn.
"""

from bet_game.engine.minigame import Minigame, MinigameCategory, register

# --- exemple_duel ----------------------------------------------------------

register(
    Minigame(
        key="exemple_duel",
        name="Exemple - Duel",
        category=MinigameCategory.DUEL,
        layouts=(
            # Layout 1
            "Le premier qui rit entre {homme} et {femme} perd.",
            # Layout 2
            "{homme} et {femme} se dévisagent : le premier qui craque et rit a perdu.",
        ),
    )
)

# --- exemple_duel_intense ---------------------------------------------------
# Reserved for the later, harder rounds — demonstrates level-based
# filtering: this minigame simply won't be drawn at levels 1-2.

register(
    Minigame(
        key="exemple_duel_intense",
        name="Exemple - Duel intense",
        category=MinigameCategory.DUEL,
        layouts=(
            # Layout 1
            "{homme} et {femme} s'affrontent en combat de regard. Le premier qui cligne des yeux ou rit perd.",
        ),
        levels=frozenset({3, 4}),
    )
)
