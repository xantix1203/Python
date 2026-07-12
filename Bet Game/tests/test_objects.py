import pytest

from bet_game.config import ROUNDS_PER_LEVEL
from bet_game.engine.dare import Dare
from bet_game.engine.dare import clear_registry as clear_dare_registry
from bet_game.engine.dare import register as register_dare
from bet_game.engine.dare import static_text
from bet_game.engine.game import Game
from bet_game.engine.minigame import Minigame, MinigameCategory
from bet_game.engine.minigame import clear_registry as clear_minigame_registry
from bet_game.engine.minigame import register as register_minigame
from bet_game.engine.objects import NounGender, ObjectSpec
from bet_game.engine.objects import clear_registry as clear_object_registry
from bet_game.engine.objects import has_removed_this_level, objects_for, register, removable_objects, trigger_object_removal
from bet_game.models.gender import Gender
from bet_game.models.player import Player


@pytest.fixture(autouse=True)
def empty_registries():
    clear_object_registry()
    clear_dare_registry()
    clear_minigame_registry()
    yield
    clear_object_registry()
    clear_dare_registry()
    clear_minigame_registry()


def register_male_objects():
    register(ObjectSpec(key="verre", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))
    register(ObjectSpec(key="assiette", gender=Gender.MALE, noun_gender=NounGender.FEMININE, requires="verre"))
    register(ObjectSpec(key="cuillere", gender=Gender.MALE, noun_gender=NounGender.FEMININE))


def test_objects_for_filters_by_gender():
    register_male_objects()
    register(ObjectSpec(key="Pierre", gender=Gender.FEMALE, noun_gender=NounGender.FEMININE))

    assert {spec.key for spec in objects_for(Gender.MALE)} == {"verre", "assiette", "cuillere"}
    assert {spec.key for spec in objects_for(Gender.FEMALE)} == {"Pierre"}


def test_removable_objects_respects_starting_selection():
    register_male_objects()
    player = Player("Alex", Gender.MALE)
    player.starting_objects = {"verre", "cuillere"}  # didn't have "assiette" to begin with

    assert set(removable_objects(player)) == {"verre", "cuillere"}


def test_removable_objects_blocks_on_unmet_dependency():
    register_male_objects()
    player = Player("Alex", Gender.MALE)
    player.starting_objects = {"verre", "assiette"}

    # assiette is blocked until verre has been removed.
    assert removable_objects(player) == ["verre"]

    player.removed_objects.append(("verre", 1))
    assert set(removable_objects(player)) == {"assiette"}


def test_trigger_object_removal_marks_removal_and_returns_none_when_empty():
    register_male_objects()
    player = Player("Alex", Gender.MALE)
    player.starting_objects = {"verre"}

    text = trigger_object_removal(player, level=1)
    assert "Alex" in text
    assert "verre" in text
    assert player.removed_objects == [("verre", 1)]

    # Nothing left to remove.
    assert trigger_object_removal(player, level=1) is None


def test_trigger_object_removal_uses_correct_determiner_and_pronoun():
    register(ObjectSpec(key="bol", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))
    register(ObjectSpec(key="cuillere", gender=Gender.MALE, noun_gender=NounGender.FEMININE))
    register(ObjectSpec(key="assiette", gender=Gender.MALE, noun_gender=NounGender.FEMININE))

    masculine_player = Player("Alex", Gender.MALE)
    masculine_player.starting_objects = {"bol"}
    assert trigger_object_removal(masculine_player, 1) == "Alex, retire ton bol et pose-le par terre."

    feminine_consonant_player = Player("Sam", Gender.MALE)
    feminine_consonant_player.starting_objects = {"cuillere"}
    assert trigger_object_removal(feminine_consonant_player, 1) == "Sam, retire ta cuillere et pose-la par terre."

    # Feminine noun starting with a vowel sound still takes "ton" (euphony).
    feminine_vowel_player = Player("Jo", Gender.MALE)
    feminine_vowel_player.starting_objects = {"assiette"}
    assert trigger_object_removal(feminine_vowel_player, 1) == "Jo, retire ton assiette et pose-la par terre."


