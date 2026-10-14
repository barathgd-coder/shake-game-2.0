"""Snake entity: body cells, queued turns, growth and render interpolation."""
from __future__ import annotations

from typing import List, Tuple

from settings import MAX_QUEUED_INPUTS, RIGHT, START_LENGTH, Vec


class Snake:
    """A grid-based snake. ``body[0]`` is the head."""

    def __init__(self, cols: int, rows: int, length: int = START_LENGTH) -> None:
        head_x, head_y = cols // 2, rows // 2
        self.body: List[Vec] = [(head_x - i, head_y) for i in range(length)]
        self.prev_body: List[Vec] = list(self.body)   # positions before the last step
        self.direction: Vec = RIGHT                   # direction of the last executed step
        self._queue: List[Vec] = []                   # pending turns (max MAX_QUEUED_INPUTS)

    @property
    def head(self) -> Vec:
        """Current head cell."""
        return self.body[0]

    def queue_direction(self, direction: Vec) -> bool:
        """Queue a turn. Rejects repeats and 180-degree reversals.

        The new direction is validated against the *last queued* direction (or the
        current one if the queue is empty). That is what makes two quick turns
        within a single tick safe: e.g. moving right, UP then LEFT is fine, but
        LEFT directly is a reversal and is ignored.
        """
        reference = self._queue[-1] if self._queue else self.direction
        if direction == reference or direction == (-reference[0], -reference[1]):
            return False
        if len(self._queue) >= MAX_QUEUED_INPUTS:
            return False
        self._queue.append(direction)
        return True

    def consume_direction(self) -> Vec:
        """Apply the next queued turn (if any) and return the direction to move in."""
        if self._queue:
            self.direction = self._queue.pop(0)
        return self.direction

    def move_to(self, new_head: Vec, grow: bool) -> None:
        """Advance the snake so its head is at ``new_head``; keep the tail if ``grow``."""
        self.prev_body = list(self.body)
        self.body.insert(0, new_head)
        if not grow:
            self.body.pop()

    def render_positions(self, t: float) -> List[Tuple[float, float]]:
        """Grid positions interpolated between the previous and current step (t in 0..1)."""
        out: List[Tuple[float, float]] = []
        last_prev = len(self.prev_body) - 1
        for i, (nx, ny) in enumerate(self.body):
            px, py = self.prev_body[min(i, last_prev)]
            dx, dy = nx - px, ny - py
            if abs(dx) > 1 or abs(dy) > 1:           # wrapped around a wall: don't sweep across
                out.append((float(nx), float(ny)))
            else:
                out.append((px + dx * t, py + dy * t))
        return out
