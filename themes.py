"""Theme rendering for the Snake game.

Each theme draws its own background, snake, food, bonus food and obstacles and
exposes a small palette that the UI module uses for buttons, panels and the HUD.
"""
from __future__ import annotations

import math
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pygame

from settings import (
    CANVAS_H, CANVAS_W, CELL, GRID_COLS, GRID_ROWS, PLAY_H, PLAY_W, PLAY_X, PLAY_Y,
    CARTOON_BG, CARTOON_BORDER, CARTOON_BROWN, CARTOON_CREAM, CARTOON_FIELD,
    CARTOON_GOLD, CARTOON_GOLD_DARK, CARTOON_GREEN, CARTOON_GREEN_DARK, CARTOON_LEAF,
    CARTOON_OUTLINE, CARTOON_RED, CARTOON_RED_DARK, CARTOON_SPECKLE, CARTOON_STEM,
    CARTOON_STONE, CARTOON_STONE_DARK, CARTOON_YELLOW,
    GB_BG, GB_DARK, GB_DARKEST, GB_FIELD, GB_LIGHT, GB_LIGHTEST,
    NOKIA_BACKDROP, NOKIA_BEZEL, NOKIA_BODY, NOKIA_BODY_EDGE, NOKIA_INK,
    NOKIA_INK_SOFT, NOKIA_KEY, NOKIA_LCD, NOKIA_LCD_SHADE,
    Color, Vec,
)
from snake import Snake

PLAY_RECT = pygame.Rect(PLAY_X, PLAY_Y, PLAY_W, PLAY_H)
RGBA = Tuple[int, int, int, int]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def cell_rect(pos: Vec) -> pygame.Rect:
    """Pixel rectangle (on the canvas) of a grid cell."""
    return pygame.Rect(PLAY_X + pos[0] * CELL, PLAY_Y + pos[1] * CELL, CELL, CELL)


def grid_to_px(gx: float, gy: float) -> Tuple[int, int]:
    """Pixel centre of a (possibly fractional) grid position."""
    return (int(round(PLAY_X + (gx + 0.5) * CELL)), int(round(PLAY_Y + (gy + 0.5) * CELL)))


def build_pixel_surface(rows: Sequence[str], colors: Dict[str, Color], px: int) -> pygame.Surface:
    """Turn a grid of characters into a surface; characters missing from ``colors`` are transparent."""
    surf = pygame.Surface((len(rows[0]) * px, len(rows) * px), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = colors.get(ch)
            if color is not None:
                surf.fill(color, (x * px, y * px, px, px))
    return surf


# 3x5 pixel digits for the Nokia-style score read-out.
_DIGITS: Dict[str, Tuple[str, ...]] = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}


def draw_pixel_number(surface: pygame.Surface, text: str, x: int, y: int, px: int, color: Color) -> int:
    """Draw digits as LCD-style pixel blocks. Returns the total width drawn."""
    cx = x
    for ch in text:
        glyph = _DIGITS.get(ch)
        if glyph:
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        surface.fill(color, (cx + c * px, y + r * px, px - 1, px - 1))
        cx += 4 * px
    return max(0, cx - x - px)


_ANGLE: Dict[Vec, int] = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}


