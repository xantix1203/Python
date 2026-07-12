"""The minigame plugin interface: every minigame the players can be handed
registers itself here, and the round engine picks among whatever is
registered for the game's current difficulty level, without knowing the
specifics of any one of them.

Two categories exist because they resolve differently on screen:
  - IMPRO: the app shows a scenario and a duration, the players act it out
    in real life, and nothing is won or lost.
  - DUEL: the app shows instructions for a real-life minigame; once the
    players report who lost, a dare is drawn for them (see engine.dare —
    dares are game-wide, not tied to which minigame was played).

`layouts` holds one or more alternate phrasings of that scenario/instruction
text (for either category) — a random one is drawn each time the minigame
itself is drawn, so repeats don't read identically.

No concrete minigames are implemented here — see private/simulations.py
(IMPRO) and private/duels.py (DUEL), both git-ignored; copy the matching
*.example.py to get started.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

from ..config import MAX_DARE_LEVEL

_ALL_LEVELS = frozenset(range(1, MAX_DARE_LEVEL + 1))


class MinigameCategory(Enum):
    IMPRO = auto()
    DUEL = auto()


@dataclass(frozen=True)
class Minigame:
    key: str
    name: str
    category: MinigameCategory
    layouts: tuple = field(default_factory=tuple)  # alternate phrasings; one is drawn at random
    duration_seconds: int = 60  # IMPRO only: how long the scene runs
    # Which difficulty levels this minigame can be drawn at (1-4, same
    # brackets as dares — see engine.game.Game.level). Defaults to every
    # level, so a minigame only needs this set to restrict when it escalates
    # (e.g. an intense minigame reserved for the later, harder rounds).
    levels: frozenset = field(default_factory=lambda: _ALL_LEVELS)


_registry: dict[str, Minigame] = {}


def register(minigame: Minigame) -> Minigame:
    if minigame.key in _registry:
        raise ValueError(f"Minigame already registered: {minigame.key}")
    _registry[minigame.key] = minigame
    return minigame


def all_minigames() -> list[Minigame]:
    return list(_registry.values())


def clear_registry():
    """Test hook: registration is normally a one-way, import-time side effect."""
    _registry.clear()
