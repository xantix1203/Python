"""Fills {homme}/{femme} placeholders in minigame prompts/instructions with
the matching player's name, so minigame text can call out either player by
name without knowing them in advance.
"""

from ..models.gender import Gender


def render(template, players):
    names = {player.gender: player.name for player in players}
    return template.format(homme=names.get(Gender.MALE, "?"), femme=names.get(Gender.FEMALE, "?"))
