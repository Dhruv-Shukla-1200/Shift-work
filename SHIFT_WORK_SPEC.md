# Shift Work: Project Spec and Agent Brief

> Hand this file to the coding agent together with `main.py` (a working prototype already exists).
> Goal: extend and polish the prototype into a complete, submittable game for the GDG Tech Wildcard Entry (Game Development, Task 1; Task 2 optional).

---

## 1. Context

- **Competition:** GDG On Campus VIT Vellore, Tech Wildcard Entry, Game Development track.
- **Required task (Task 1):** Build a small but fully playable 2D game with a complete gameplay loop.
- **Optional task (Task 2):** An enemy with patrol, detect, chase and return-to-patrol behaviour, with visible state feedback.
- **Deadline:** Tomorrow night. Time is very limited, so **stability and a finished, explainable result matter more than scope.**
- **Developer level:** Beginner with basic Python. The developer must be able to explain every part of the code during evaluation, so code must be simple, readable and well commented.

### Hard rules from the brief

1. Keyboard-controlled player movement.
2. At least one obstacle, enemy or hazard.
3. A scoring system based on progress or actions.
4. A game-over condition and a restart option.
5. Score and relevant game info displayed on screen.
6. No crashes during normal gameplay.
7. Free assets and tutorials are allowed, but the applicant must understand and be able to explain the implementation.
8. Deliverables: GitHub repo, README.md (engine, controls, features, how to run), 1-2 minute gameplay demo video.

---

## 2. Game Concept

**Title:** Shift Work
**Genre:** Dimension-swapping action-platformer / puzzle-platformer
**Engine:** Python + Pygame (no other game libraries)

You play a night-shift custodian in a mundane corporate office that exists in two dimensions at once:

| Dimension | Look | Rules |
|---|---|---|
| **Corporate Reality** | Muted blue-grey office | Walls and partitions exist. Filing cabinets are short and pushable. Pests are harmless and invisible. |
| **Surreal Chaos** | Purple, dreamlike | Office walls vanish. The cabinet becomes a tall stone pillar. Interdimensional pests are visible and deadly. |

At the press of a button (SPACE) the entire world swaps instantly.

### The twist (core mechanic)

Objects have an **anchor** shared by both worlds. A filing cabinet in Reality and a stone pillar in Chaos share the same `x` position. **Pushing the object in one world moves its counterpart in the other.** The player must manipulate both layers to solve puzzles.

Example puzzle (already in the prototype):
1. A Reality-only wall blocks the corridor, so the player swaps to Chaos to pass it.
2. In Chaos the player pushes the pillar toward the ledge. Pests patrol the floor there, so the player swaps to Reality to dodge them.
3. The pillar becomes a stepping stone to reach a ledge the player can't jump to directly.
4. The exit door is on the ledge.

---

## 3. Current State (what already exists in `main.py`)

A working prototype (about 200 lines, one file) with:

- 800x500 window, 60 FPS, Pygame.
- Player rectangle with gravity, jump (UP/W), left/right (arrows/A/D), AABB collision resolved separately on X and Y.
- `dim` variable (0 = Reality, 1 = Chaos) chooses which solids are active and which sprites are drawn.
- `static_solids(dim)` returns the ground, ledge, and the wall (Reality only).
- `anchor_rect(dim, x)` returns the shared object (cabinet 40x50 in Reality, pillar 40x100 in Chaos).
- Pushing: moving horizontally into the anchor moves `anchor_x` by `dx` if the destination is free; otherwise the player is blocked.
- `try_swap`: refuses a swap if the player would overlap a solid in the target world (shows a message).
- Two patrolling pests, active only in Chaos. Touching one means game over.
- Score increases with time; reaching the door gives +1000 and shows "SHIFT COMPLETE!".
- Game states: `play`, `lose`, `win`. R restarts at any time.
- Headless-tested: the wall blocks in Reality, the swap works, pushing works, and the pillar-to-ledge-to-door route is reachable.

### Key constants