# --------------------------------------------------------------------------- #
# Base class
# --------------------------------------------------------------------------- #
class Theme:
    """Interface and palette shared by all themes."""

    name: str = "Theme"
    smooth: bool = False          # True: snake is drawn interpolated between cells
    pixel_digits: bool = False    # True: HUD numbers use the LCD pixel font
    radius: int = 8               # button / panel corner radius

    bg: Color = (0, 0, 0)
    text: Color = (255, 255, 255)
    text_dim: Color = (180, 180, 180)
    accent: Color = (255, 255, 255)
    title_color: Color = (255, 255, 255)
    title_shadow: Optional[Color] = None
    panel: Color = (30, 30, 30)
    panel_border: Color = (200, 200, 200)
    button: Color = (50, 50, 50)
    button_hover: Color = (200, 200, 200)
    button_text: Color = (255, 255, 255)
    button_text_hover: Color = (0, 0, 0)
    bar_fg: Color = (255, 255, 255)
    bar_bg: Color = (60, 60, 60)
    dim: RGBA = (0, 0, 0, 150)

    @property
    def has_frame(self) -> bool:
        """True when the theme draws its own decorative frame (Nokia phone)."""
        return False

    def toggle_frame(self) -> None:
        """Toggle the optional frame (only meaningful for the Nokia theme)."""

    def draw_background(self, surface: pygame.Surface) -> None:
        raise NotImplementedError

    def draw_obstacles(self, surface: pygame.Surface, cells: Iterable[Vec]) -> None:
        raise NotImplementedError

    def draw_food(self, surface: pygame.Surface, pos: Vec, time: float) -> None:
        raise NotImplementedError

    def draw_bonus(self, surface: pygame.Surface, pos: Vec, time: float, ratio: float) -> None:
        raise NotImplementedError

    def draw_snake(self, surface: pygame.Surface, snake: Snake, t: float, time: float) -> None:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# 1. Nokia 3310 Classic
