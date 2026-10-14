"""Snake - entry point and main game loop.

Run on desktop:  python main.py
Run in a browser: python -m pygbag .   (see README.md)
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import traceback
from dataclasses import asdict, dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pygame

IS_WEB = sys.platform == "emscripten"          # True when running in the browser via pygbag
if IS_WEB:
    import platform                            # pygbag's platform module exposes the JS window

import ui
from food import BonusFood, Food
from settings import (
    BONUS_EVERY_MAX, BONUS_EVERY_MIN, BONUS_POINTS, CANVAS_H, CANVAS_W, DEATH_ANIM_TIME,
    DEATH_BLINK_INTERVAL, DIFFICULTIES, DOWN, FADE_TIME, FOOD_POINTS, FPS, GRID_COLS,
    GRID_ROWS, HIGHSCORE_FILE, LEFT, MAX_FRAME_TIME, MAX_HIGH_SCORES, OBSTACLE_CLUSTERS,
    RIGHT, SPEEDUP_EVERY, START_GRACE, UP, WINDOW_TITLE, Difficulty, Mode, Vec,
)
from snake import Snake
from sounds import SAMPLE_RATE, SoundManager
from themes import Theme, create_themes

SCORE_PATH = Path(__file__).resolve().parent / HIGHSCORE_FILE
WEB_STORAGE_KEY = "snake_highscores"           # browser localStorage key (the web build has no real disk)

KEY_TO_DIRECTION: Dict[int, Vec] = {
    pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
    pygame.K_LEFT: LEFT, pygame.K_a: LEFT, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
}


# --------------------------------------------------------------------------- #
# High scores
# --------------------------------------------------------------------------- #
@dataclass
class ScoreEntry:
    """One row of the high-score table."""
    name: str
    score: int


class HighScoreTable:
    """Top-N scores stored in a JSON file; tolerant of missing or corrupt files."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: List[ScoreEntry] = []
        self.load()
        self.save()                                   # auto-create the file on first run

    @property
    def best(self) -> int:
        """Highest stored score (0 if none)."""
        return self.entries[0].score if self.entries else 0

    def _read_raw(self) -> Optional[str]:
        """Return the stored JSON text, or None if nothing is stored yet."""
        if IS_WEB:
            try:
                value = platform.window.localStorage.getItem(WEB_STORAGE_KEY)
            except Exception:                         # pylint: disable=broad-except
                return None
            return None if value is None else str(value)
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return None

    def load(self) -> None:
        """Read the scores, silently discarding anything malformed."""
        self.entries = []
        try:
            raw = self._read_raw()
            if raw is None:
                return
            data = json.loads(raw)
        except (OSError, ValueError):
            self._quarantine()
            return
        if not isinstance(data, list):
            self._quarantine()
            return
        for item in data:
            if (isinstance(item, dict) and isinstance(item.get("name"), str)
                    and isinstance(item.get("score"), int) and not isinstance(item.get("score"), bool)
                    and item["score"] >= 0):
                self.entries.append(ScoreEntry(item["name"][:10], item["score"]))
        self.entries.sort(key=lambda e: e.score, reverse=True)
        del self.entries[MAX_HIGH_SCORES:]

    def _quarantine(self) -> None:
        """Move a corrupt file aside so it is not overwritten blindly."""
        if IS_WEB:
            return
        try:
            os.replace(self.path, self.path.with_suffix(".json.bak"))
        except OSError:
            pass

    def save(self) -> None:
        """Persist the table. Desktop: atomic file write. Web: browser localStorage."""
        text = json.dumps([asdict(e) for e in self.entries], indent=2)
        if IS_WEB:
            try:
                platform.window.localStorage.setItem(WEB_STORAGE_KEY, text)
            except Exception as exc:                  # pylint: disable=broad-except
                print(f"Warning: could not save high scores: {exc}", file=sys.stderr)
            return
        tmp = self.path.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, self.path)
        except OSError as exc:
            print(f"Warning: could not save high scores: {exc}", file=sys.stderr)

    def qualifies(self, score: int) -> bool:
        """True if the score belongs in the table."""
        return score > 0 and (len(self.entries) < MAX_HIGH_SCORES or score > self.entries[-1].score)

    def add(self, name: str, score: int) -> int:
        """Insert a score (after equal scores), save, and return its 1-based rank."""
        entry = ScoreEntry(name, score)
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.score, reverse=True)   # stable: ties keep older first
        rank = next(i for i, e in enumerate(self.entries) if e is entry) + 1
        del self.entries[MAX_HIGH_SCORES:]
        self.save()
        return rank

    def as_tuples(self) -> List[Tuple[str, int]]:
        return [(e.name, e.score) for e in self.entries]


