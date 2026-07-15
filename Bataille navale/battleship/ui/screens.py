"""Pre-game setup menu and post-game end screen. Each owns its own event loop
and draws into the shared game window, the same way battleship.ui.input_handler
does for the board itself.
"""

import pygame as pg

from ..config import (
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_DARK_GREY,
    COLOR_RED,
    COUNTRIES,
    MAX_PLAYERS,
    MENU_WINDOW_SIZE,
    NETWORK_PORT,
    WINDOW_SIZE,
    resolve_nickname,
)
from ..models.bot import Bot
from ..models.player import Player
from ..network.connection import Connection, ConnectAttempt, HostListener, get_local_ip
from . import sound
from .events import quit_if_closed
from .widgets import Button, Dropdown, TextBox

_TITLE_FONT_SIZE = 48
_LABEL_FONT_SIZE = 28


def run_setup_menu(window):
    """Blocks until the player configures a match. Returns one of:
    ("local", [players])            -- hotseat/bot play (2 players)
    ("host",  (host_player, joined))-- LAN host; joined is a list of
                                       {"conn", "name", "country"} for each peer
    ("join",  (local_player, conn)) -- LAN joiner already connected to a host
    """
    title_font = pg.font.Font(None, _TITLE_FONT_SIZE)
    label_font = pg.font.Font(None, _LABEL_FONT_SIZE)
    center_x = MENU_WINDOW_SIZE[0] // 2

    player1_box = TextBox((center_x - 200, 160, 220, 40), "Joueur 1")
    player2_box = TextBox((center_x - 200, 340, 220, 40), "Joueur 2")
    player1_country = Dropdown((center_x + 30, 160, 160, 40), COUNTRIES)
    player2_country = Dropdown((center_x + 30, 340, 160, 40), COUNTRIES)
    bot_button = Button((center_x - 320, 240, 200, 50), "CONTRE BOT")
    player_button = Button((center_x - 100, 240, 200, 50), "CONTRE JOUEUR")
    network_button = Button((center_x + 120, 240, 200, 50), "EN RÉSEAU")
    start_button = Button((center_x - 100, 440, 200, 60), "Commencer")
    host_button = Button((center_x - 220, 440, 200, 60), "HÉBERGER")
    join_button = Button((center_x + 20, 440, 200, 60), "REJOINDRE")

    mode = "bot"

    while True:
        for event in pg.event.get():
            quit_if_closed(event)

            # Dropdowns get first look. If one was already open, this click is
            # "theirs" (selecting an option, or closing it) -- don't also let
            # it fall through to a button/box that happens to sit underneath.
            dropdown_was_open = player1_country.open or (mode == "player" and player2_country.open)
            player1_country.handle_event(event)
            if mode == "player":
                player2_country.handle_event(event)
            if dropdown_was_open:
                continue

            # A name box locks the instant it loses focus for the first time,
            # revealing the resolved nickname right there in the box.
            was_active = player1_box.active
            player1_box.handle_event(event)
            if was_active and not player1_box.active and not player1_box.locked:
                player1_box.text = resolve_nickname(player1_box.text) or "Joueur 1"
                player1_box.locked = True

            if mode == "player":
                was_active = player2_box.active
                player2_box.handle_event(event)
                if was_active and not player2_box.active and not player2_box.locked:
                    player2_box.text = resolve_nickname(player2_box.text) or "Joueur 2"
                    player2_box.locked = True

            if bot_button.is_clicked(event):
                mode = "bot"
            elif player_button.is_clicked(event):
                mode = "player"
            elif network_button.is_clicked(event):
                mode = "network"
            elif mode in ("bot", "player") and start_button.is_clicked(event):
                # resolve_nickname is idempotent -- harmless if the box already locked-in a resolved name.
                name1 = resolve_nickname(player1_box.text) or "Joueur 1"
                country1 = player1_country.selected
                sound.play_intro(country1)
                if mode == "bot":
                    return "local", [Player(name1, country=country1), Bot()]
                name2 = resolve_nickname(player2_box.text) or "Joueur 2"
                country2 = player2_country.selected
                sound.play_intro(country2)
                return "local", [Player(name1, country=country1), Player(name2, country=country2)]
            elif mode == "network" and host_button.is_clicked(event):
                name1 = resolve_nickname(player1_box.text) or "Joueur 1"
                country1 = player1_country.selected
                sound.play_intro(country1)
                host_player = Player(name1, country=country1)
                joined = _run_host_lobby(window, host_player, label_font, title_font)
                if joined is not None:
                    return "host", (host_player, joined)
            elif mode == "network" and join_button.is_clicked(event):
                name1 = resolve_nickname(player1_box.text) or "Joueur 1"
                country1 = player1_country.selected
                connection = _run_join_screen(window, label_font, title_font)
                if connection is not None:
                    sound.play_intro(country1)
                    connection.send({"type": "join", "name": name1, "country": country1})
                    return "join", (Player(name1, country=country1), connection)

        window.fill(COLOR_BLUE)
        title_surface = title_font.render("Bataille navale", True, COLOR_BLACK)
        window.blit(title_surface, title_surface.get_rect(center=(center_x, 80)))

        window.blit(
            label_font.render("Nom du joueur 1 :", True, COLOR_BLACK), (player1_box.rect.x, player1_box.rect.y - 30)
        )
        player1_box.draw(window, label_font)
        window.blit(
            label_font.render("Pays :", True, COLOR_BLACK), (player1_country.rect.x, player1_country.rect.y - 30)
        )

        bot_button.draw(window, label_font, selected=mode == "bot")
        player_button.draw(window, label_font, selected=mode == "player")
        network_button.draw(window, label_font, selected=mode == "network")

        if mode == "player":
            window.blit(
                label_font.render("Nom du joueur 2 :", True, COLOR_BLACK),
                (player2_box.rect.x, player2_box.rect.y - 30),
            )
            player2_box.draw(window, label_font)
            window.blit(
                label_font.render("Pays :", True, COLOR_BLACK), (player2_country.rect.x, player2_country.rect.y - 30)
            )

        if mode in ("bot", "player"):
            start_button.draw(window, label_font)
        else:
            host_button.draw(window, label_font)
            join_button.draw(window, label_font)

        # Drawn last so an open dropdown's option list renders on top of everything else.
        player1_country.draw(window, label_font)
        if mode == "player":
            player2_country.draw(window, label_font)

        pg.display.flip()


