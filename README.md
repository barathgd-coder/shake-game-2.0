# Snake (Pygame)

A polished Snake game with three visual themes, three game modes, three difficulty
levels, a top-5 high-score table and code-generated sound effects. No asset files needed.

## Install

Requires Python 3.9+.

```bash
cd snake_game
pip install -r requirements.txt      # installs pygame-ce (works on new Python versions too)
```

## Run

```bash
python main.py
```

## Controls

| Key / input | Action |
|---|---|
| Arrow keys / WASD | Steer the snake (2 turns are buffered per tick) |
| P or Esc | Pause / resume |
| M | Mute / unmute (or click the speaker icon) |
| T | Cycle theme (menu, game, pause) |
| F | Toggle the Nokia phone frame (Nokia theme) |
| Menu: Up/Down or mouse | Select an item |
| Menu: Left/Right, Enter, click | Change a value / activate (right-click = previous value) |
| Enter | Confirm name entry on the game-over screen |

## Modes and difficulty

- Classic: walls are deadly.
- Wrap-around: the snake passes through walls.
- Obstacles: random wall blocks (walls are deadly too). Blocks never split the board.

Food gives 10 points; bonus food (about every 7 foods) gives 50 points and vanishes
after 5 seconds. Speed rises every 5 foods. Tune everything in `settings.py`.

## Files

`main.py` loop and states, `settings.py` constants, `snake.py` snake logic,
`food.py` food and bonus, `themes.py` theme rendering, `ui.py` menus/HUD/overlays,
`sounds.py` generated sounds, `highscore.json` top 5 (auto-created).

## Play in the browser (pygbag)

The game loop is async, so the same code runs on desktop and in the browser.

```bash
pip install pygbag
cd ..                         # the folder ABOVE snake_game
python -m pygbag snake_game   # test at http://localhost:8000
python -m pygbag --build snake_game   # creates snake_game/build/web
```

Upload the contents of `build/web` to itch.io (HTML project) or GitHub Pages.
In the browser, high scores are stored in localStorage and the Quit item is hidden.
