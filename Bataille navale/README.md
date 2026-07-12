# Bataille navale

A local, hotseat Battleship game built with Pygame: place your fleet, then take
turns firing at your opponent's board.

## Setup

Install the dependencies once, with whichever Python you normally use (no
virtualenv needed — `battleship/` sits right next to `main.py`, so nothing
needs to be installed as a package):

```bash
pip3 install --user pygame numpy pytest
```

## Run the game

```bash
python main.py
```

- On launch, enter a name and pick "CONTRE BOT", "CONTRE JOUEUR" (same
  laptop, hotseat), or "EN RÉSEAU" (two laptops on the same Wi-Fi). In-game
  text (status bar, menu, end screen) is in French for French players; code,
  comments, and docs stay in English.
- For LAN play: one player clicks "HÉBERGER" — this shows their local IP
  and waits for the other player to join. The other player clicks
  "REJOINDRE" and types that IP in. Both machines need to be on the same
  Wi-Fi network, and the host's firewall may prompt to allow incoming
  connections the first time (expected — allow it). There's no internet/NAT
  support: this only works on the same local network, not across different
  networks.
- During setup, move the mouse to preview a boat and click to place it; press
  `r` to rotate between vertical/horizontal.
- During a turn, click a cell on your opponent's board to fire at it. The
  status bar under the board shows whose turn it is and the outcome of each
  shot; hits, misses, sinks, and the final win all have a short synthesized
  sound (generated at runtime — no audio files needed).
- The bot hunts randomly until it lands a hit, then targets the neighboring
  cells until it sinks that ship, like a real opponent would.
- After the match, the end screen shows the winner and final scores — click
  or press any key to quit.

## Run the tests

```bash
pytest
```

Tests cover the core game logic (`Boat`, `Grid`, `Player`, `Bot`) and the
networking layer (`Connection`, using `socket.socketpair()` to exercise real
threads and sockets without needing an actual network). The Pygame-driven UI
(`battleship.ui`) isn't covered by automated tests since it needs a real
display and mouse input — verify it manually by running the game.

## Project layout

```
battleship/
├── config.py     # board/window size, colors, fleet composition, network port
├── models/       # Boat, Grid, Player, Bot — game state and rules, no UI dependencies
├── engine/       # Game — turn/round resolution for local (hotseat/bot) play
├── network/      # connection.py (sockets/threading), match.py (LAN match orchestration)
└── ui/           # Pygame rendering (board_view.py), input handling (input_handler.py),
                  # menus/end screen (screens.py), sound (sound.py)
main.py           # entry point wiring everything together
```
