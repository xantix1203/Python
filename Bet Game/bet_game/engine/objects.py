"""The starting-objects plugin interface, and the "remove an object" dare
mechanic. Each player picks, at setup, which objects from their gender's
pool they have in front of them. Some objects sit on top of others and can
only be removed once the object underneath is already gone (`requires`).

Every object also carries its French grammatical gender (`noun_gender`), so
the generated dare text can use the correct possessive article and pronoun
("ta feuille" / "pose-la" vs. "ton bol" / "pose-le") — not the player's own
gender, which is unrelated.

Which objects exist per gender, and their removal-order constraints, live
in private/objects.py (git-ignored) — see private/objects.example.py for
the tracked template.
"""

import random
from dataclasses import dataclass
from enum import Enum, auto

_VOWEL_SOUNDS = "aàâäeéèêëiîïoôöuùûüyh"


class NounGender(Enum):
    MASCULINE = auto()
    FEMININE = auto()


@dataclass(frozen=True)
class ObjectSpec:
    key: str
    gender: object  # models.gender.Gender — whose pool this belongs to
    noun_gender: NounGender  # grammatical gender of the French noun
    requires: str = None  # key of the object that must be removed first, if any


_registry: dict[str, ObjectSpec] = {}


def register(spec: ObjectSpec) -> ObjectSpec:
    if spec.key in _registry:
        raise ValueError(f"Object already registered: {spec.key}")
    _registry[spec.key] = spec
    return spec


def objects_for(gender) -> list[ObjectSpec]:
    return [spec for spec in _registry.values() if spec.gender == gender]


def clear_registry():
    """Test hook: registration is normally a one-way, import-time side effect."""
    _registry.clear()


def removable_objects(player) -> list[str]:
    """Keys the player could be asked to remove right now: still in front of
    them, and not blocked by a still-present object stacked on top of them.
    """
    removed_keys = {key for key, _level in player.removed_objects}
    remaining = player.starting_objects - removed_keys
    specs = {spec.key: spec for spec in objects_for(player.gender)}
    return [key for key in remaining if specs[key].requires is None or specs[key].requires in removed_keys]


def has_removed_this_level(player, level) -> bool:
    return any(removal_level == level for _, removal_level in player.removed_objects)


def _determiner(key, noun_gender):
    # "ton" also fronts feminine nouns starting with a vowel sound (euphony:
    # "ton assiette", never "ta assiette").
    if noun_gender == NounGender.MASCULINE or key[0].lower() in _VOWEL_SOUNDS:
        return "ton"
    return "ta"


def _pronoun(noun_gender):
    return "le" if noun_gender == NounGender.MASCULINE else "la"


def trigger_object_removal(player, level):
    """Picks one removable object for `player` (only one — a player can only
    be asked to remove one item at once), marks it removed at `level`, and
    returns the dare text. Returns None if nothing is removable.
    """
    candidates = removable_objects(player)
    if not candidates:
        return None
    key = random.choice(candidates)
    player.removed_objects.append((key, level))
    spec = _registry[key]
    determiner = _determiner(key, spec.noun_gender)
    pronoun = _pronoun(spec.noun_gender)
    return f"{player.name}, retire {determiner} {key.lower()} et pose-{pronoun} par terre."
