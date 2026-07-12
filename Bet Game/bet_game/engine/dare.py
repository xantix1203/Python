"""The dare plugin interface: dares register themselves with the levels and
genders they're valid for, and the game draws one that matches the current
difficulty level and the loser's gender when a DUEL minigame is lost.

A dare carries one or more `layouts` — alternate phrasings of the same
action — and a random one is chosen each time the dare itself is drawn, so
repeat dares don't read identically. Each layout is a
`describe(level, loser, partner)` callback given both players, not just the
loser, since a dare can involve both of them even though only one gender's
loss triggers it (e.g. a MALE-only dare "carry your partner" still needs to
name both players). Most layouts ignore `level` and just return static
text, but a layout can use it to scale intensity (e.g. "2 to 5 jumping
jacks" at level 1 vs. "10 to 12" at level 4), and/or use `loser`/`partner`
genders to compute a different intensity per player (e.g. push-up counts,
to respect physiological differences on sport dares) — see
private/dares.example.py for placeholder examples of both.

No real dare content lives here — see private/dares.py (git-ignored; copy
private/dares.example.py to get started).
"""

import random
from dataclasses import dataclass
from typing import Callable

from ..models.player import Player

MIN_LEVEL = 1
MAX_LEVEL = 4

Layout = Callable[[int, Player, Player], str]


@dataclass(frozen=True)
class Dare:
    key: str
    levels: frozenset
    genders: frozenset  # whose loss triggers this dare
    layouts: tuple  # tuple[Layout, ...] — alternate phrasings; one is drawn at random


def static_text(text):
    """Build a layout callback for a phrasing that never changes."""
    return lambda level, loser, partner: text


_registry: dict[str, Dare] = {}


def register(dare: Dare) -> Dare:
    if dare.key in _registry:
        raise ValueError(f"Dare already registered: {dare.key}")
    _registry[dare.key] = dare
    return dare


def all_dares() -> list[Dare]:
    return list(_registry.values())


def clear_registry():
    """Test hook: registration is normally a one-way, import-time side effect."""
    _registry.clear()


def eligible_dares(level, gender) -> list[Dare]:
    return [dare for dare in all_dares() if level in dare.levels and gender in dare.genders]


def render_dare(dare: Dare, level, loser, partner) -> str:
    layout = random.choice(dare.layouts)
    return layout(level, loser, partner)


def pick_dare(level, loser, partner):
    pool = eligible_dares(level, loser.gender)
    if not pool:
        return "Improvise un gage !"
    dare = random.choice(pool)
    return render_dare(dare, level, loser, partner)
