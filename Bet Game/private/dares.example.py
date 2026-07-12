"""Template for private/dares.py (git-ignored). Copy this file to
dares.py — without the .example — and edit freely; that copy will never be
committed. The content below is placeholder-only — do not build on top of
it, only the registration pattern.

Each dare is its own block below: a header naming the dare, its layout
functions numbered "_<dare>_layout_N", and the register() call listing them
in `layouts=`. A layout is drawn uniformly at random each time the dare
itself is drawn (see engine.dare.pick_dare) — counting the numbered
functions in a block tells you how many variants that dare has.
"""

from bet_game.engine.dare import Dare, register
from bet_game.models.gender import Gender

_ANY = frozenset({Gender.MALE, Gender.FEMALE})
_ALL_LEVELS = frozenset({1, 2, 3, 4})


# --- exemple_compliment ------------------------------------------------


def _compliment_layout_1(level, loser, partner):
    return f"{loser.name}, fais un compliment sincère à {partner.name}."


def _compliment_layout_2(level, loser, partner):
    return f"{loser.name}, dis à {partner.name} une chose que tu adores chez elle/lui."


register(
    Dare(
        key="exemple_compliment",
        levels=frozenset({1}),
        genders=_ANY,
        layouts=(_compliment_layout_1, _compliment_layout_2),
    )
)


# --- exemple_danse -------------------------------------------------------
# Unisex dare, scaled by level only: same text shape, growing intensity.

_DANCE_DURATION_BY_LEVEL = {1: 15, 2: 30, 3: 45, 4: 60}


def _danse_layout_1(level, loser, partner):
    return f"{loser.name}, danse pendant {_DANCE_DURATION_BY_LEVEL[level]} secondes, sans musique."


register(Dare(key="exemple_danse", levels=_ALL_LEVELS, genders=_ANY, layouts=(_danse_layout_1,)))


# --- exemple_pompes_homme / exemple_pompes_femme --------------------------
# Same sport dare, but the intensity range differs by gender at a given
# level (standard push-ups vs. knee push-ups), to respect physiological
# differences the way the user described.

_PUSHUPS_BY_LEVEL = {1: (5, 8), 2: (9, 12), 3: (13, 16), 4: (17, 20)}
_KNEE_PUSHUPS_BY_LEVEL = {1: (4, 6), 2: (7, 9), 3: (10, 12), 4: (13, 15)}


def _pompes_homme_layout_1(level, loser, partner):
    low, high = _PUSHUPS_BY_LEVEL[level]
    return f"{loser.name}, fais entre {low} et {high} pompes."


def _pompes_homme_layout_2(level, loser, partner):
    low, high = _PUSHUPS_BY_LEVEL[level]
    return f"{loser.name}, {low} à {high} pompes, à toi de jouer !"


def _pompes_femme_layout_1(level, loser, partner):
    low, high = _KNEE_PUSHUPS_BY_LEVEL[level]
    return f"{loser.name}, fais entre {low} et {high} pompes sur les genoux."


register(
    Dare(
        key="exemple_pompes_homme",
        levels=_ALL_LEVELS,
        genders=frozenset({Gender.MALE}),
        layouts=(_pompes_homme_layout_1, _pompes_homme_layout_2),
    )
)
register(
    Dare(
        key="exemple_pompes_femme",
        levels=_ALL_LEVELS,
        genders=frozenset({Gender.FEMALE}),
        layouts=(_pompes_femme_layout_1,),
    )
)


# --- exemple_portage -------------------------------------------------------
# Involves both players, but only triggers off one gender losing — the
# scenario the user asked for by name (only the man can be asked to carry).


def _portage_layout_1(level, loser, partner):
    return f"{loser.name}, tu dois faire un tour de jardin en portant {partner.name} sur ton dos."


register(
    Dare(
        key="exemple_portage",
        levels=frozenset({2, 3, 4}),
        genders=frozenset({Gender.MALE}),
        layouts=(_portage_layout_1,),
    )
)


# --- exemple_extreme ---------------------------------------------------


def _extreme_layout_1(level, loser, partner):
    return f"{loser.name} doit chanter une déclaration d'amour improvisée à {partner.name}."


register(Dare(key="exemple_extreme", levels=frozenset({4}), genders=_ANY, layouts=(_extreme_layout_1,)))
