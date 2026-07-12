"""Procedurally synthesized sound effects — no external audio assets needed.

Generates short tones/melodies with numpy and hands them to pygame's mixer.
If there's no audio device available, `init()` just leaves sound disabled
and every play_* call becomes a no-op rather than crashing the game.
"""

import numpy as np
import pygame as pg

_NOTE_VOLUME = 0.4
_enabled = False
_sounds = {}


def init():
    global _enabled
    try:
        pg.mixer.init()
    except pg.error:
        _enabled = False
        return
    _enabled = True
    _sounds["hit"] = _make_sound([880], 120)
    _sounds["miss"] = _make_sound([180], 150)
    _sounds["sunk"] = _make_sound([600, 450, 300], 120)
    _sounds["victory"] = _make_sound([523, 659, 784], 150)


def play_hit():
    _play("hit")


def play_miss():
    _play("miss")


def play_sunk():
    _play("sunk")


def play_victory():
    _play("victory")


def _play(name):
    if _enabled:
        _sounds[name].play()


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