# --------------------------------------------------------------------------- #
# Obstacles
# --------------------------------------------------------------------------- #
def _is_connected(free: Set[Vec], start: Vec) -> bool:
    """True if every free cell can be reached from ``start`` (flood fill)."""
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in (UP, DOWN, LEFT, RIGHT):
            n = (x + dx, y + dy)
            if n in free and n not in seen:
                seen.add(n)
                stack.append(n)
    return len(seen) == len(free)


def generate_obstacles(rng: random.Random, snake: Snake) -> Set[Vec]:
    """Random short wall segments that never touch the start area or split the board."""
    hx, hy = snake.head
    safe = {(x, y) for x in range(hx - 5, hx + 9) for y in range(hy - 2, hy + 3)}
    cells = {(x, y) for x in range(GRID_COLS) for y in range(GRID_ROWS)}
    for _attempt in range(60):
        blocks: Set[Vec] = set()
        for _cluster in range(OBSTACLE_CLUSTERS):
            x, y = rng.randrange(GRID_COLS), rng.randrange(GRID_ROWS)
            dx, dy = rng.choice(((1, 0), (0, 1)))
            for i in range(rng.randint(2, 4)):
                cell = (x + dx * i, y + dy * i)
                if cell in cells and cell not in safe:
                    blocks.add(cell)
        if _is_connected(cells - blocks, snake.head):
            return blocks
    return set()


