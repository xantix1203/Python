"""Sound effects: a per-country file (`private/sounds/<country>/<event>.wav`)
if one exists, falling back to a procedurally synthesized default tone
(numpy + pygame.mixer, no external assets) when it doesn't. `intro` has no
synthesized fallback -- it only plays if a file exists for that country.

The sounds live under `private/` (outside version control, see the project
README) rather than `battleship/assets/` since they're personal, user-supplied
files, not project assets.

If there's no audio device available, `init()` just leaves sound disabled
and every play_* call becomes a no-op rather than crashing the game.
"""

from pathlib import Path

import numpy as np
import pygame as pg

_SOUNDS_DIR = Path(__file__).resolve().parent.parent.parent / "private" / "sounds"
_NOTE_VOLUME = 0.4
_enabled = False
_default_sounds = {}
_country_sounds = {}  # (country, event) -> Sound or None (None = no file, checked already)


def init():
    global _enabled
    try:
        pg.mixer.init()
    except pg.error:
        _enabled = False
        return
    _enabled = True
    _default_sounds["hit"] = _make_sound([880], 120)
    _default_sounds["miss"] = _make_sound([180], 150)
    _default_sounds["sunk"] = _make_sound([600, 450, 300], 120)
    _default_sounds["cast"] = _make_sound([440, 880], 100)
    _default_sounds["victory"] = _make_sound([523, 659, 784], 150)


def play_hit(country=None):
    _play("hit", country)


def play_miss(country=None):
    _play("miss", country)


def play_sunk(country=None):
    _play("sunk", country)


def play_cast(country=None):
    _play("cast", country)


def play_victory():
    _play("victory", None)


def play_intro(country=None):
    if not _enabled or country is None:
        return
    sound = _country_sound("intro", country)
    if sound is not None:
        sound.play()


def play_special(country=None):
    """A country-specific stinger for "a special was just announced",
    layered on top of play_cast's generic blip. Unlike every other play_*
    here, there is no synthesized fallback: without private/sounds/<country>/
    special.wav this is silent, since a generic beep wouldn't read as that
    country's own flourish.
    """
    if not _enabled or country is None:
        return
    sound = _country_sound("special", country)
    if sound is not None:
        sound.play()


def _play(event_name, country):
    if not _enabled:
        return
    sound = _country_sound(event_name, country) if country else None
    (sound if sound is not None else _default_sounds[event_name]).play()


def _country_sound(event_name, country):
    key = (country, event_name)
    if key not in _country_sounds:
        path = _SOUNDS_DIR / country.lower() / f"{event_name}.wav"
        _country_sounds[key] = pg.mixer.Sound(str(path)) if path.is_file() else None
    return _country_sounds[key]


def _make_sound(note_frequencies, note_duration_ms):
    sample_rate, sample_size, channels = pg.mixer.get_init()
    notes = [_note_waveform(freq, note_duration_ms, sample_rate, sample_size) for freq in note_frequencies]
    samples = np.concatenate(notes)
    if channels == 2:
        samples = np.column_stack([samples, samples])
    return pg.sndarray.make_sound(np.ascontiguousarray(samples))


def _note_waveform(frequency, duration_ms, sample_rate, sample_size):
    n_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
    waveform = np.sin(2 * np.pi * frequency * t)
    waveform *= np.linspace(1, 0, n_samples)  # fade out, avoids an audible click at the end
    max_amplitude = 2 ** (abs(sample_size) - 1) - 1
    dtype = np.int16 if abs(sample_size) <= 16 else np.int32
    return (waveform * _NOTE_VOLUME * max_amplitude).astype(dtype)