```
WIDTH, HEIGHT = 800, 500      GROUND_Y = 440
SPEED = 5   GRAVITY = 0.6   JUMP = -12   MAX_FALL = 15
Jump height is about 120 px. Wall is 140 px tall (cannot be jumped). Pillar is 100 px (can be jumped onto).
Ledge top y=300; pillar top y=340; door on ledge at x=740.
```

---

## 4. What the Agent Should Do (priority order)

Complete in order. **Stop after any step if time is short. Each step must leave the game runnable.**

### P0: Must have (verify, don't break)
- [ ] Run the game, confirm it matches Section 3, and fix any bugs found.
- [ ] Add clear code comments and docstrings so a beginner can explain every function.
- [ ] Create `README.md` (see Section 7).
- [ ] Add `requirements.txt` containing `pygame`.

### P1: High value, low risk
- [ ] **Level 2 / progression:** after reaching the door, load a second, slightly harder layout (data-driven level dictionaries, not hard-coded constants). Show "Level N" on screen. After the final level, show a win screen with total score.
- [ ] **Lives or checkpoints:** 3 lives, with respawn at the level start, and game over when lives reach 0. Display lives on screen.
- [ ] **Swap feedback:** a brief screen flash or fade (about 8 frames) on swap, plus a swap cooldown (about 0.3 s) to prevent spamming.
- [ ] **High score** stored in memory (and optionally in a local `highscore.txt`, wrapped in try/except).

### P2: Gameplay depth (pick 1-2 at most)
- [ ] **Healing water cooler:** in Chaos, the Reality water cooler becomes a healing fountain that restores one life when touched. Anchored at a fixed position.
- [ ] **Combat vs pests:** the custodian can swing a mop (X key) in Chaos to kill a nearby pest, with a short cooldown and a short hit-box in front of the player. +50 score per pest.
- [ ] **Coins:** collectibles that exist in only one world each (some Reality-only, some Chaos-only), so the player has to swap to collect all of them. +10 each.
- [ ] **Second pushable object** with its own anchor.

### P3: Task 2 (enemy AI), optional but valuable
Turn one pest into a **state-machine enemy**:
- States: `PATROL`, `CHASE`, (optional) `RETURN`.
- Patrol between two or more waypoints.
- If the player is within `DETECT_RANGE` (e.g. 180 px) and in the same dimension, switch to CHASE and move toward the player.
- If the player leaves range (or swaps dimension), return to PATROL.
- **Visible feedback:** colour change (green or orange for patrol, red for chase) and optionally a "!" above its head.
- Keep the logic in a small, separate `Enemy` class so it is easy to explain.

### P4: Polish (only if everything above is done)
- Simple sound effects via `pygame.mixer` (swap, jump, hit, win), wrapped in try/except so the game still runs without audio.
- Background parallax or simple decorative shapes per world (desks, monitors in Reality; floating shapes in Chaos).
- Simple animation (bobbing player, pulsing door).
- Difficulty ramp (pests get faster per level).

---

## 5. Architecture Guidance

Keep it **simple and explainable**. A single `main.py` is acceptable. If it grows, a light split is fine:

```
shift-work/
  main.py            # game loop, input, drawing
  levels.py          # level data (walls, ledges, anchors, pests, door, spawn)
  entities.py        # Player / Enemy / Anchor classes (only if needed)
  requirements.txt
  README.md
  assets/            # optional sounds/images (free licences only)
```

Design principles:
- **Separate update from draw.** `update(game_state, dt)` changes state; `draw(screen, game_state)` only renders.
- **One state dict or `Game` class** holds everything (`dim`, player, anchors, enemies, score, lives, level index, state).
- **Dimension is data.** Anything that differs between worlds should be a per-dimension lookup (solids, colours, visible sprites), not scattered `if` statements.
- **Collision:** axis-aligned rectangles (`pygame.Rect.colliderect`). Resolve X movement, then Y movement, separately.
- **No external physics or game libraries.** Plain Pygame only.
- **No crashes:** guard file I/O and audio with try/except. Clamp the player inside the screen. Never leave the player stuck inside a solid (swap refusal already handles this).