# --------------------------------------------------------------------------- #
class NokiaTheme(Theme):
    """Yellow-green LCD with black pixel blocks and an optional phone frame."""

    name = "Nokia 3310"
    pixel_digits = True
    radius = 3
    bg = NOKIA_BACKDROP
    text = NOKIA_INK
    text_dim = NOKIA_INK_SOFT
    accent = NOKIA_INK
    title_color = NOKIA_INK
    title_shadow = None
    panel = NOKIA_LCD
    panel_border = NOKIA_INK
    button = NOKIA_LCD_SHADE
    button_hover = NOKIA_INK
    button_text = NOKIA_INK
    button_text_hover = NOKIA_LCD
    bar_fg = NOKIA_INK
    bar_bg = NOKIA_LCD_SHADE
    dim = (163, 213, 15, 175)

    def __init__(self) -> None:
        self.frame_enabled = True
        self._bg_framed = self._build_bg(True)
        self._bg_plain = self._build_bg(False)

    @property
    def has_frame(self) -> bool:
        return self.frame_enabled

    def toggle_frame(self) -> None:
        self.frame_enabled = not self.frame_enabled

    @staticmethod
    def _build_bg(framed: bool) -> pygame.Surface:
        s = pygame.Surface((CANVAS_W, CANVAS_H))
        if framed:
            s.fill(NOKIA_BACKDROP)
            body = pygame.Rect(14, 10, 692, 756)
            pygame.draw.rect(s, NOKIA_BODY, body, border_radius=70)
            pygame.draw.rect(s, NOKIA_BODY_EDGE, body, 4, border_radius=70)
            logo_font = pygame.font.Font(None, 46)
            logo_font.set_bold(True)
            logo = logo_font.render("NOKIA", True, (40, 44, 50))
            s.blit(logo, logo.get_rect(center=(CANVAS_W // 2, 34)))
            pygame.draw.rect(s, NOKIA_BEZEL, (30, 56, 660, 588), border_radius=30)
            pygame.draw.rect(s, NOKIA_LCD, (44, 70, 632, 560), border_radius=12)
            # Keypad: two rows of three keys.
            key_font = pygame.font.Font(None, 32)
            key_w, key_h, gap = 130, 40, 16
            x0 = (CANVAS_W - (3 * key_w + 2 * gap)) // 2
            for row in range(2):
                for col in range(3):
                    rect = pygame.Rect(x0 + col * (key_w + gap), 660 + row * 52, key_w, key_h)
                    pygame.draw.rect(s, NOKIA_KEY, rect, border_radius=18)
                    pygame.draw.rect(s, NOKIA_BODY_EDGE, rect, 3, border_radius=18)
                    label = key_font.render(str(row * 3 + col + 1), True, (205, 210, 215))
                    s.blit(label, label.get_rect(center=rect.center))
        else:
            s.fill(NOKIA_LCD)
        pygame.draw.rect(s, NOKIA_INK, PLAY_RECT.inflate(8, 8), 2)   # thin pixel border
        return s.convert()

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg_framed if self.frame_enabled else self._bg_plain, (0, 0))

    def draw_obstacles(self, surface: pygame.Surface, cells: Iterable[Vec]) -> None:
        for pos in cells:
            r = cell_rect(pos)
            pygame.draw.rect(surface, NOKIA_INK, r.inflate(-2, -2))
            pygame.draw.rect(surface, NOKIA_LCD, r.inflate(-12, -12))
            pygame.draw.rect(surface, NOKIA_INK, r.inflate(-16, -16))

    def draw_food(self, surface: pygame.Surface, pos: Vec, time: float) -> None:
        cx, cy = cell_rect(pos).center
        for dx, dy in ((0, -7), (7, 0), (0, 7), (-7, 0)):     # four pixels forming a diamond
            surface.fill(NOKIA_INK, (cx + dx - 3, cy + dy - 3, 6, 6))

    def draw_bonus(self, surface: pygame.Surface, pos: Vec, time: float, ratio: float) -> None:
        if ratio < 0.35 and int(time * 8) % 2:
            return                                           # blink when about to vanish
        cx, cy = cell_rect(pos).center
        surface.fill(NOKIA_INK, (cx - 10, cy - 3, 20, 6))
        surface.fill(NOKIA_INK, (cx - 3, cy - 10, 6, 20))
        for dx, dy in ((-8, -8), (8, -8), (-8, 8), (8, 8)):
            surface.fill(NOKIA_INK, (cx + dx - 2, cy + dy - 2, 4, 4))

    def draw_snake(self, surface: pygame.Surface, snake: Snake, t: float, time: float) -> None:
        for pos in snake.body:
            pygame.draw.rect(surface, NOKIA_INK, cell_rect(pos).inflate(-4, -4))
        head = cell_rect(snake.head)
        fx, fy = snake.direction
        px, py = -fy, fx
        for side in (-1, 1):                                  # two LCD-coloured eye pixels
            ex = head.centerx + fx * 5 + px * 5 * side
            ey = head.centery + fy * 5 + py * 5 * side
            surface.fill(NOKIA_LCD, (ex - 1, ey - 1, 3, 3))


# --------------------------------------------------------------------------- #
# 2. Retro Pixel (Game Boy palette)
# --------------------------------------------------------------------------- #
# 12x12 head facing right. O=outline B=body E=eye W=shine F=fang T=tongue.
HEAD_ROWS: Tuple[str, ...] = (
    "............",
    "..OOOOOOO...",
    ".OBBBBBBBO..",
    ".OBBBEEBBO..",
    ".OBBBEWBFO.T",
    ".OBBBBBBBOTT",
    ".OBBBBBBBOTT",
    ".OBBBEWBFO.T",
    ".OBBBEEBBO..",
    ".OBBBBBBBO..",
    "..OOOOOOO...",
    "............",
)
APPLE_ROWS: Tuple[str, ...] = (
    "....OO..",
    "...O....",
    ".LLLLLL.",
    "LLWLLLLL",
    "LLWLLLLL",
    "LLLLLLLL",
    ".LLLLLL.",
    "..LL.LL.",
)
STAR_ROWS: Tuple[str, ...] = (
    "...LL...",
    "...LL...",
    "..LLLL..",
    "LLLLLLLL",
    "LLLLLLLL",
    "..LLLL..",
    "...LL...",
    "...LL...",
)


class RetroTheme(Theme):
    """Four-shade green palette with a pixel-art snake head."""

    name = "Retro Pixel"
    radius = 0
    bg = GB_BG
    text = GB_LIGHTEST
    text_dim = GB_LIGHT
    accent = GB_LIGHTEST
    title_color = GB_LIGHTEST
    title_shadow = GB_DARK
    panel = (12, 44, 12)
    panel_border = GB_LIGHT
    button = GB_DARKEST
    button_hover = GB_LIGHT
    button_text = GB_LIGHTEST
    button_text_hover = GB_BG
    bar_fg = GB_LIGHT
    bar_bg = GB_DARKEST
    dim = (4, 14, 4, 175)

    _HEAD_COLORS: Dict[str, Color] = {
        "O": GB_DARK, "B": GB_LIGHT, "E": GB_DARKEST, "W": GB_LIGHTEST,
        "F": GB_LIGHTEST, "T": GB_LIGHTEST,
    }

    def __init__(self) -> None:
        self._bg = self._build_bg()
        self._heads: Dict[Tuple[Vec, bool], pygame.Surface] = {}
        self._apple = build_pixel_surface(
            APPLE_ROWS, {"O": GB_DARK, "L": GB_LIGHTEST, "W": GB_LIGHT}, 3)
        self._star_a = build_pixel_surface(STAR_ROWS, {"L": GB_LIGHTEST}, 3)
        self._star_b = build_pixel_surface(STAR_ROWS, {"L": GB_LIGHT}, 3)

    @staticmethod
    def _build_bg() -> pygame.Surface:
        s = pygame.Surface((CANVAS_W, CANVAS_H))
        s.fill(GB_BG)
        pygame.draw.rect(s, GB_FIELD, PLAY_RECT)
        for gx in range(GRID_COLS):                          # faint dot grid
            for gy in range(GRID_ROWS):
                s.fill(GB_DARKEST, (PLAY_X + gx * CELL + 11, PLAY_Y + gy * CELL + 11, 2, 2))
        pygame.draw.rect(s, GB_DARK, PLAY_RECT.inflate(12, 12), 4)
        pygame.draw.rect(s, GB_LIGHT, PLAY_RECT.inflate(20, 20), 2)
        return s.convert()

    def _head_surface(self, direction: Vec, tongue: bool) -> pygame.Surface:
        key = (direction, tongue)
        surf = self._heads.get(key)
        if surf is None:
            colors = dict(self._HEAD_COLORS)
            if not tongue:
                colors.pop("T")
            surf = pygame.transform.rotate(build_pixel_surface(HEAD_ROWS, colors, 2), _ANGLE[direction])
            self._heads[key] = surf
        return surf

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))

    def draw_obstacles(self, surface: pygame.Surface, cells: Iterable[Vec]) -> None:
        for pos in cells:
            r = cell_rect(pos)
            inner = r.inflate(-2, -2)
            pygame.draw.rect(surface, GB_DARK, inner)
            pygame.draw.rect(surface, GB_DARKEST, inner, 2)
            pygame.draw.line(surface, GB_DARKEST, (r.x + 2, r.centery), (r.right - 3, r.centery), 2)
            pygame.draw.line(surface, GB_DARKEST, (r.centerx, r.y + 2), (r.centerx, r.centery), 2)
            pygame.draw.line(surface, GB_DARKEST, (r.x + 8, r.centery), (r.x + 8, r.bottom - 3), 2)

    def draw_food(self, surface: pygame.Surface, pos: Vec, time: float) -> None:
        surface.blit(self._apple, cell_rect(pos).topleft)

    def draw_bonus(self, surface: pygame.Surface, pos: Vec, time: float, ratio: float) -> None:
        if ratio < 0.3 and int(time * 8) % 2:
            return
        star = self._star_a if int(time * 4) % 2 == 0 else self._star_b
        surface.blit(star, cell_rect(pos).topleft)

    def draw_snake(self, surface: pygame.Surface, snake: Snake, t: float, time: float) -> None:
        for pos in snake.body[1:]:
            outer = cell_rect(pos).inflate(-2, -2)
            inner = outer.inflate(-6, -6)
            pygame.draw.rect(surface, GB_DARK, outer)         # darker outline
            pygame.draw.rect(surface, GB_LIGHT, inner)        # body
            surface.fill(GB_LIGHTEST, (inner.x + 2, inner.y + 2, 2, 2))
        head = self._head_surface(snake.direction, int(time * 2) % 2 == 0)   # tongue flicks
        surface.blit(head, cell_rect(snake.head).topleft)


