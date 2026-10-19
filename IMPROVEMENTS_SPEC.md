# Shift Work: Improvements Spec

> Give this to the coding agent together with the current project (`Shift_Work/`).
> The game works: `test_levels.py` passes all 5 levels, and a randomized 60-run x 3,000-frame test found no crashes. These are **polish, game feel, a repo cleanup and the optional Task 2 enemy**, not a rewrite.

## Ground rules (apply to every item)

1. **Do not change** `SPEED`, `GRAVITY`, `JUMP`, `MAX_FALL`, `SWAP_COOLDOWN_MS`, the player size (28x40), or the coordinates of Levels 1-5. The levels were verified against those numbers.
2. After **every** item, run `python test_levels.py`. It must still pass. If an item changes behaviour the tests depend on (noted below), update the tests in the same change.
3. Keep the code simple, commented and beginner-readable. The developer has to explain it in an evaluation.
4. Work in the priority order below, commit after each group, and keep the game runnable at every step.
5. Explain each change in plain English when you finish it.

---

## Priority 0: Fixes (about 1 hour)

### P0.1 Title screen text overflows its panel
`draw_title`: the "SPACE: Swap between Corporate Reality and Surreal Chaos" line runs past the right edge of the instruction panel.
- Size the panel from the text: `panel_w = max(font.size(line)[0] for line in lines) + 40`, then centre it with `panel_x = (WIDTH - panel_w) // 2`.
- Keep every line inside the panel. If a line is still too long, shorten the wording, for example `SPACE: swap worlds`.
- Make sure there is a visible, blinking "Press any key to start" prompt.

### P0.2 Ghost outlines are too faint (`draw_ghost_rect`)
Right now it draws a 1 px outline at alpha 75. In Level 2 the Chaos platform is barely visible from Reality, and in Level 5 the goal ledge nearly vanishes in Chaos. These outlines are the only hint for the mid-air swaps, so they must be readable.
- Draw a **dashed** outline, 2 px thick, alpha about 130-170, with a slow pulse (alpha oscillating about +/-30 using `sin(tick * 0.08)`). This needs `tick` passed in, so update the call sites.
- Add a very faint fill (alpha about 20-30) in the same colour so thin platforms read as shapes.
- Keep colours per world: cool blue for Reality objects seen from Chaos, violet for Chaos objects seen from Reality. They must contrast with the background of the world they are drawn in.
- Apply the same style to ghost spikes and the ghost plate.
- **Drawing only.** No collision change.

### P0.3 Chaos background decoration looks like ghost outlines (`_draw_chaos_decor`)
The thin floating outline triangles are visually the same as ghost outlines and confuse the player (for example the faint box in Level 5).
- Remove outline-only shapes from the background decoration. Use **filled, low-alpha (<= 40)** shapes, or no outline at all, so only real ghost objects look like outlines.
- Check Levels 2 and 5 in Chaos afterwards; the only outline-style objects visible should be real ghosts.

### P0.4 Spawn point hidden behind decoration (`_draw_reality_decor` / `_draw_desk`)
At the Level 2 spawn (60, 400) the player stands in front of a desk and is hard to see.
- Do not draw desks or monitors inside any level's gameplay space: nothing within about 80 px of the spawn, the door, or any platform/wall/gate/plate rect.
- Simplest approach: pass the current level in and skip any decoration whose rect (inflated by 30 px) overlaps a level rect or the spawn.

### P0.5 Repo hygiene
- `assets/` and `public/assets/` are duplicates. Keep **`assets/`** (what `main.py` loads) and delete `public/`.
- `tools/generate_assets.py` writes to the wrong folder (that is how `public/` appeared). Make it write to `<project root>/assets` and print the path it used. Remove the reference to a non-existent `requirements-assets.txt` from its docstring.
- Add `.gitignore` with: `__pycache__/`, `*.pyc`, `highscore.txt`, `.venv/`. Run `git rm --cached highscore.txt` so it stops being tracked.
- `HIGH_SCORE_FILE = "highscore.txt"` is relative to the working directory, so running from another folder writes the file elsewhere. Use `Path(__file__).resolve().parent / "highscore.txt"`.
- Keep `test_levels.py` in the repo and mention it in the README.

### P0.6 README accuracy
- Replace "self-made in Figma" with accurate wording, for example: "Sprites were designed in Figma and exported with a Pygame generator script (`tools/generate_assets.py`); the in-game rendering code and levels are my own."
- Add the author's name and the demo video link (leave a clearly marked placeholder `[ADD LINK]` if the video does not exist yet).
- Add a short "Limitations and future work" section.
- Update the controls table when P1 adds ESC/pause and mute.