def test_has_removed_this_level():
    player = Player("Alex", Gender.MALE)
    assert not has_removed_this_level(player, 1)
    player.removed_objects.append(("verre", 1))
    assert has_removed_this_level(player, 1)
    assert not has_removed_this_level(player, 2)


def test_resolve_duel_can_trigger_object_removal_when_no_text_dares_registered():
    register_minigame(Minigame(key="duel", name="Duel", category=MinigameCategory.DUEL))
    register(ObjectSpec(key="verre", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))

    male = Player("Alex", Gender.MALE)
    male.starting_objects = {"verre"}
    game = Game(male, Player("Sam", Gender.FEMALE))
    game.next_round()

    game.resolve_duel(male)

    assert male.removed_objects == [("verre", 1)]
    assert "verre" in game.current_round.gage


def test_object_removal_is_not_offered_twice_in_the_same_level():
    register_minigame(Minigame(key="duel", name="Duel", category=MinigameCategory.DUEL))
    register(ObjectSpec(key="verre", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))
    register(ObjectSpec(key="bol", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))

    male = Player("Alex", Gender.MALE)
    male.starting_objects = {"verre", "bol"}
    game = Game(male, Player("Sam", Gender.FEMALE))

    game.next_round()
    game.resolve_duel(male)
    assert len(male.removed_objects) == 1  # first loss used up this level's object removal

    game.next_round()
    game.resolve_duel(male)
    # Still within level 1 (ROUNDS_PER_LEVEL >= 2 assumed): no second object
    # removal, and no text dares registered either, so the fallback fires.
    assert len(male.removed_objects) == 1
    assert game.current_round.gage == "Improvise un gage !"


def test_next_round_catches_up_missed_object_removal_at_level_change():
    register_minigame(Minigame(key="impro", name="Impro", category=MinigameCategory.IMPRO, layouts=("x",)))
    register(ObjectSpec(key="verre", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))
    register(ObjectSpec(key="Pierre", gender=Gender.FEMALE, noun_gender=NounGender.FEMININE))

    male, female = Player("Alex", Gender.MALE), Player("Sam", Gender.FEMALE)
    male.starting_objects = {"verre"}
    female.starting_objects = {"Pierre"}
    game = Game(male, female)

    for _ in range(ROUNDS_PER_LEVEL):
        game.next_round()
        assert game.pending_object_removals == []  # still level 1, no boundary crossed yet

    game.next_round()  # first round of level 2: neither player was asked during level 1
    removed_names = {player.name for player, _text in game.pending_object_removals}
    assert removed_names == {"Alex", "Sam"}
    assert male.removed_objects == [("verre", 1)]
    assert female.removed_objects == [("Pierre", 1)]


def test_next_round_skips_catch_up_if_already_removed_via_duel():
    register_minigame(Minigame(key="duel", name="Duel", category=MinigameCategory.DUEL))
    register(ObjectSpec(key="verre", gender=Gender.MALE, noun_gender=NounGender.MASCULINE))
    register(ObjectSpec(key="Pierre", gender=Gender.FEMALE, noun_gender=NounGender.FEMININE))
    register_dare(Dare(key="noop", levels=frozenset({1}), genders=frozenset({Gender.FEMALE}), layouts=(static_text("x"),)))

    male, female = Player("Alex", Gender.MALE), Player("Sam", Gender.FEMALE)
    male.starting_objects = {"verre"}
    female.starting_objects = {"Pierre"}
    game = Game(male, female)

    game.next_round()
    game.resolve_duel(male)  # male already asked to remove "verre" during level 1
    assert male.removed_objects == [("verre", 1)]

    for _ in range(ROUNDS_PER_LEVEL - 1):
        game.next_round()

    game.next_round()  # crosses into level 2
    removed_names = {player.name for player, _text in game.pending_object_removals}
    assert removed_names == {"Sam"}  # Alex already covered via the duel loss, Sam wasn't yet
