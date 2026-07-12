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

- On launch, enter a name and pick a country from the dropdown next to it
  (cosmetic for now). Once you click away from the name box it's locked in —
  no going back to edit it — and a couple of names get swapped for a joke
  nickname automatically. Then pick "CONTRE BOT", "CONTRE JOUEUR" (same
  laptop, hotseat), or "EN RÉSEAU" (two laptops on the same Wi-Fi). In-game
  text (status bar, menu, end screen) is in French for French players; code,
  comments, and docs stay in English.
- During placement, after you place each ship you're prompted to name it
  (Enter to confirm, or leave it blank to keep the default type name). If
  that ship is later sunk, its custom name is what shows up in the result
  message, in both local and LAN play.
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
- Hit/miss/sunk sounds can have a per-country variant: drop `.wav` files under
  `private/sounds/<country>/{hit,miss,sunk}.wav` (lowercase country name —
  `pakistan`, `china`, `japan`, `usa`, `france`, `canada`). Anything missing
  (a whole country, or just one event) automatically falls back to the
  default synthesized sound — no code changes needed to add files later.
  There's also an optional `intro.wav` per country (no synthesized fallback):
  it plays once, right as a player's country choice becomes final — on
  clicking "Commencer" or "Héberger", or the moment a "Rejoindre" attempt
  successfully connects.
- After the match, the end screen shows the winner and final scores — click
  or press any key to quit.

## Private, non-versioned files

`private/` (gitignored, except the `.example.json` templates) is where
anything personal or machine-specific lives — content the game reads at
runtime but that shouldn't be published:

- `private/sounds/<country>/{hit,miss,sunk,intro}.wav` — per-country sound
  overrides (see above).
- `private/nicknames.json` — maps an entered name (lowercase) to a nickname
  it gets swapped for automatically, e.g. `{"samy": "Tunisian Conqueror"}`.
  See `private/nicknames.example.json` for the format. If the file is
  missing, names simply pass through unchanged — nothing crashes on a fresh
  clone that doesn't have it.

If you need to add another non-public asset or config later, put it under
`private/` too and add a `!/private/whatever.example...` line to
`.gitignore` if it needs a tracked template.

## Run the tests

```bash
pytest
```

Tests cover the core game logic (`Boat`, `Grid`, `Player`, `Bot`), config
helpers (`resolve_nickname`), and the networking layer (`Connection`, using
`socket.socketpair()` to exercise real threads and sockets without needing an
actual network). The Pygame-driven UI (`battleship.ui`) isn't covered by
automated tests since it needs a real display and mouse input — verify it
manually by running the game.

## Project layout

```
battleship/
├── config.py     # board/window size, colors, fleet composition, network port,
                  # countries, nickname loading (from private/nicknames.json)
├── models/       # Boat, Grid, Player, Bot — game state and rules, no UI dependencies
├── engine/       # Game — turn/round resolution for local (hotseat/bot) play
├── network/      # connection.py (sockets/threading), match.py (LAN match orchestration)
└── ui/           # Pygame rendering (board_view.py), input handling (input_handler.py),
                  # menus/end screen (screens.py), reusable widgets (widgets.py), sound (sound.py)
main.py           # entry point wiring everything together
private/          # gitignored: nicknames.json, sounds/<country>/*.wav (see below)
```