def _run_host_lobby(window, host_player, label_font, title_font):
    """Gather 1..MAX_PLAYERS-1 peers into a lobby, then START the match. Returns
    a seat-ordered list of {"conn", "name", "country"} for the joiners (the host
    itself is seat 0, added by the caller). No 'back' option on purpose: the
    listening socket is bound for as long as this runs; closing the window is
    the way out, same as other blocking waits in the app.
    """
    center_x = MENU_WINDOW_SIZE[0] // 2
    listener = HostListener(NETWORK_PORT)
    local_ip = get_local_ip()
    start_button = Button((center_x - 100, 640, 200, 60), "COMMENCER")

    pending = []  # accepted, awaiting their join message
    joined = []  # [{"conn", "name", "country"}]

    while True:
        for event in pg.event.get():
            quit_if_closed(event)
            if len(joined) >= 1 and start_button.is_clicked(event):
                listener.close()
                return joined

        connection = listener.poll()
        if connection is not None and len(joined) < MAX_PLAYERS - 1:
            pending.append(connection)

        _drain_joins(pending, joined)

        window.fill(COLOR_BLUE)
        title = title_font.render("Salon réseau", True, COLOR_BLACK)
        window.blit(title, title.get_rect(center=(center_x, 90)))
        window.blit(
            label_font.render(f"Votre IP : {local_ip}    Port : {NETWORK_PORT}", True, COLOR_BLACK),
            (center_x - 240, 150),
        )
        roster = [f"1. {host_player.name} (vous)"] + [f"{i + 2}. {peer['name']}" for i, peer in enumerate(joined)]
        for i, line in enumerate(roster):
            window.blit(label_font.render(line, True, COLOR_BLACK), (center_x - 240, 210 + i * 34))

        hint = "Prêt à commencer." if joined else "En attente de joueurs..."
        window.blit(label_font.render(hint, True, COLOR_DARK_GREY), (center_x - 240, 210 + len(roster) * 34 + 10))
        start_button.draw(window, label_font, selected=bool(joined))
        pg.display.flip()
        pg.time.wait(16)


def _drain_joins(pending, joined):
    """Move any pending peers that have sent their `join` message into `joined`,
    and drop any that disconnected before doing so.
    """
    for connection in list(pending):
        try:
            message = connection.poll()
        except ConnectionError:
            pending.remove(connection)
            continue
        if message is not None and message.get("type") == "join":
            pending.remove(connection)
            joined.append(
                {"conn": connection, "name": message.get("name", "Joueur"), "country": message.get("country")}
            )


def _run_join_screen(window, label_font, title_font):
    """Blocks until the player connects successfully or backs out."""
    center_x = MENU_WINDOW_SIZE[0] // 2
    ip_box = TextBox((center_x - 150, 220, 300, 40), "")
    connect_button = Button((center_x - 220, 300, 200, 50), "Connecter")
    back_button = Button((center_x + 20, 300, 200, 50), "Retour")

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
