# Shift Work

A 2D **dimension-swapping action-platformer** built in Python + Pygame for the GDG On Campus VIT Vellore Tech Wildcard Game Development competition.

You play a night-shift custodian who exists in two dimensions at once. Press **SPACE** to instantly swap between *Corporate Reality* (muted blue-grey office) and *Surreal Chaos* (dreamlike purple). Each world has different obstacles and hazards — you must use both to solve each level.

---

## Engine / Framework

- **Language:** Python 3
- **Library:** [Pygame](https://www.pygame.org/) (no other game libraries)
- All graphics are drawn with `pygame.draw.rect` — no external assets needed.

---

## How to Run

```bash
pip install -r requirements.txt
python main.py
```

> **Windows note:** If you have multiple Python versions, use `py -3.13 main.py`.

---

## Controls

| Key | Action |
|---|---|
| Left / A | Move left |
| Right / D | Move right |
| Up / W | Jump (only when grounded) |
| SPACE | Swap dimension |
| R | Restart at any time |

---

## Implemented Features (Task 1 mapping)

| Task 1 Requirement | Feature in Shift Work |
|---|---|
| Keyboard-controlled player | WASD / Arrow keys + jump |
| Obstacle / hazard | Reality wall (blocks movement) + Chaos pests (deadly) |
| Scoring system | +10 pts/sec while alive; +1000 on exit |
| Game-over condition | Lose all 3 lives → GAME OVER screen |
| Restart option | Press R at any time |
| Score on screen | Live HUD: Score, Level, Lives, Best |

**Additional features (P1):**
- 2-level progression (data-driven LEVELS list, easily extensible)
- 3 lives with respawn at the start of the current level
- Swap cooldown (0.3 s) prevents spamming
- White screen flash (8 frames) gives immediate swap feedback
- High score persisted to `highscore.txt` across sessions

---

## How the Dimension Swap Works

A single integer variable `dim` (0 = Reality, 1 = Chaos) controls everything. `static_solids(level, dim)` returns a different list of solid rectangles depending on `dim` — the Reality wall only appears when `dim == REALITY`. The background colour, object colours, and which sprites are drawn all use `dim` as an index into colour palette tuples. Swapping is instant (one frame) but guarded by a 0.3 s cooldown and a collision check that prevents swapping into a solid.

---

## How the Anchor / Pushing Twist Works

The filing cabinet (Reality) and stone pillar (Chaos) share one `anchor_x` float. `anchor_rect(level, dim, anchor_x)` builds the correct rectangle for the current dimension from that single x value. When the player walks into the object, `move_x` tries to shift `anchor_x` by the player's movement speed. If the destination is clear of static solids and within screen bounds, `anchor_x` is updated — both objects move together. If blocked, the player stops at the object's edge instead.

---

## Limitations / Future Work

- 2 levels only (adding more requires one new dict in the `LEVELS` list)
- No sprite art — all objects are coloured rectangles (placeholders)
- No sound effects (P4 scope)
- No parallax backgrounds
- Enemy AI (P3 state machine) not implemented

---

## Credits

- Built entirely from scratch using Python + Pygame.
- No external assets, tutorials, or art used.
- Pygame community: https://www.pygame.org/contribute.html