# --------------------------------------------------------------------------- #
# 3. Modern Cartoon
# --------------------------------------------------------------------------- #
class CartoonTheme(Theme):
    """Cream background, smooth rounded snake with sleepy eyes, apple food."""

    name = "Modern Cartoon"
    smooth = True
    radius = 16
    bg = CARTOON_BG
    text = CARTOON_BROWN
    text_dim = (140, 110, 80)
    accent = (214, 64, 48)
    title_color = CARTOON_GREEN
    title_shadow = CARTOON_GREEN_DARK
    panel = (255, 248, 228)
    panel_border = CARTOON_BORDER
    button = (255, 240, 205)
    button_hover = CARTOON_GREEN
    button_text = CARTOON_BROWN
    button_text_hover = (255, 255, 255)
    bar_fg = (240, 170, 30)
    bar_bg = (230, 215, 185)
    dim = (60, 40, 20, 140)

    def __init__(self) -> None:
        self._bg = self._build_bg()

    @staticmethod
    def _build_bg() -> pygame.Surface:
        rng = random.Random(11)                              # fixed seed: same speckles every run
        s = pygame.Surface((CANVAS_W, CANVAS_H))
        s.fill(CARTOON_CREAM)
        for _ in range(420):
            pos = (rng.randrange(CANVAS_W), rng.randrange(CANVAS_H))
            pygame.draw.circle(s, CARTOON_SPECKLE, pos, rng.choice((1, 1, 2)))
        pygame.draw.rect(s, CARTOON_FIELD, PLAY_RECT, border_radius=14)
        for _ in range(160):
            pos = (rng.randrange(PLAY_X + 10, PLAY_X + PLAY_W - 10),
                   rng.randrange(PLAY_Y + 10, PLAY_Y + PLAY_H - 10))
            pygame.draw.circle(s, (238, 226, 196), pos, rng.choice((1, 1, 2)))
        pygame.draw.rect(s, CARTOON_BORDER, PLAY_RECT.inflate(12, 12), 6, border_radius=20)
        return s.convert()

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))

    def draw_obstacles(self, surface: pygame.Surface, cells: Iterable[Vec]) -> None:
        for pos in cells:
            r = cell_rect(pos).inflate(-2, -2)
            pygame.draw.rect(surface, CARTOON_STONE_DARK, r, border_radius=7)
            pygame.draw.rect(surface, CARTOON_STONE, r.inflate(-4, -4), border_radius=6)
            pygame.draw.circle(surface, (190, 182, 172), (r.x + 8, r.y + 8), 3)

    @staticmethod
    def _apple(surface: pygame.Surface, cx: int, cy: int, body: Color, outline: Color) -> None:
        lobes = ((-3, 0, 8), (3, 0, 8), (0, 1, 8))
        for dx, dy, r in lobes:
            pygame.draw.circle(surface, outline, (cx + dx, cy + dy), r + 1)
        for dx, dy, r in lobes:
            pygame.draw.circle(surface, body, (cx + dx, cy + dy), r)
        pygame.draw.circle(surface, (255, 235, 225), (cx - 5, cy - 3), 2)        # highlight
        pygame.draw.line(surface, CARTOON_STEM, (cx, cy - 6), (cx + 1, cy - 11), 2)
        pygame.draw.polygon(surface, CARTOON_LEAF,
                            [(cx + 2, cy - 9), (cx + 8, cy - 13), (cx + 12, cy - 9), (cx + 7, cy - 6)])

    def draw_food(self, surface: pygame.Surface, pos: Vec, time: float) -> None:
        cx, cy = cell_rect(pos).center
        bob = int(round(math.sin(time * 4.0) * 1.5))
        self._apple(surface, cx, cy + 2 + bob, CARTOON_RED, CARTOON_RED_DARK)

    def draw_bonus(self, surface: pygame.Surface, pos: Vec, time: float, ratio: float) -> None:
        if ratio < 0.3 and int(time * 8) % 2:
            return
        cx, cy = cell_rect(pos).center
        bob = int(round(math.sin(time * 6.0) * 2))
        self._apple(surface, cx, cy + 2 + bob, CARTOON_GOLD, CARTOON_GOLD_DARK)
        if int(time * 3) % 2 == 0:                                               # sparkles
            for sx, sy in ((cx + 10, cy - 8), (cx - 10, cy + 7)):
                pygame.draw.line(surface, (255, 255, 255), (sx - 3, sy), (sx + 3, sy), 2)
                pygame.draw.line(surface, (255, 255, 255), (sx, sy - 3), (sx, sy + 3), 2)

    @staticmethod
    def _stroke(surface: pygame.Surface, pts: List[Tuple[int, int]], width: int, color: Color) -> None:
        """Draw a thick rounded polyline (circles at joints + lines between them)."""
        radius = width // 2
        for i, p in enumerate(pts):
            pygame.draw.circle(surface, color, p, radius)
            if i > 0:
                q = pts[i - 1]
                if abs(p[0] - q[0]) + abs(p[1] - q[1]) <= CELL * 1.6:   # skip wrap-around jumps
                    pygame.draw.line(surface, color, q, p, width)

    def draw_snake(self, surface: pygame.Surface, snake: Snake, t: float, time: float) -> None:
        pts = [grid_to_px(x, y) for x, y in snake.render_positions(t)]
        self._stroke(surface, pts, 24, CARTOON_OUTLINE)
        self._stroke(surface, pts, 20, CARTOON_GREEN)
        for i in range(1, len(pts)):                          # dark diamonds with yellow centres
            x, y = pts[i]
            d = 6
            pygame.draw.polygon(surface, CARTOON_GREEN_DARK, [(x, y - d), (x + d, y), (x, y + d), (x - d, y)])
            pygame.draw.circle(surface, CARTOON_YELLOW, (x, y), 2)

        # Rounded head with sleepy eyes.
        hx, hy = pts[0]
        fx, fy = snake.direction
        px, py = -fy, fx
        pygame.draw.circle(surface, CARTOON_OUTLINE, (hx, hy), 14)
        pygame.draw.circle(surface, CARTOON_GREEN, (hx, hy), 12)
        pygame.draw.circle(surface, CARTOON_YELLOW, (hx - fx * 5, hy - fy * 5), 3)    # yellow head spot
        for side in (-1, 1):
            pygame.draw.circle(surface, CARTOON_GREEN_DARK,
                               (hx + fx * 9 + px * 3 * side, hy + fy * 9 + py * 3 * side), 1)   # nostrils
        for side in (-1, 1):
            ex = hx + fx * 3 + px * 6 * side
            ey = hy + fy * 3 + py * 6 * side
            r = 5
            pygame.draw.circle(surface, (255, 255, 255), (ex, ey), r)
            pygame.draw.circle(surface, (30, 30, 30), (ex + fx, ey + fy), 2)
            lid = [(ex - px * r, ey - py * r), (ex + px * r, ey + py * r),
                   (ex + px * r - fx * r, ey + py * r - fy * r), (ex - px * r - fx * r, ey - py * r - fy * r)]
            pygame.draw.polygon(surface, CARTOON_GREEN, lid)                          # droopy lid
            pygame.draw.line(surface, CARTOON_OUTLINE, (ex - px * r, ey - py * r), (ex + px * r, ey + py * r), 2)


def create_themes() -> List[Theme]:
    """Return the three themes in menu order."""
    return [NokiaTheme(), RetroTheme(), CartoonTheme()]
