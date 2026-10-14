"""UI building blocks: fonts, buttons, HUD, overlays, name entry and screen fades."""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

import pygame

from settings import CANVAS_H, CANVAS_W, MAX_HIGH_SCORES, NAME_MAX_LEN, PLAY_W, PLAY_X
from themes import PLAY_RECT, Theme, draw_pixel_number


class Fonts:
    """Built-in pygame fonts at the sizes the UI needs (no font files required)."""

    def __init__(self) -> None:
        self.title = pygame.font.Font(None, 110)
        self.large = pygame.font.Font(None, 64)
        self.medium = pygame.font.Font(None, 38)
        self.small = pygame.font.Font(None, 26)


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, color: Tuple[int, int, int],
              pos: Tuple[float, float], anchor: str = "center",
              shadow: Optional[Tuple[int, int, int]] = None,
              shadow_offset: Tuple[int, int] = (3, 3)) -> pygame.Rect:
    """Render text anchored at ``pos`` (anchor is any pygame Rect attribute, e.g. 'midleft')."""
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow is not None:
        surface.blit(font.render(text, True, shadow), rect.move(*shadow_offset))
    surface.blit(img, rect)
    return rect


def draw_dim(surface: pygame.Surface, theme: Theme) -> None:
    """Darken (or lighten) the play area behind an overlay."""
    overlay = pygame.Surface(PLAY_RECT.size, pygame.SRCALPHA)
    overlay.fill(theme.dim)
    surface.blit(overlay, PLAY_RECT.topleft)


def draw_panel(surface: pygame.Surface, theme: Theme, rect: pygame.Rect) -> None:
    """Draw a themed panel."""
    pygame.draw.rect(surface, theme.panel, rect, border_radius=theme.radius + 4)
    pygame.draw.rect(surface, theme.panel_border, rect, 4, border_radius=theme.radius + 4)


# --------------------------------------------------------------------------- #
# Buttons
# --------------------------------------------------------------------------- #
class Button:
    """A single clickable button."""

    def __init__(self, action: str, label: str, rect: pygame.Rect) -> None:
        self.action = action
        self.label = label
        self.rect = rect

    def draw(self, surface: pygame.Surface, theme: Theme, fonts: Fonts, selected: bool) -> None:
        fill = theme.button_hover if selected else theme.button
        color = theme.button_text_hover if selected else theme.button_text
        pygame.draw.rect(surface, fill, self.rect, border_radius=theme.radius)
        pygame.draw.rect(surface, theme.panel_border, self.rect, 3, border_radius=theme.radius)
        draw_text(surface, fonts.medium, self.label, color, self.rect.center)
        if selected:
            cx, cy = self.rect.left + 20, self.rect.centery
            pygame.draw.polygon(surface, color, [(cx - 5, cy - 7), (cx + 5, cy), (cx - 5, cy + 7)])


class ButtonList:
    """A vertical list of buttons with keyboard and mouse navigation.

    ``handle_event`` returns ``(action, delta)`` where delta is 0 for activation
    (Enter/Space/left click), -1 for Left/right-click and +1 for Right.
    """

    def __init__(self, entries: Sequence[Tuple[str, str]], top: int, width: int = 340,
                 height: int = 46, gap: int = 8,
                 on_move: Optional[Callable[[], None]] = None) -> None:
        x = (CANVAS_W - width) // 2
        self.buttons: List[Button] = [
            Button(action, label, pygame.Rect(x, top + i * (height + gap), width, height))
            for i, (action, label) in enumerate(entries)
        ]
        self.index = 0
        self._on_move = on_move

    def reset(self) -> None:
        """Select the first button again."""
        self.index = 0

    def set_label(self, action: str, label: str) -> None:
        """Change the label of the button with the given action."""
        for button in self.buttons:
            if button.action == action:
                button.label = label

    def _select(self, index: int) -> None:
        if index != self.index:
            self.index = index
            if self._on_move:
                self._on_move()

    def handle_event(self, event: pygame.event.Event,
                     pos: Optional[Tuple[float, float]]) -> Optional[Tuple[str, int]]:
        """Process one event; ``pos`` is the mouse position in canvas coordinates."""
        count = len(self.buttons)
        current = self.buttons[self.index].action
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._select((self.index - 1) % count)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._select((self.index + 1) % count)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                return current, -1
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                return current, 1
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return current, 0
        elif event.type == pygame.MOUSEMOTION and pos is not None:
            for i, button in enumerate(self.buttons):
                if button.rect.collidepoint(pos):
                    self._select(i)
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and pos is not None and event.button in (1, 3):
            for i, button in enumerate(self.buttons):
                if button.rect.collidepoint(pos):
                    self._select(i)
                    return button.action, (0 if event.button == 1 else -1)
        return None

    def draw(self, surface: pygame.Surface, theme: Theme, fonts: Fonts) -> None:
        for i, button in enumerate(self.buttons):
            button.draw(surface, theme, fonts, i == self.index)


