from bet_game.engine.wording import render
from bet_game.models.gender import Gender
from bet_game.models.player import Player


def test_render_fills_placeholders_by_gender():
    male = Player("Alex", Gender.MALE)
    female = Player("Sam", Gender.FEMALE)
    assert render("{homme} et {femme} dansent.", (male, female)) == "Alex et Sam dansent."


def test_render_is_independent_of_player_order():
    male = Player("Alex", Gender.MALE)
    female = Player("Sam", Gender.FEMALE)
    assert render("{femme} regarde {homme}.", (female, male)) == "Sam regarde Alex."
