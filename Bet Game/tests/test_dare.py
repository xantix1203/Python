import pytest

from bet_game.config import MAX_DARE_LEVEL, ROUNDS_PER_LEVEL
from bet_game.engine.dare import Dare, clear_registry, pick_dare, register, static_text
from bet_game.engine.game import Game
from bet_game.engine.minigame import Minigame, MinigameCategory
from bet_game.engine.minigame import clear_registry as clear_minigame_registry
from bet_game.engine.minigame import register as register_minigame
from bet_game.models.gender import Gender
from bet_game.models.player import Player


@pytest.fixture(autouse=True)
def empty_registries():
    clear_registry()
    clear_minigame_registry()
    yield
    clear_registry()
    clear_minigame_registry()


_MALE = Player("Alex", Gender.MALE)
_FEMALE = Player("Sam", Gender.FEMALE)


def test_pick_dare_falls_back_when_pool_is_empty():
    assert pick_dare(1, _MALE, _FEMALE) == "Improvise un gage !"


def test_pick_dare_only_matches_level_and_losers_gender():
    register(Dare(key="m1", levels=frozenset({1}), genders=frozenset({Gender.MALE}), layouts=(static_text("M1"),)))
    register(Dare(key="f1", levels=frozenset({1}), genders=frozenset({Gender.FEMALE}), layouts=(static_text("F1"),)))
    register(Dare(key="m2", levels=frozenset({2}), genders=frozenset({Gender.MALE}), layouts=(static_text("M2"),)))

    assert pick_dare(1, _MALE, _FEMALE) == "M1"
    assert pick_dare(1, _FEMALE, _MALE) == "F1"
    assert pick_dare(2, _FEMALE, _MALE) == "Improvise un gage !"


def test_dare_can_scale_intensity_with_level_and_name_both_players():
    def describe(level, loser, partner):
        base = 5 if loser.gender == Gender.MALE else 3
        return f"{loser.name}, fais {base * level} pompes devant {partner.name}"

    register(
        Dare(key="pompes", levels=frozenset({1, 2}), genders=frozenset({Gender.MALE, Gender.FEMALE}), layouts=(describe,))
    )

    assert pick_dare(2, _MALE, _FEMALE) == "Alex, fais 10 pompes devant Sam"
    assert pick_dare(2, _FEMALE, _MALE) == "Sam, fais 6 pompes devant Alex"


def test_dare_can_involve_both_players_while_triggering_off_one_gender():
    register(
        Dare(
            key="portage",
            levels=frozenset({1}),
            genders=frozenset({Gender.MALE}),
            layouts=(lambda level, loser, partner: f"{loser.name} porte {partner.name} sur son dos.",),
        )
    )

    assert pick_dare(1, _MALE, _FEMALE) == "Alex porte Sam sur son dos."
    assert pick_dare(1, _FEMALE, _MALE) == "Improvise un gage !"


def test_pick_dare_draws_a_random_layout_for_the_same_dare():
    register(
        Dare(
            key="varied",
            levels=frozenset({1}),
            genders=frozenset({Gender.MALE}),
            layouts=(static_text("A"), static_text("B")),
        )
    )

    results = {pick_dare(1, _MALE, _FEMALE) for _ in range(50)}
    assert results == {"A", "B"}  # both layouts show up given enough draws


def test_game_level_climbs_by_round_bracket_and_caps():
    register_minigame(Minigame(key="duel", name="Duel", category=MinigameCategory.DUEL))
    game = Game(Player("Alex", Gender.MALE), Player("Sam", Gender.FEMALE))

    assert game.level == 1  # before any round is drawn

    for expected_level in range(1, MAX_DARE_LEVEL + 2):
        for _ in range(ROUNDS_PER_LEVEL):
            game.next_round()
        assert game.level == min(expected_level, MAX_DARE_LEVEL)


def test_next_round_only_draws_minigames_valid_for_that_rounds_level():
    register_minigame(Minigame(key="always", name="Always", category=MinigameCategory.IMPRO, layouts=("x",)))
    register_minigame(
        Minigame(key="early_only", name="EarlyOnly", category=MinigameCategory.IMPRO, layouts=("y",), levels=frozenset({1}))
    )

    game = Game(Player("Alex", Gender.MALE), Player("Sam", Gender.FEMALE))
    for _ in range(ROUNDS_PER_LEVEL):
        game.next_round()  # still level 1: either minigame may be drawn

    round_ = game.next_round()  # first round of level 2: early_only is excluded
    assert round_.minigame.key == "always"


def test_resolve_duel_draws_a_dare_matching_the_losers_gender():
    register_minigame(Minigame(key="duel", name="Duel", category=MinigameCategory.DUEL))
    register(Dare(key="m1", levels=frozenset({1}), genders=frozenset({Gender.MALE}), layouts=(static_text("M1"),)))
    register(Dare(key="f1", levels=frozenset({1}), genders=frozenset({Gender.FEMALE}), layouts=(static_text("F1"),)))

    male, female = Player("Alex", Gender.MALE), Player("Sam", Gender.FEMALE)
    game = Game(male, female)
    round_ = game.next_round()

    game.resolve_duel(male)

    assert round_.loser is male
    assert round_.gage == "M1"