# --------------------------------------------------------------------------- #
# HUD and decoration
# --------------------------------------------------------------------------- #
def draw_chrome(surface: pygame.Surface, theme: Theme, fonts: Fonts, show_header: bool) -> None:
    """Title and controls footer for themes without their own frame."""
    if theme.has_frame:
        return
    if show_header:
        draw_text(surface, fonts.large, "SNAKE", theme.title_color, (CANVAS_W // 2, 42),
                  shadow=theme.title_shadow, shadow_offset=(2, 2))
    footer = pygame.Rect(PLAY_X, 646, PLAY_W, 96)
    draw_panel(surface, theme, footer)
    draw_text(surface, fonts.small, "Move: Arrows / WASD     Pause: P / Esc", theme.text, (CANVAS_W // 2, 676))
    draw_text(surface, fonts.small, "Mute: M     Theme: T     Frame (Nokia): F", theme.text_dim,
              (CANVAS_W // 2, 712))


def draw_sound_icon(surface: pygame.Surface, theme: Theme, center: Tuple[int, int], muted: bool) -> pygame.Rect:
    """Speaker icon (with waves, or a cross when muted). Returns its clickable rect."""
    cx, cy = center
    col = theme.text
    pygame.draw.polygon(surface, col, [(cx - 14, cy - 5), (cx - 8, cy - 5), (cx, cy - 12),
                                       (cx, cy + 12), (cx - 8, cy + 5), (cx - 14, cy + 5)])
    if muted:
        pygame.draw.line(surface, col, (cx + 5, cy - 6), (cx + 15, cy + 6), 3)
        pygame.draw.line(surface, col, (cx + 5, cy + 6), (cx + 15, cy - 6), 3)
    else:
        pygame.draw.arc(surface, col, pygame.Rect(cx - 4, cy - 8, 16, 16), -0.9, 0.9, 2)
        pygame.draw.arc(surface, col, pygame.Rect(cx - 2, cy - 13, 26, 26), -0.9, 0.9, 2)
    return pygame.Rect(cx - 20, cy - 20, 40, 40)


def _hud_item(surface: pygame.Surface, theme: Theme, fonts: Fonts, label: str, value: str,
              x: int, y: int) -> int:
    """Draw 'LABEL value' starting at x; returns the x where it ended."""
    if theme.pixel_digits and label == "SCORE":
        vx = x                                    # Nokia style: bare 4-digit score at top-left
    else:
        vx = draw_text(surface, fonts.small, label, theme.text_dim, (x, y), "midleft").right + 8
    if theme.pixel_digits:
        return vx + draw_pixel_number(surface, value, vx, y - 8, 3, theme.text)
    img = fonts.medium.render(value, True, theme.text)
    rect = img.get_rect(midleft=(vx, y))
    surface.blit(img, rect)
    return rect.right


def draw_hud(surface: pygame.Surface, theme: Theme, fonts: Fonts, score: int, best: int, level: int,
             muted: bool, bonus_ratio: Optional[float], time: float) -> pygame.Rect:
    """Score, high score, level, bonus timer bar and sound icon. Returns the icon rect."""
    y = 88
    _hud_item(surface, theme, fonts, "SCORE", f"{score:04d}", PLAY_X, y)
    _hud_item(surface, theme, fonts, "HI", f"{best:04d}", 262, y)
    _hud_item(surface, theme, fonts, "LV", f"{level:02d}", 420, y)
    if bonus_ratio is not None:
        if bonus_ratio > 0.3 or int(time * 4) % 2 == 0:
            draw_text(surface, fonts.small, "BONUS +50", theme.accent, (500, y), "midleft")
        bar = pygame.Rect(PLAY_X, 112, PLAY_W, 8)
        pygame.draw.rect(surface, theme.bar_bg, bar)
        fill = bar.copy()
        fill.width = max(0, int(PLAY_W * bonus_ratio))
        pygame.draw.rect(surface, theme.accent if bonus_ratio < 0.3 else theme.bar_fg, fill)
        pygame.draw.rect(surface, theme.panel_border, bar, 1)
    return draw_sound_icon(surface, theme, (CANVAS_W - PLAY_X - 18, y), muted)


# --------------------------------------------------------------------------- #
# Name entry
# --------------------------------------------------------------------------- #
class NameEntry:
    """Tiny text field for the high-score name."""

    def __init__(self, max_len: int = NAME_MAX_LEN) -> None:
        self.max_len = max_len
        self.text = ""

    def reset(self) -> None:
        self.text = ""

    def handle_key(self, event: pygame.event.Event) -> bool:
        """Process a KEYDOWN. Returns True when Enter was pressed."""
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return True
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        else:
            ch = event.unicode
            if (ch and ch.isascii() and ch.isprintable() and (ch.isalnum() or ch in " _-")
                    and len(self.text) < self.max_len):
                self.text += ch
        return False

    def draw(self, surface: pygame.Surface, theme: Theme, fonts: Fonts, rect: pygame.Rect, time: float) -> None:
        pygame.draw.rect(surface, theme.button, rect, border_radius=theme.radius)
        pygame.draw.rect(surface, theme.panel_border, rect, 3, border_radius=theme.radius)
        img = fonts.medium.render(self.text, True, theme.button_text)
        r = img.get_rect(midleft=(rect.x + 14, rect.centery))
        surface.blit(img, r)
        if int(time * 2) % 2 == 0:
            pygame.draw.rect(surface, theme.button_text, (r.right + 3, rect.centery - 12, 3, 24))


# --------------------------------------------------------------------------- #
# Overlays / screens
# --------------------------------------------------------------------------- #
def draw_menu(surface: pygame.Surface, theme: Theme, fonts: Fonts, buttons: ButtonList) -> None:
    """Main menu: big title plus the button list inside the play area."""
    draw_chrome(surface, theme, fonts, show_header=False)
    draw_text(surface, fonts.title, "SNAKE", theme.title_color, (CANVAS_W // 2, 188),
              shadow=theme.title_shadow, shadow_offset=(4, 4))
    buttons.draw(surface, theme, fonts)


def draw_pause(surface: pygame.Surface, theme: Theme, fonts: Fonts, buttons: ButtonList) -> None:
    """Pause overlay with Resume / Restart / Menu."""
    draw_dim(surface, theme)
    panel = pygame.Rect(160, 185, 400, 320)
    draw_panel(surface, theme, panel)
    draw_text(surface, fonts.large, "PAUSED", theme.title_color, (CANVAS_W // 2, 232),
              shadow=theme.title_shadow, shadow_offset=(3, 3))
    buttons.draw(surface, theme, fonts)
    draw_text(surface, fonts.small, "P / Esc to resume", theme.text_dim, (CANVAS_W // 2, 470))


def draw_game_over(surface: pygame.Surface, theme: Theme, fonts: Fonts, score: int, new_best: bool,
                   made_table: bool, entering: bool, name_entry: NameEntry, saved_rank: Optional[int],
                   buttons: ButtonList, time: float) -> None:
    """Game-over panel: score, high-score message, name entry and Restart / Menu."""
    draw_dim(surface, theme)
    draw_panel(surface, theme, pygame.Rect(130, 165, 460, 415))
    cx = CANVAS_W // 2
    draw_text(surface, fonts.large, "GAME OVER", theme.title_color, (cx, 212),
              shadow=theme.title_shadow, shadow_offset=(3, 3))
    draw_text(surface, fonts.medium, f"Score  {score:04d}", theme.text, (cx, 268))
    pulse = theme.accent if int(time * 3) % 2 == 0 else theme.text
    if new_best:
        draw_text(surface, fonts.medium, "New High Score!", pulse, (cx, 312))
    elif made_table:
        draw_text(surface, fonts.medium, "You made the Top 5!", pulse, (cx, 312))
    else:
        draw_text(surface, fonts.small, "Good game!", theme.text_dim, (cx, 312))
    if entering:
        draw_text(surface, fonts.small, "Enter your name:", theme.text, (cx, 352))
        name_entry.draw(surface, theme, fonts, pygame.Rect(cx - 150, 372, 300, 46), time)
        draw_text(surface, fonts.small, "Press Enter to save", theme.text_dim, (cx, 440))
    else:
        if saved_rank is not None:
            draw_text(surface, fonts.medium, f"Saved - rank #{saved_rank}", theme.text, (cx, 380))
        buttons.draw(surface, theme, fonts)


def draw_high_scores(surface: pygame.Surface, theme: Theme, fonts: Fonts,
                     entries: Sequence[Tuple[str, int]], buttons: ButtonList) -> None:
    """Top-5 table."""
    draw_chrome(surface, theme, fonts, show_header=True)
    draw_dim(surface, theme)
    draw_panel(surface, theme, pygame.Rect(110, 160, 500, 430))
    draw_text(surface, fonts.large, "HIGH SCORES", theme.title_color, (CANVAS_W // 2, 205),
              shadow=theme.title_shadow, shadow_offset=(3, 3))
    for i in range(MAX_HIGH_SCORES):
        y = 262 + i * 46
        filled = i < len(entries)
        name, score = entries[i] if filled else ("---", 0)
        color = theme.text if filled else theme.text_dim
        draw_text(surface, fonts.medium, f"{i + 1}.", color, (170, y), "midleft")
        draw_text(surface, fonts.medium, name, color, (230, y), "midleft")
        draw_text(surface, fonts.medium, f"{score:04d}", color, (550, y), "midright")
    buttons.draw(surface, theme, fonts)


# --------------------------------------------------------------------------- #
# Fade transition
# --------------------------------------------------------------------------- #
class Fade:
    """Fade to black, run a callback at the darkest point, then fade back in."""

    def __init__(self, duration: float) -> None:
        self.duration = duration
        self.active = False
        self._elapsed = 0.0
        self._fired = False
        self._callback: Optional[Callable[[], None]] = None
        self._overlay = pygame.Surface((CANVAS_W, CANVAS_H))
        self._overlay.fill((0, 0, 0))

    def start(self, callback: Callable[[], None]) -> bool:
        """Begin a transition. Ignored (returns False) if one is already running."""
        if self.active:
            return False
        self.active = True
        self._elapsed = 0.0
        self._fired = False
        self._callback = callback
        return True

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self._elapsed += dt
        if not self._fired and self._elapsed >= self.duration / 2:
            self._fired = True
            if self._callback:
                self._callback()
        if self._elapsed >= self.duration:
            self.active = False

    @property
    def alpha(self) -> int:
        """Current overlay opacity 0..255."""
        if not self.active:
            return 0
        half = self.duration / 2
        frac = self._elapsed / half if self._elapsed < half else max(0.0, 2.0 - self._elapsed / half)
        return int(255 * min(1.0, frac))

    def draw(self, surface: pygame.Surface) -> None:
        a = self.alpha
        if a > 0:
            self._overlay.set_alpha(a)
            surface.blit(self._overlay, (0, 0))
