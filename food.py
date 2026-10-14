"""Regular food and timed bonus food."""
from __future__ import annotations

import random
from typing import Set

from settings import BONUS_LIFETIME, Vec


def _pick_free_cell(blocked: Set[Vec], cols: int, rows: int, rng: random.Random) -> Vec:
    """Return a random cell not in ``blocked``; raises IndexError if the board is full."""
    free = [(x, y) for x in range(cols) for y in range(rows) if (x, y) not in blocked]
    return rng.choice(free)


class Food:
    """The normal food item (worth 10 points)."""

    def __init__(self) -> None:
        self.pos: Vec = (0, 0)

    def respawn(self, blocked: Set[Vec], cols: int, rows: int, rng: random.Random) -> bool:
        """Place the food on a random free cell. Returns False if no cell is free."""
        try:
            self.pos = _pick_free_cell(blocked, cols, rows, rng)
        except IndexError:
            return False
        return True


class BonusFood:
    """Bonus food (worth 50 points) that disappears after ``lifetime`` seconds."""

    def __init__(self, lifetime: float = BONUS_LIFETIME) -> None:
        self.lifetime = lifetime
        self.remaining = 0.0
        self.active = False
        self.pos: Vec = (0, 0)

    @property
    def ratio(self) -> float:
        """Fraction of time left (1.0 = just spawned, 0.0 = gone)."""
        return max(0.0, min(1.0, self.remaining / self.lifetime)) if self.active else 0.0

    def spawn(self, blocked: Set[Vec], cols: int, rows: int, rng: random.Random) -> bool:
        """Activate the bonus food on a free cell. Returns False if there is no room."""
        try:
            self.pos = _pick_free_cell(blocked, cols, rows, rng)
        except IndexError:
            return False
        self.remaining = self.lifetime
        self.active = True
        return True

    def update(self, dt: float) -> bool:
        """Count down the timer. Returns True on the frame it expires."""
        if not self.active:
            return False
        self.remaining -= dt
        if self.remaining <= 0.0:
            self.remaining = 0.0
            self.active = False
            return True
        return False

    def deactivate(self) -> None:
        """Remove the bonus food (eaten)."""
        self.active = False
        self.remaining = 0.0