### Known edge cases to check
- Pushing the anchor into a position that overlaps a solid in the *other* world after a swap. Either prevent it or resolve it (e.g. block the swap, or nudge).
- Player standing on the pillar when it is pushed away (the player should fall, not clip).
- Pushing the pillar under the ledge (the player could get stuck). Consider limiting the push range or allowing R to restart (already works).
- `on_ground` flicker when standing on a surface (the current code uses `ceil` for positive velocity to avoid this; keep it).

---

## 6. Controls

| Key | Action |
|---|---|
| Left / A | Move left |
| Right / D | Move right |
| Up / W | Jump (only when grounded) |
| SPACE | Swap dimension |
| X (if combat added) | Mop attack |
| R | Restart |

---

## 7. Deliverables Checklist

### README.md must include
1. Project title and one-paragraph description.
2. **Engine/framework:** Python + Pygame.
3. **How to run:** `pip install -r requirements.txt`, then `python main.py`.
4. **Controls** (table above).
5. **Implemented features** (honest list, including which Task 1 requirements map to which feature).
6. **How the dimension swap works** (2-3 sentences: the `dim` variable selects the active solids and drawn sprites).
7. **How the anchor/pushing twist works.**
8. **Enemy AI explanation** if P3 is done (states and transitions).
9. **Limitations / future work** (e.g. only N levels, no sprites, rectangles used as placeholders).
10. **Credits:** any assets or tutorials used.

### Other deliverables
- Public GitHub repo with clean commits (commit after each working step).
- 1-2 minute demo video showing: movement, a dimension swap, pushing the object, dodging a pest via swap, reaching the door, a game over, and a restart. If Task 2 is done, show the enemy switching patrol to chase and back.

---

## 8. Constraints and Instructions for the Agent

1. **Do not rewrite the game from scratch.** Extend `main.py` incrementally and keep it runnable after every step.
2. **Prioritise reliability.** A smaller game that never crashes beats a bigger one with bugs.
3. **Keep the code beginner-friendly:** clear names, short functions, comments that explain *why*, and no clever tricks or heavy abstractions.
4. **Explain as you go.** After each change, give a short plain-English summary of what changed and why, so the developer can explain it in the evaluation.
5. **Test headlessly where possible** (`SDL_VIDEODRIVER=dummy`) and confirm the puzzle remains solvable after each level or layout change. Check that the player can actually jump between platforms (jump height is about 120 px, horizontal air distance about 200 px).
6. **Do not add dependencies** beyond `pygame`.
7. **Use only free or self-made assets.** Rectangles and simple shapes are acceptable; visual polish is not the grading focus (functionality and understanding are).
8. **Ask before large changes** to architecture or controls.

---

## 9. Acceptance Criteria (definition of done)

- [ ] `python main.py` launches with no errors on a clean install.
- [ ] All six Task 1 requirements are visibly satisfied.
- [ ] The dimension swap is instant and visually obvious.
- [ ] Pushing an object in one world visibly moves its counterpart in the other.
- [ ] At least one level is fully solvable and the solution requires using both worlds.
- [ ] Death, win and restart all work repeatedly without needing to relaunch.
- [ ] No crash when spamming swap, jump or restart.
- [ ] README and `requirements.txt` exist and are accurate.
- [ ] The developer can explain the game loop, collision, swap and push logic from the code and comments alone.

---

## 10. Suggested Prompt to Give the Agent

> I'm building "Shift Work", a 2D dimension-swapping platformer in Python/Pygame, for a university game-dev competition due tomorrow night. Read `SHIFT_WORK_SPEC.md` and the existing `main.py`. First run the game and confirm it works. Then implement the P0 and P1 items in order, keeping the code simple and well commented, and keep the game runnable after every step. After each step, briefly explain what you changed so I can explain it in my evaluation. Don't add dependencies besides pygame, and ask me before making big architectural changes.