# --------------------------------------------------------------------------- #
# One round of play
# --------------------------------------------------------------------------- #
class GameSession:
    """All mutable state of a single round (no globals)."""

    def __init__(self, mode: Mode, difficulty: Difficulty, rng: random.Random) -> None:
        self.mode = mode
        self.difficulty = difficulty
        self.rng = rng
        self.snake = Snake(GRID_COLS, GRID_ROWS)
        self.obstacles: Set[Vec] = generate_obstacles(rng, self.snake) if mode is Mode.OBSTACLES else set()
        self.food = Food()
        self.bonus = BonusFood()
        self.score = 0
        self.foods_eaten = 0
        self.next_bonus_at = rng.randint(BONUS_EVERY_MIN, BONUS_EVERY_MAX)
        self.accumulator = -START_GRACE        # negative = short "get ready" pause
        self.alive = True
        self.food.respawn(self._blocked(include_food=False), GRID_COLS, GRID_ROWS, rng)

    @property
    def level(self) -> int:
        return self.foods_eaten // SPEEDUP_EVERY + 1

    @property
    def step_delay(self) -> float:
        """Seconds between snake moves at the current level."""
        d = self.difficulty
        return max(d.min_delay, d.start_delay - d.delay_step * (self.level - 1))

    def _blocked(self, include_food: bool = True) -> Set[Vec]:
        """Cells where nothing new may spawn."""
        blocked = set(self.snake.body) | self.obstacles
        if self.bonus.active:
            blocked.add(self.bonus.pos)
        if include_food:
            blocked.add(self.food.pos)
        return blocked

    def interpolation(self) -> float:
        """Progress (0..1) towards the next step, used for smooth rendering."""
        return max(0.0, min(1.0, self.accumulator / self.step_delay))

    def update(self, dt: float) -> List[str]:
        """Advance the simulation. Returns events: 'eat', 'bonus', 'die'."""
        events: List[str] = []
        if not self.alive:
            return events
        self.bonus.update(dt)
        self.accumulator += dt
        while self.alive and self.accumulator >= self.step_delay:
            self.accumulator -= self.step_delay
            events.extend(self._tick())
        return events

    def _die(self, events: List[str]) -> List[str]:
        self.alive = False
        events.append("die")
        return events

    def _tick(self) -> List[str]:
        """One snake step: move, collide, eat."""
        events: List[str] = []
        dx, dy = self.snake.consume_direction()
        hx, hy = self.snake.head
        new_head = (hx + dx, hy + dy)
        if self.mode is Mode.WRAP:
            new_head = (new_head[0] % GRID_COLS, new_head[1] % GRID_ROWS)
        elif not (0 <= new_head[0] < GRID_COLS and 0 <= new_head[1] < GRID_ROWS):
            return self._die(events)                         # wall

        eats_food = new_head == self.food.pos
        eats_bonus = self.bonus.active and new_head == self.bonus.pos
        grow = eats_food or eats_bonus
        # The tail cell is vacated this step, so it is only solid if the snake grows.
        solid = self.snake.body if grow else self.snake.body[:-1]
        if new_head in solid or new_head in self.obstacles:
            return self._die(events)

        self.snake.move_to(new_head, grow)

        if eats_bonus:
            self.score += BONUS_POINTS
            self.bonus.deactivate()
            events.append("bonus")
        if eats_food:
            self.score += FOOD_POINTS
            self.foods_eaten += 1
            events.append("eat")
            if not self.food.respawn(self._blocked(include_food=False), GRID_COLS, GRID_ROWS, self.rng):
                return self._die(events)                     # board completely full
            if self.foods_eaten >= self.next_bonus_at and not self.bonus.active:
                if self.bonus.spawn(self._blocked(), GRID_COLS, GRID_ROWS, self.rng):
                    self.next_bonus_at = self.foods_eaten + self.rng.randint(BONUS_EVERY_MIN, BONUS_EVERY_MAX)
        return events


