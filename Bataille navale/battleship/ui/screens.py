"""Pre-game setup menu and post-game end screen. Each owns its own event loop
and draws into the shared game window, the same way battleship.ui.input_handler
does for the board itself.
"""

import pygame as pg

from ..config import COLOR_BLACK, COLOR_BLUE, COLOR_DARK_GREY, COLOR_GREY, COLOR_RED, COLOR_WHITE, NETWORK_PORT, WINDOW_SIZE
from ..models.bot import Bot
from ..models.player import Player
from ..network.connection import Connection, ConnectAttempt, HostListener, get_local_ip
from .events import quit_if_closed

_TITLE_FONT_SIZE = 48
_LABEL_FONT_SIZE = 28
_MAX_NAME_LENGTH = 16


class _TextBox:
    def __init__(self, rect, initial_text):
        self.rect = pg.Rect(rect)
        self.text = initial_text
        self.active = False

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.KEYDOWN and self.active:
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable() and len(self.text) < _MAX_NAME_LENGTH:
                self.text += event.unicode

    def draw(self, window, font):
        pg.draw.rect(window, COLOR_WHITE, self.rect)
        pg.draw.rect(window, COLOR_BLACK if self.active else COLOR_GREY, self.rect, 2)
        text_surface = font.render(self.text, True, COLOR_BLACK)
        y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        window.blit(text_surface, (self.rect.x + 8, y))


class _Button:
    def __init__(self, rect, label):
        self.rect = pg.Rect(rect)
        self.label = label

    def is_clicked(self, event):
        return event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, window, font, selected=False):
        pg.draw.rect(window, COLOR_BLACK if selected else COLOR_GREY, self.rect)
        text_surface = font.render(self.label, True, COLOR_WHITE)
        window.blit(text_surface, text_surface.get_rect(center=self.rect.center))


def run_setup_menu(window):
    """Blocks until the player configures a match. Returns either
    ("local", [players]) for hotseat/bot play, or
    ("network", (local_player, connection, is_host)) for LAN play.
    """
    title_font = pg.font.Font(None, _TITLE_FONT_SIZE)
    label_font = pg.font.Font(None, _LABEL_FONT_SIZE)
    center_x = WINDOW_SIZE // 2

    player1_box = _TextBox((center_x - 150, 160, 300, 40), "Joueur 1")
    player2_box = _TextBox((center_x - 150, 340, 300, 40), "Joueur 2")
    bot_button = _Button((center_x - 320, 240, 200, 50), "CONTRE BOT")
    player_button = _Button((center_x - 100, 240, 200, 50), "CONTRE JOUEUR")
    network_button = _Button((center_x + 120, 240, 200, 50), "EN RÉSEAU")
    start_button = _Button((center_x - 100, 440, 200, 60), "Commencer")
    host_button = _Button((center_x - 220, 440, 200, 60), "HÉBERGER")
    join_button = _Button((center_x + 20, 440, 200, 60), "REJOINDRE")

    mode = "bot"

    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            player1_box.handle_event(event)
            if mode == "player":
                player2_box.handle_event(event)

            if bot_button.is_clicked(event):
                mode = "bot"
            elif player_button.is_clicked(event):
                mode = "player"
            elif network_button.is_clicked(event):
                mode = "network"
            elif mode in ("bot", "player") and start_button.is_clicked(event):
                name1 = player1_box.text.strip() or "Joueur 1"
                if mode == "bot":
                    return "local", [Player(name1), Bot()]
                name2 = player2_box.text.strip() or "Joueur 2"
                return "local", [Player(name1), Player(name2)]
            elif mode == "network" and host_button.is_clicked(event):
                name1 = player1_box.text.strip() or "Joueur 1"
                connection = _run_host_screen(window, label_font, title_font)
                if connection is not None:
                    return "network", (Player(name1), connection, True)
            elif mode == "network" and join_button.is_clicked(event):
                name1 = player1_box.text.strip() or "Joueur 1"
                connection = _run_join_screen(window, label_font, title_font)
                if connection is not None:
                    return "network", (Player(name1), connection, False)

        window.fill(COLOR_BLUE)
        title_surface = title_font.render("Bataille navale", True, COLOR_BLACK)
        window.blit(title_surface, title_surface.get_rect(center=(center_x, 80)))

        window.blit(label_font.render("Nom du joueur 1 :", True, COLOR_BLACK), (player1_box.rect.x, player1_box.rect.y - 30))
        player1_box.draw(window, label_font)

        bot_button.draw(window, label_font, selected=mode == "bot")
        player_button.draw(window, label_font, selected=mode == "player")
        network_button.draw(window, label_font, selected=mode == "network")

        if mode == "player":
            window.blit(label_font.render("Nom du joueur 2 :", True, COLOR_BLACK), (player2_box.rect.x, player2_box.rect.y - 30))
            player2_box.draw(window, label_font)

        if mode in ("bot", "player"):
            start_button.draw(window, label_font)
        else:
            host_button.draw(window, label_font)
            join_button.draw(window, label_font)

        pg.display.flip()