---

## Priority 1: Game feel (1-2 hours)

### P1.1 Jump forgiveness
- **Coyote time:** `COYOTE_FRAMES = 6`. Keep a counter that is set to `COYOTE_FRAMES` while `on_ground` and counts down otherwise. A jump is allowed while the counter is greater than 0, and jumping consumes it (sets it to 0).
- **Jump buffer:** `JUMP_BUFFER_FRAMES = 6`. When the jump key is pressed, set a buffer counter. In `update`, if the buffer is above 0 and a jump is allowed, jump and clear the buffer.
- **Variable jump height:** on key release of UP/W while rising, cut the speed: `if vy < -4: vy = -4`. **A fully held jump must stay identical** (126 px max rise), so the levels remain solvable.
- Level shortcuts must still fail: the 140 px wall, the 150 px gate and the 220 px spike strip. Add tests for these if they are not covered.
- `test_levels.py` sets `g["vy"] = JUMP` directly in places, which still works. Run it to confirm.

### P1.2 Hit feedback and invulnerability
- On `_player_hit`: red screen flash (about 6 frames), the existing screen shake, and a short hit particle burst.
- After respawn: **60 frames of invulnerability**. Ignore pest and spike hits during this time (falling off the screen still counts), and blink the player sprite (visible every other 4 frames).
- Add `g["invuln"]` and reset it in `new_game`. This prevents being chain-killed on respawn next to a pest.

### P1.3 Sound (no external files needed)
- `pygame.mixer` may be unavailable, so initialize it in `try/except` and keep the game silent if it fails.
- Generate short effects in code with the standard `array` module plus `pygame.mixer.Sound(buffer=...)` (sine or square tones with a quick fade-out). No downloaded assets, so no licensing issues. Effects: `swap` (rising blip), `jump` (short blip), `blocked` (low buzz when a swap is refused), `hit` (descending tone), `plate` (click when the plate is pressed or released), `win` (small arpeggio).
- Keep volume around 0.3. Add an `M` key to mute and show "M: mute" in the controls text.

### P1.4 Pause, quit and window
- **ESC** toggles a pause overlay (`state = "pause"`) with "Paused: ESC to resume, R to restart level, Q to quit". On the title screen, ESC quits. Also handle window close cleanly.
- Use `pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)` so the game scales up on large monitors. Nothing else should change (no mouse input).
- While paused, do not advance the score, timers, pests or particles.

---

## Priority 2: Design issues (1 hour)

### P2.1 Scoring should not reward stalling
Score currently grows with time (`score += dt / 1000 * 10`), so slow play scores more. Replace it:
- Remove the per-frame time score.
- On reaching the door: `score += 500 + time_bonus`, with `time_bonus = max(0, 60 - seconds_on_level) * 10` (0-600).
- On each death: `score = max(0, score - 100)`.
- Track `seconds_on_level` in the game state (frames / 60 or real elapsed time), and do not count the intro card, pause, or game-over time.
- Show the level time on the HUD if there is room (inside the existing HUD panel; nothing in the gameplay area).

### P2.2 Game over should not send the player back to Level 1
- Store `level_start_score` when a level begins.
- On game over, show "R: retry this level   N: new game". **R** restarts the **current level** with 3 lives and the score at `level_start_score`. **N** restarts the whole game.
- The win screen: R restarts the whole game.
- Update the README controls table.

### P2.3 The intro card should pause play
Currently the player can move and die while the intro card is showing.
- While `intro_timer > 0`, skip physics, pests and scoring in `update`. Only count the card down (or wait for a key press).
- **`test_levels.py` does not clear `intro_timer`, so it will break.** Set `g["intro_timer"] = 0` in the test's level-loading helper and wherever it creates a game.

---

## Priority 3: Task 2, the enemy AI (optional, about 1.5 hours)

The brief's optional Task 2 requires an enemy that: patrols between two or more points; detects the player within a range; chases when detected; returns to patrol when the player leaves the range; and shows visible feedback distinguishing the states. The current pests only walk back and forth. **Leave the existing pests and Levels 1-5 exactly as they are** and add a separate enemy type, the **Warden**, used in a new **Level 6**.

### Warden behaviour (a small state machine)
Create a small `Warden` class or a dict-based helper with clear, commented states:

