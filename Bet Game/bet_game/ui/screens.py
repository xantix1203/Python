"""The two screens of a match: player name entry, then the round loop.
Each owns its own event loop and draws into the shared game window, the
same way battleship.ui.screens does.
"""

import pygame as pg

from ..config import (
    BODY_SIZE,
    COLOR_BG,
    COLOR_CARD_DUEL,
    COLOR_CARD_GAGE,
    COLOR_CARD_IMPRO,
    COLOR_WHITE,
    FPS,
    LABEL_SIZE,
    TITLE_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from ..engine.minigame import MinigameCategory
from ..engine.objects import objects_for
from ..engine.wording import render
from ..models.gender import Gender
from ..models.player import Player
from .card import Card
from .events import quit_if_closed
from .widgets import Button, Checkbox, GenderToggle, TextBox

_MAIN_CARD_RECT = (WINDOW_WIDTH // 2 - 320, 110, 640, 220)
_GAGE_CARD_RECT = (WINDOW_WIDTH // 2 - 320, 400, 640, 180)


def run_setup_screen(window, clock):
    """Blocks until both names are filled in and "Commencer" is pressed.
    Returns the two Player objects.
    """
    title_font = pg.font.Font(None, TITLE_SIZE)
    label_font = pg.font.Font(None, LABEL_SIZE)

    box1 = TextBox((WINDOW_WIDTH // 2 - 220, 300, 300, 50), "Joueur 1")
    box2 = TextBox((WINDOW_WIDTH // 2 - 220, 380, 300, 50), "Joueur 2")
    toggle1 = GenderToggle((WINDOW_WIDTH // 2 + 100, 300, 120, 50), Gender.MALE)
    toggle2 = GenderToggle((WINDOW_WIDTH // 2 + 100, 380, 120, 50), Gender.FEMALE)
    start_button = Button((WINDOW_WIDTH // 2 - 110, 470, 220, 54), "Commencer")

    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            box1.handle_event(event)
            box2.handle_event(event)
            toggle1.handle_event(event)
            toggle2.handle_event(event)
            if start_button.is_clicked(event) and box1.text.strip() and box2.text.strip():
                player1 = Player(box1.text.strip(), toggle1.gender)
                player2 = Player(box2.text.strip(), toggle2.gender)
                return player1, player2

        window.fill(COLOR_BG)
        title = title_font.render("Bet Game", True, COLOR_WHITE)
        window.blit(title, title.get_rect(centerx=WINDOW_WIDTH // 2, top=140))

        subtitle = label_font.render("Entrez les noms des deux joueurs", True, COLOR_WHITE)
        window.blit(subtitle, subtitle.get_rect(centerx=WINDOW_WIDTH // 2, top=220))

        box1.draw(window, label_font)
        box2.draw(window, label_font)
        toggle1.draw(window, label_font)
        toggle2.draw(window, label_font)
        start_button.draw(window, label_font)

        pg.display.flip()
        clock.tick(FPS)


def run_objects_screen(window, clock, player1, player2):
    """Blocks until "Commencer" is pressed. Each player picks, from their
    gender's pool, which objects they currently have in front of them —
    this is what the "remove an object" dare draws from later.
    """
    title_font = pg.font.Font(None, TITLE_SIZE)
    label_font = pg.font.Font(None, LABEL_SIZE)

    columns = ((player1, WINDOW_WIDTH // 2 - 380), (player2, WINDOW_WIDTH // 2 + 60))
    checkboxes = {
        player: [Checkbox((x, 260 + i * 50, 26, 26), spec.key) for i, spec in enumerate(objects_for(player.gender))]
        for player, x in columns
    }
    start_button = Button((WINDOW_WIDTH // 2 - 110, 560, 220, 54), "Commencer")

    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            for player_checkboxes in checkboxes.values():
                for checkbox in player_checkboxes:
                    checkbox.handle_event(event)
            if start_button.is_clicked(event):
                for player, player_checkboxes in checkboxes.items():
                    player.starting_objects = {checkbox.label for checkbox in player_checkboxes if checkbox.checked}
                return

        window.fill(COLOR_BG)
        title = title_font.render("Objets de départ", True, COLOR_WHITE)
        window.blit(title, title.get_rect(centerx=WINDOW_WIDTH // 2, top=120))

        subtitle = label_font.render("Cochez ce que chacun a devant soi", True, COLOR_WHITE)
        window.blit(subtitle, subtitle.get_rect(centerx=WINDOW_WIDTH // 2, top=190))

        for player, x in columns:
            name_label = label_font.render(player.name, True, COLOR_WHITE)
            window.blit(name_label, (x, 220))
            for checkbox in checkboxes[player]:
                checkbox.draw(window, label_font)

        start_button.draw(window, label_font)

        pg.display.flip()
        clock.tick(FPS)


def run_round_screen(window, clock, game):
    """Runs rounds back to back until the window is closed. Each round draws
    a minigame, shows its card, and — for DUEL minigames — waits for the
    loser to be reported before revealing the gage. Whenever a level change
    forces a catch-up object removal (see Game.next_round), that's shown
    first, before the round's own card.
    """
    title_font = pg.font.Font(None, TITLE_SIZE)
    label_font = pg.font.Font(None, LABEL_SIZE)
    body_font = pg.font.Font(None, BODY_SIZE)

    while True:
        round_ = game.next_round()
        for player, dare_text in game.pending_object_removals:
            _show_object_removal_card(window, clock, label_font, body_font, player, dare_text)
        _play_round(window, clock, game, round_, label_font, body_font)


def _show_object_removal_card(window, clock, label_font, body_font, player, dare_text):
    card = Card(_MAIN_CARD_RECT, COLOR_CARD_GAGE, f"Objet à retirer — {player.name}", dare_text)
    next_button = Button((WINDOW_WIDTH // 2 - 110, 620, 220, 50), "Continuer")

    while True:
        dt = clock.tick(FPS) / 1000
        for event in pg.event.get():
            quit_if_closed(event)
            if card.done_popping and next_button.is_clicked(event):
                return

        card.update(dt)
        window.fill(COLOR_BG)
        label = label_font.render("Changement de niveau", True, COLOR_WHITE)
        window.blit(label, label.get_rect(centerx=WINDOW_WIDTH // 2, top=40))
        card.draw(window, label_font, body_font)
        if card.done_popping:
            next_button.draw(window, label_font)
        pg.display.flip()


def _play_round(window, clock, game, round_, label_font, body_font):
    minigame = round_.minigame
    is_impro = minigame.category == MinigameCategory.IMPRO

    color = COLOR_CARD_IMPRO if is_impro else COLOR_CARD_DUEL
    body = render(round_.text, game.players)
    if is_impro:
        body = f"{body}\n\nDurée : {minigame.duration_seconds} s"
    card = Card(_MAIN_CARD_RECT, color, minigame.name, body)

    next_button = Button((WINDOW_WIDTH // 2 - 110, 620, 220, 50), "Round suivant")
    loser_buttons = None
    if not is_impro:
        player1, player2 = game.players
        loser_buttons = [
            (player1, Button((WINDOW_WIDTH // 2 - 330, 350, 320, 50), f"{player1.name} a perdu")),
            (player2, Button((WINDOW_WIDTH // 2 + 10, 350, 320, 50), f"{player2.name} a perdu")),
        ]
    gage_card = None

    while True:
        dt = clock.tick(FPS) / 1000
        for event in pg.event.get():
            quit_if_closed(event)
            if not card.done_popping:
                continue
            if is_impro:
                if next_button.is_clicked(event):
                    return
            elif gage_card is None:
                for player, button in loser_buttons:
                    if button.is_clicked(event):
                        game.resolve_duel(player)
                        gage_card = Card(_GAGE_CARD_RECT, COLOR_CARD_GAGE, f"Gage pour {player.name}", round_.gage)
            elif gage_card.done_popping and next_button.is_clicked(event):
                return

        card.update(dt)
        if gage_card is not None:
            gage_card.update(dt)

        window.fill(COLOR_BG)
        round_label = label_font.render(f"Round {round_.number} · Niveau {game.level}", True, COLOR_WHITE)
        window.blit(round_label, round_label.get_rect(centerx=WINDOW_WIDTH // 2, top=40))

        card.draw(window, label_font, body_font)

        if card.done_popping:
            if is_impro:
                next_button.draw(window, label_font)
            elif gage_card is None:
                for _, button in loser_buttons:
                    button.draw(window, label_font)
            else:
                gage_card.draw(window, label_font, body_font)
                if gage_card.done_popping:
                    next_button.draw(window, label_font)

        pg.display.flip()
