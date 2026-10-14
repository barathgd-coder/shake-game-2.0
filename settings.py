"""Game-wide constants: grid geometry, timing, colours, modes and difficulty presets."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

Color = Tuple[int, int, int]
Vec = Tuple[int, int]

# --------------------------------------------------------------------------- #
# Grid and logical canvas (everything is drawn on a fixed canvas that is then
# scaled to the real window, so resizing always keeps correct proportions).
# --------------------------------------------------------------------------- #
GRID_COLS = 25
GRID_ROWS = 20
CELL = 24
PLAY_W = GRID_COLS * CELL            # 600
PLAY_H = GRID_ROWS * CELL            # 480
CANVAS_W = 720
CANVAS_H = 780
PLAY_X = (CANVAS_W - PLAY_W) // 2    # 60
PLAY_Y = 132

FPS = 60
MAX_FRAME_TIME = 0.1                 # clamp dt so a stall never causes a burst of moves
WINDOW_TITLE = "Snake"

# Directions as (dx, dy)
UP: Vec = (0, -1)
DOWN: Vec = (0, 1)
LEFT: Vec = (-1, 0)
RIGHT: Vec = (1, 0)

# --------------------------------------------------------------------------- #
# Gameplay tuning
# --------------------------------------------------------------------------- #
START_LENGTH = 3
FOOD_POINTS = 10
BONUS_POINTS = 50
SPEEDUP_EVERY = 5                    # foods per level
BONUS_EVERY_MIN = 6                  # bonus food appears every 6-8 foods (~7)
BONUS_EVERY_MAX = 8
BONUS_LIFETIME = 5.0                 # seconds
MAX_QUEUED_INPUTS = 2
OBSTACLE_CLUSTERS = 9
START_GRACE = 0.35                   # short pause before the snake starts moving

DEATH_ANIM_TIME = 1.2
DEATH_BLINK_INTERVAL = 0.15
FADE_TIME = 0.45

MAX_HIGH_SCORES = 5
NAME_MAX_LEN = 10
HIGHSCORE_FILE = "highscore.json"


class Mode(Enum):
    """Selectable game modes."""
    CLASSIC = "Classic"
    WRAP = "Wrap-around"
    OBSTACLES = "Obstacles"


@dataclass(frozen=True)
class Difficulty:
    """Seconds per snake step: start_delay - delay_step * (level - 1), never below min_delay."""
    name: str
    start_delay: float
    delay_step: float
    min_delay: float


DIFFICULTIES: Tuple[Difficulty, ...] = (
    Difficulty("Easy", 0.16, 0.006, 0.075),
    Difficulty("Normal", 0.12, 0.007, 0.055),
    Difficulty("Hard", 0.09, 0.008, 0.040),
)

# --------------------------------------------------------------------------- #
# Colours
# --------------------------------------------------------------------------- #
# Nokia 3310
NOKIA_LCD: Color = (163, 213, 15)
NOKIA_LCD_SHADE: Color = (147, 197, 12)
NOKIA_INK: Color = (20, 30, 8)
NOKIA_INK_SOFT: Color = (66, 96, 20)
NOKIA_BACKDROP: Color = (24, 28, 34)
NOKIA_BODY: Color = (112, 118, 126)
NOKIA_BODY_EDGE: Color = (74, 79, 87)
NOKIA_BEZEL: Color = (52, 57, 63)
NOKIA_KEY: Color = (88, 94, 102)

# Retro Pixel (Game Boy style 4-shade palette on a very dark green background)
GB_BG: Color = (6, 22, 6)
GB_FIELD: Color = (11, 38, 11)
GB_DARKEST: Color = (15, 56, 15)
GB_DARK: Color = (48, 98, 48)
GB_LIGHT: Color = (139, 172, 15)
GB_LIGHTEST: Color = (196, 224, 96)

# Modern Cartoon
CARTOON_BG: Color = (222, 205, 165)
CARTOON_CREAM: Color = (245, 236, 210)
CARTOON_FIELD: Color = (252, 246, 228)
CARTOON_SPECKLE: Color = (214, 196, 160)
CARTOON_BROWN: Color = (92, 64, 38)
CARTOON_BORDER: Color = (150, 110, 70)
CARTOON_GREEN: Color = (104, 190, 70)
CARTOON_GREEN_DARK: Color = (40, 110, 52)
CARTOON_OUTLINE: Color = (34, 90, 44)
CARTOON_YELLOW: Color = (250, 205, 70)
CARTOON_RED: Color = (220, 52, 46)
CARTOON_RED_DARK: Color = (150, 30, 30)
CARTOON_GOLD: Color = (255, 200, 40)
CARTOON_GOLD_DARK: Color = (190, 130, 20)
CARTOON_LEAF: Color = (78, 164, 62)
CARTOON_STEM: Color = (110, 72, 40)
CARTOON_STONE: Color = (158, 148, 136)
CARTOON_STONE_DARK: Color = (112, 102, 92)