def _run_host_screen(window, label_font, title_font):
    """Blocks until a peer connects. No 'back' option here on purpose: the
    listening socket is bound to a fixed port for as long as this runs, and
    tearing that down cleanly to go back adds real complexity (see
    connection.py's HostListener) for a case that isn't worth it in v1 —
    closing the window is the only way out, same as other blocking waits
    elsewhere in the app.
    """
    center_x = WINDOW_SIZE // 2
    listener = HostListener(NETWORK_PORT)
    local_ip = get_local_ip()

    while True:
        for event in pg.event.get():
            quit_if_closed(event)

        connection = listener.poll()
        if connection is not None:
            return connection

        window.fill(COLOR_BLUE)
        title_surface = title_font.render("En attente d'un adversaire...", True, COLOR_BLACK)
        window.blit(title_surface, title_surface.get_rect(center=(center_x, 140)))
        ip_surface = label_font.render(f"Votre IP : {local_ip}    Port : {NETWORK_PORT}", True, COLOR_BLACK)
        window.blit(ip_surface, ip_surface.get_rect(center=(center_x, 220)))
        pg.display.flip()
        pg.time.wait(16)


def _run_join_screen(window, label_font, title_font):
    """Blocks until the player connects successfully or backs out."""
    center_x = WINDOW_SIZE // 2
    ip_box = _TextBox((center_x - 150, 220, 300, 40), "")
    connect_button = _Button((center_x - 220, 300, 200, 50), "Connecter")
    back_button = _Button((center_x + 20, 300, 200, 50), "Retour")

    attempt = None
    error_message = None

    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            ip_box.handle_event(event)
            if back_button.is_clicked(event):
                return None
            if connect_button.is_clicked(event) and attempt is None and ip_box.text.strip():
                error_message = None
                attempt = ConnectAttempt(ip_box.text.strip(), NETWORK_PORT)

        if attempt is not None:
            result = attempt.poll()
            if isinstance(result, Connection):
                return result
            if isinstance(result, OSError):
                error_message = "Connexion impossible. Vérifiez l'adresse IP."
                attempt = None

        window.fill(COLOR_BLUE)
        title_surface = title_font.render("Rejoindre une partie", True, COLOR_BLACK)
        window.blit(title_surface, title_surface.get_rect(center=(center_x, 140)))
        window.blit(
            label_font.render("Adresse IP de l'hôte :", True, COLOR_BLACK), (ip_box.rect.x, ip_box.rect.y - 30)
        )
        ip_box.draw(window, label_font)
        connect_button.draw(window, label_font, selected=attempt is not None)
        back_button.draw(window, label_font)
        if attempt is not None:
            status_surface = label_font.render("Connexion en cours...", True, COLOR_BLACK)
            window.blit(status_surface, status_surface.get_rect(center=(center_x, 380)))
        elif error_message is not None:
            error_surface = label_font.render(error_message, True, COLOR_RED)
            window.blit(error_surface, error_surface.get_rect(center=(center_x, 380)))
        pg.display.flip()
        pg.time.wait(16)


def show_end_screen(window, players, winner):
    """Blocks until the player closes the window, a key, or a click."""
    title_font = pg.font.Font(None, _TITLE_FONT_SIZE)
    label_font = pg.font.Font(None, _LABEL_FONT_SIZE)
    center_x = WINDOW_SIZE // 2

    headline = f"{winner.name} gagne !" if winner is not None else "Match nul."

    window.fill(COLOR_BLUE)
    headline_surface = title_font.render(headline, True, COLOR_BLACK)
    window.blit(headline_surface, headline_surface.get_rect(center=(center_x, 140)))

    for i, player in enumerate(players):
        line = f"{player.name} : {player.score} points"
        surface = label_font.render(line, True, COLOR_BLACK)
        window.blit(surface, surface.get_rect(center=(center_x, 220 + i * 40)))

    hint_surface = label_font.render("Cliquez ou appuyez sur une touche pour quitter", True, COLOR_DARK_GREY)
    window.blit(hint_surface, hint_surface.get_rect(center=(center_x, 240 + len(players) * 40)))
    pg.display.flip()

    waiting = True
    while waiting:
        for event in pg.event.get():
            quit_if_closed(event)
            if event.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN):
                waiting = False
        pg.time.wait(16)
