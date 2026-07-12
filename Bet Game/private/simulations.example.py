"""Template for private/simulations.py (git-ignored). Copy this file to
simulations.py — without the .example — and edit freely; that copy will
never be committed. IMPRO minigames (scenarios to act out) live here. The
content below is placeholder-only — do not build on top of it, only the
registration pattern.

Each simulation is its own block below: a header naming it, and its
register() call listing numbered "# Layout N" text variants in `layouts=`.
One is drawn uniformly at random each time the simulation itself is drawn.
"""

from bet_game.engine.minigame import Minigame, MinigameCategory, register

# --- exemple_impro -------------------------------------------------------

register(
    Minigame(
        key="exemple_impro",
        name="Exemple - Impro",
        category=MinigameCategory.IMPRO,
        layouts=(
            # Layout 1
            "{homme} et {femme} sont deux astronautes qui réalisent, en "
            "pleine mission, qu'il ne reste plus de café à bord.",
            # Layout 2
            "Rejouez la première rencontre entre {homme} et {femme}, mais "
            "l'un des deux est persuadé de l'avoir déjà rencontré dans une "
            "autre vie.",
        ),
        duration_seconds=90,
    )
)
