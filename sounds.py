"""Procedurally generated square-wave sound effects (no external asset files)."""
from __future__ import annotations

import array
from typing import Dict, Sequence, Tuple

import pygame

SAMPLE_RATE = 22050
Note = Tuple[float, float]   # (frequency in Hz, duration in seconds)

EFFECTS: Dict[str, Sequence[Note]] = {
    "eat": ((880.0, 0.06), (1100.0, 0.05)),
    "bonus": ((1320.0, 0.06), (1760.0, 0.06), (2349.0, 0.12)),
    "gameover": ((392.0, 0.16), (330.0, 0.16), (262.0, 0.16), (196.0, 0.16), (147.0, 0.35)),
    "click": ((1000.0, 0.03),),
}


def _square_wave(notes: Sequence[Note], rate: int, channels: int, volume: float = 0.16) -> bytes:
    """Render notes as signed 16-bit square-wave PCM with a tiny fade to avoid clicks."""
    samples = array.array("h")
    amplitude = int(32767 * volume)
    ramp = max(1, int(rate * 0.004))
    for freq, duration in notes:
        count = int(rate * duration)
        period = rate / freq
        half = period / 2.0
        for i in range(count):
            level = amplitude if (i % period) < half else -amplitude
            edge = min(i, count - 1 - i)
            if edge < ramp:
                level = int(level * edge / ramp)
            samples.extend([level] * channels)
    return samples.tobytes()


class SoundManager:
    """Builds all effects at start-up and plays them. Degrades silently without audio."""

    def __init__(self) -> None:
        self.muted = False
        self.available = False
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
            info = pygame.mixer.get_init()
            if info is None:
                return
            rate, fmt, channels = info
            if fmt not in (-16, 32784):          # only signed 16-bit output is supported
                return
            for name, notes in EFFECTS.items():
                self._sounds[name] = pygame.mixer.Sound(buffer=_square_wave(notes, rate, channels))
            self.available = True
        except (pygame.error, OSError, ValueError, TypeError, NotImplementedError):
            self.available = False

    def play(self, name: str) -> None:
        """Play an effect by name unless muted or audio is unavailable."""
        if self.available and not self.muted:
            sound = self._sounds.get(name)
            if sound is not None:
                sound.play()

    def toggle_mute(self) -> bool:
        """Toggle mute and return the new state."""
        self.muted = not self.muted
        if self.muted and self.available:
            pygame.mixer.stop()
        return self.muted
