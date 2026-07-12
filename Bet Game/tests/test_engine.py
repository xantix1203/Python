import pytest

from bet_game.engine.game import Game
from bet_game.engine.minigame import Minigame, MinigameCategory, clear_registry, register
from bet_game.engine.round import draw_round
from bet_game.models.gender import Gender
from bet_game.models.player import Player


@pytest.fixture(autouse=True)
def empty_registry():
    clear_registry()
    yield
    clear_registry()


def make_players():
    return Player("Alex", Gender.MALE), Player("Sam", Gender.FEMALE)


def test_draw_round_with_no_minigames_raises():
    with pytest.raises(RuntimeError):
        draw_round(1, 1)


def test_draw_round_picks_a_prompt_for_impro():
    register(
        Minigame(
            key="impro",
            name="Impro",
            category=MinigameCategory.IMPRO,
            layouts=("scenario A", "scenario B"),
            duration_seconds=30,
        )
    )
    round_ = draw_round(1, 1)
    assert round_.number == 1
    assert round_.text in ("scenario A", "scenario B")
    assert round_.is_resolved


def test_duel_round_is_unresolved_until_a_loser_is_reported():
    register(Minigame(key="duel", name="Duel", category=MinigameCategory.DUEL))
    round_ = draw_round(1, 1)
    assert round_.text == ""
    assert not round_.is_resolved

    round_.resolve_duel(Player("Alex", Gender.MALE), "fais 10 pompes")

    assert round_.is_resolved
    assert round_.loser.name == "Alex"
    assert round_.gage == "fais 10 pompes"


def test_draw_round_filters_by_level():
    register(Minigame(key="early", name="Early", category=MinigameCategory.IMPRO, layouts=("x",), levels=frozenset({1})))
    register(Minigame(key="late", name="Late", category=MinigameCategory.IMPRO, layouts=("y",), levels=frozenset({4})))

    assert draw_round(1, 1).minigame.key == "early"
    assert draw_round(1, 4).minigame.key == "late"
    with pytest.raises(RuntimeError):
        draw_round(1, 2)


def test_game_next_round_increments_round_number():
    register(Minigame(key="impro", name="Impro", category=MinigameCategory.IMPRO, layouts=("x",)))

    game = Game(*make_players())
    first = game.next_round()
    second = game.next_round()

    assert first.number == 1
    assert second.number == 2
    assert game.current_round is second
    assert game.rounds == [first, second]