| State | Behaviour | Transition |
|---|---|---|
| `PATROL` | Walk between `patrol_min` and `patrol_max` at `patrol_speed` (2 px/frame), turning at each end | Player is in **Chaos** and within `DETECT_RANGE` -> `CHASE` |
| `CHASE` | Move toward the player's x at `chase_speed` (3 px/frame, always slower than the player's 5), clamped to a leash range `[leash_min, leash_max]` | Player left range (distance > `DETECT_RANGE + 40`, hysteresis) **or the player swapped to Reality** -> `RETURN` |
| `RETURN` | Walk back to the nearest patrol point at `patrol_speed` | Reached it -> `PATROL`. If the player is detected again -> `CHASE` |

- **Detection:** horizontal distance `<= 170` px **and** vertical difference `< 60` px, and only while `g["dim"] == CHAOS`. In Reality the Warden is blind and harmless, consistent with the pests.
- **Contact:** touching the player's rect in Chaos calls `_player_hit`, same as pests.
- **Visible feedback (required by the brief):**
  - Patrol: orange body (tint the pest sprite, or draw with orange shapes).
  - Chase: red body with glowing eyes, plus a "!" above its head for about 30 frames when it first spots the player.
  - Return: dimmer/greyed body.
  - Optional: a faint detection-range circle or bar under it while in Chaos.
- It walks on the floor (`GROUND_Y`), so size it like a pest (30 x 24), or slightly larger (36 x 28) and keep collision rects consistent with what is drawn.
- Use `g["warden"]` list/dicts reset in `new_game` and `_player_hit` like the pests. Frame update lives next to the pest update.

### Level 6: "Night Watch" (suggested layout)

```python
{
  "name": "Night Watch",
  "hint": "The Warden only sees you in Chaos. Reality is your hiding place.",
  "spawn": (60, 400),
  "platforms": [ F,
      (pygame.Rect(300, 300, 30, 140), REAL),        # Reality-only partition, so Chaos is required to pass
  ],
  "anchor": None,
  "pests": [],
  "wardens": [ {"patrol_min": 420, "patrol_max": 560, "leash_min": 340, "leash_max": 600} ],
  "spikes": [],
  "door": pygame.Rect(720, 390, 30, 50),
}
```
**Intended solution:** wait in Reality at the wall while the Warden patrols to its far end (right side), swap to Chaos, walk past the wall (about 18 frames before swapping back is allowed), and swap back to Reality before it closes in. The Warden notices you, chases, then loses you when you swap back and returns to patrol. Then walk to the door.
**This layout is a suggestion and has not been verified.** Before keeping it, add a headless test that:
1. proves a solution exists (a scripted route that waits for the Warden to be at the far end);
2. proves the state transitions `PATROL -> CHASE -> RETURN -> PATROL` happen, including that the Warden returns to patrol after the player swaps to Reality;
3. proves the Warden cannot hit the player in Reality.
Tune `patrol_min/max`, `DETECT_RANGE` and `chase_speed` until the route works with a comfortable timing window. Do not change the player's physics to make it work.

### Task 2 deliverables
- Add Level 6 to `LEVELS` and update "Level N / 6" text, the win condition, and `test_levels.py` (it currently assumes 5 levels).
- README: add the Warden state machine table and the controls note.
- The demo video must show the Warden patrolling, spotting the player (the "!" and colour change), chasing, and returning to patrol.

---

## Acceptance checklist

- [ ] `python test_levels.py` passes, now covering Levels 1-6 and the new mechanics.
- [ ] Title panel text fits; ghost outlines are clearly visible in Levels 2 and 5; no outline-only decoration; the spawn is not hidden.
- [ ] `public/` removed, `.gitignore` added, `highscore.txt` untracked, the asset generator writes to `assets/`.
- [ ] Coyote time, jump buffering and variable jump work, and a held jump still reaches 126 px max.
- [ ] Death shows feedback, respawn gives 1 s of invulnerability, and sound works (or the game stays silent without crashing if audio fails). M mutes.
- [ ] ESC pauses; the window scales; closing the window works.
- [ ] Scoring no longer rewards stalling; game over retries the current level; the intro card pauses play.
- [ ] Warden: patrol, detect, chase and return all work, with visible state feedback, and Level 6 is solvable.
- [ ] README is accurate (assets wording, author, video link, controls, Warden).
- [ ] No crashes when spamming swap, jump, restart and pause. Run a randomized input test (random keys, 3,000+ frames, many runs) and report the result.

---

## Prompt to give the agent

> Read `IMPROVEMENTS_SPEC.md` and the current project. Work through it in priority order (P0, then P1, then P2, then P3 only if time allows). Never change the physics constants or the Level 1-5 coordinates. After each item run `python test_levels.py` and fix anything that breaks (update the tests where the spec says to). Keep the code simple and commented, commit after each group, and explain each change in plain English so I can explain it in my evaluation. At the end, run a randomized input fuzz test and report the results honestly, including anything you could not verify.