# --------------------------------------------------------------------------- #
# The application
# --------------------------------------------------------------------------- #
class State(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    DYING = auto()
    GAME_OVER = auto()
    HIGH_SCORES = auto()


class Game:
    """Owns the window, state machine, input handling and rendering."""

    def __init__(self) -> None:
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        if IS_WEB:
            # The browser scales the canvas itself, so use a fixed logical size.
            pygame.display.set_mode((CANVAS_W, CANVAS_H))
        else:
            pygame.display.set_mode(self._initial_window_size(), pygame.RESIZABLE)
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H)).convert()
        self.clock = pygame.time.Clock()
        self.rng = random.Random()
        self.running = True
        self.time = 0.0

        self.fonts = ui.Fonts()
        self.sound = SoundManager()
        self.scores = HighScoreTable(SCORE_PATH)
        self.themes: List[Theme] = create_themes()
        self.theme_index = 0
        self.mode_index = 0
        self.difficulty_index = 1                               # Normal
        self.modes = list(Mode)

        click = lambda: self.sound.play("click")                # noqa: E731
        menu_items = [("play", "Play"), ("theme", ""), ("mode", ""), ("difficulty", ""),
                      ("scores", "High Scores")]
        if not IS_WEB:                                          # a browser tab can't "quit"
            menu_items.append(("quit", "Quit"))
        self.menu = ui.ButtonList(menu_items, top=240, on_move=click)
        self.pause_menu = ui.ButtonList(
            [("resume", "Resume"), ("restart", "Restart"), ("menu", "Menu")], top=275, on_move=click)
        self.over_menu = ui.ButtonList([("restart", "Restart"), ("menu", "Menu")], top=455, on_move=click)
        self.back_menu = ui.ButtonList([("back", "Back")], top=520, on_move=click)
        self.name_entry = ui.NameEntry()
        self.fade = ui.Fade(FADE_TIME)

        self.state = State.MENU
        self.session: Optional[GameSession] = None
        self.death_timer = 0.0
        self.death_done = False
        self.entering_name = False
        self.new_best = False
        self.made_table = False
        self.saved_rank: Optional[int] = None
        self.sound_icon_rect = pygame.Rect(0, 0, 0, 0)
        self.view_rect = pygame.Rect(0, 0, CANVAS_W, CANVAS_H)
        self.view_scale = 1.0
        self._refresh_menu_labels()

    # ----- setup helpers -------------------------------------------------- #
    @staticmethod
    def _initial_window_size() -> Tuple[int, int]:
        """Fit the window to the desktop (never larger than the logical canvas)."""
        info = pygame.display.Info()
        scale = 1.0
        if info.current_w > 0 and info.current_h > 0:
            scale = min(1.0, (info.current_w - 60) / CANVAS_W, (info.current_h - 120) / CANVAS_H)
        scale = max(scale, 0.5)
        return int(CANVAS_W * scale), int(CANVAS_H * scale)

    @property
    def theme(self) -> Theme:
        return self.themes[self.theme_index]

    @property
    def mode(self) -> Mode:
        return self.modes[self.mode_index]

    @property
    def difficulty(self) -> Difficulty:
        return DIFFICULTIES[self.difficulty_index]

    def _refresh_menu_labels(self) -> None:
        self.menu.set_label("theme", f"Theme: {self.theme.name}")
        self.menu.set_label("mode", f"Mode: {self.mode.value}")
        self.menu.set_label("difficulty", f"Difficulty: {self.difficulty.name}")

    # ----- coordinates ---------------------------------------------------- #
    def _update_view(self) -> None:
        """Compute where the scaled canvas sits in the (resizable) window."""
        sw, sh = pygame.display.get_surface().get_size()
        self.view_scale = max(0.01, min(sw / CANVAS_W, sh / CANVAS_H))
        w, h = max(1, int(CANVAS_W * self.view_scale)), max(1, int(CANVAS_H * self.view_scale))
        self.view_rect = pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)

    def _canvas_pos(self, pos: Tuple[int, int]) -> Tuple[float, float]:
        """Convert window coordinates to canvas coordinates."""
        return ((pos[0] - self.view_rect.x) / self.view_scale, (pos[1] - self.view_rect.y) / self.view_scale)

    # ----- state transitions ---------------------------------------------- #
    def _fade_to(self, callback) -> None:                      # type: ignore[no-untyped-def]
        self.fade.start(callback)

    def _start_game(self) -> None:
        self.session = GameSession(self.mode, self.difficulty, self.rng)
        self.state = State.PLAYING

    def _go_menu(self) -> None:
        self.state = State.MENU
        self.menu.reset()

    def _show_scores(self) -> None:
        self.state = State.HIGH_SCORES
        self.back_menu.reset()

    def _pause(self) -> None:
        self.state = State.PAUSED
        self.pause_menu.reset()
        self.sound.play("click")

    def _begin_death(self) -> None:
        self.state = State.DYING
        self.death_timer = 0.0
        self.death_done = False
        self.sound.play("gameover")

    def _enter_game_over(self) -> None:
        assert self.session is not None
        score = self.session.score
        self.new_best = score > 0 and score > self.scores.best
        self.made_table = self.scores.qualifies(score)
        self.entering_name = self.made_table
        self.saved_rank = None
        self.name_entry.reset()
        self.over_menu.reset()
        self.state = State.GAME_OVER

    def _submit_name(self) -> None:
        assert self.session is not None
        name = self.name_entry.text.strip() or "PLAYER"
        self.saved_rank = self.scores.add(name, self.session.score)
        self.entering_name = False
        self.sound.play("click")

    def _cycle_theme(self, step: int) -> None:
        self.theme_index = (self.theme_index + step) % len(self.themes)
        self._refresh_menu_labels()
        self.sound.play("click")

    # ----- events --------------------------------------------------------- #
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == getattr(pygame, "WINDOWFOCUSLOST", -1) and self.state is State.PLAYING:
            self._pause()                                     # auto-pause when the window loses focus
            return
        if self.fade.active:
            return                                            # ignore input during transitions
        pos = None
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            pos = self._canvas_pos(event.pos)
        if event.type == pygame.KEYDOWN and self._handle_global_key(event):
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and pos is not None
                and self.sound_icon_rect.collidepoint(pos)):
            self.sound.toggle_mute()
            return

        if self.state is State.MENU:
            result = self.menu.handle_event(event, pos)
            if result:
                self._menu_action(*result)
        elif self.state is State.PLAYING:
            self._playing_event(event)
        elif self.state is State.PAUSED:
            self._paused_event(event, pos)
        elif self.state is State.GAME_OVER:
            self._game_over_event(event, pos)
        elif self.state is State.HIGH_SCORES:
            self._scores_event(event, pos)

    def _handle_global_key(self, event: pygame.event.Event) -> bool:
        """M (mute), T (theme), F (Nokia frame) work everywhere except while typing a name."""
        if self.state is State.GAME_OVER and self.entering_name:
            return False
        if event.key == pygame.K_m:
            self.sound.toggle_mute()
            return True
        if event.key == pygame.K_t:
            self._cycle_theme(1)
            return True
        if event.key == pygame.K_f:
            self.theme.toggle_frame()
            return True
        return False

    def _menu_action(self, action: str, delta: int) -> None:
        step = delta or 1
        if action == "theme":
            self._cycle_theme(step)
        elif action == "mode":
            self.mode_index = (self.mode_index + step) % len(self.modes)
            self._refresh_menu_labels()
            self.sound.play("click")
        elif action == "difficulty":
            self.difficulty_index = (self.difficulty_index + step) % len(DIFFICULTIES)
            self._refresh_menu_labels()
            self.sound.play("click")
        elif delta == 0:
            self.sound.play("click")
            if action == "play":
                self._fade_to(self._start_game)
            elif action == "scores":
                self._fade_to(self._show_scores)
            elif action == "quit":
                self.running = False

    def _playing_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN or self.session is None:
            return
        if event.key in (pygame.K_p, pygame.K_ESCAPE):
            self._pause()
            return
        direction = KEY_TO_DIRECTION.get(event.key)
        if direction is not None:
            self.session.snake.queue_direction(direction)

    def _paused_event(self, event: pygame.event.Event, pos: Optional[Tuple[float, float]]) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = State.PLAYING
            return
        result = self.pause_menu.handle_event(event, pos)
        if result and result[1] == 0:
            self.sound.play("click")
            if result[0] == "resume":
                self.state = State.PLAYING
            elif result[0] == "restart":
                self._fade_to(self._start_game)
            elif result[0] == "menu":
                self._fade_to(self._go_menu)

    def _game_over_event(self, event: pygame.event.Event, pos: Optional[Tuple[float, float]]) -> None:
        if self.entering_name:
            if event.type == pygame.KEYDOWN and self.name_entry.handle_key(event):
                self._submit_name()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._fade_to(self._go_menu)
            return
        result = self.over_menu.handle_event(event, pos)
        if result and result[1] == 0:
            self.sound.play("click")
            self._fade_to(self._start_game if result[0] == "restart" else self._go_menu)

    def _scores_event(self, event: pygame.event.Event, pos: Optional[Tuple[float, float]]) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.sound.play("click")
            self._fade_to(self._go_menu)
            return
        result = self.back_menu.handle_event(event, pos)
        if result and result[1] == 0:
            self.sound.play("click")
            self._fade_to(self._go_menu)

    # ----- update --------------------------------------------------------- #
    def update(self, dt: float) -> None:
        self.fade.update(dt)
        if self.state is State.PLAYING and self.session is not None:
            for event in self.session.update(dt):
                if event == "eat":
                    self.sound.play("eat")
                elif event == "bonus":
                    self.sound.play("bonus")
                elif event == "die" and self.state is State.PLAYING:
                    self._begin_death()
        elif self.state is State.DYING:
            self.death_timer += dt
            if not self.death_done and self.death_timer >= DEATH_ANIM_TIME:
                self.death_done = True
                self._fade_to(self._enter_game_over)

    # ----- drawing -------------------------------------------------------- #
    def _draw_world(self) -> None:
        assert self.session is not None
        s, th, c = self.session, self.theme, self.canvas
        interpolating = self.state in (State.PLAYING, State.PAUSED)
        t = s.interpolation() if interpolating else 1.0
        th.draw_obstacles(c, s.obstacles)
        th.draw_food(c, s.food.pos, self.time)
        if s.bonus.active:
            th.draw_bonus(c, s.bonus.pos, self.time, s.bonus.ratio)
        visible = True
        if self.state is State.DYING:
            visible = int(self.death_timer / DEATH_BLINK_INTERVAL) % 2 == 0      # death blink
        if visible:
            th.draw_snake(c, s.snake, t, self.time)

    def draw(self) -> None:
        c, th, fonts = self.canvas, self.theme, self.fonts
        th.draw_background(c)
        self.sound_icon_rect = pygame.Rect(0, 0, 0, 0)

        if self.state in (State.PLAYING, State.PAUSED, State.DYING, State.GAME_OVER) and self.session:
            s = self.session
            ui.draw_chrome(c, th, fonts, show_header=True)
            self._draw_world()
            self.sound_icon_rect = ui.draw_hud(
                c, th, fonts, s.score, max(self.scores.best, s.score), s.level, self.sound.muted,
                s.bonus.ratio if s.bonus.active else None, self.time)
            if self.state is State.PAUSED:
                ui.draw_pause(c, th, fonts, self.pause_menu)
            elif self.state is State.GAME_OVER:
                ui.draw_game_over(c, th, fonts, s.score, self.new_best, self.made_table,
                                  self.entering_name, self.name_entry, self.saved_rank,
                                  self.over_menu, self.time)
        elif self.state is State.MENU:
            ui.draw_menu(c, th, fonts, self.menu)
        elif self.state is State.HIGH_SCORES:
            ui.draw_high_scores(c, th, fonts, self.scores.as_tuples(), self.back_menu)

        self.fade.draw(c)

    def present(self) -> None:
        """Scale the canvas into the window (letterboxed) and flip."""
        screen = pygame.display.get_surface()
        screen.fill(self.theme.bg)
        if self.view_rect.size == (CANVAS_W, CANVAS_H):
            screen.blit(self.canvas, self.view_rect.topleft)
        else:
            screen.blit(pygame.transform.smoothscale(self.canvas, self.view_rect.size), self.view_rect.topleft)
        pygame.display.flip()

    # ----- main loop ------------------------------------------------------ #
    async def run(self) -> None:
        """Render at FPS; the snake itself moves on its own accumulator timer."""
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, MAX_FRAME_TIME)
            self.time += dt
            self._update_view()
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
            self.present()
            await asyncio.sleep(0)                             # hand control back to the browser (required by pygbag)


async def main() -> int:
    """Create the game, run it, and always shut pygame down cleanly."""
    try:
        await Game().run()
    except KeyboardInterrupt:
        pass
    except Exception:                                          # pylint: disable=broad-except
        traceback.print_exc()
        print("\nSnake crashed - see the error above.", file=sys.stderr)
        return 1
    finally:
        if not IS_WEB:
            pygame.quit()
    return 0


asyncio.run(main())
