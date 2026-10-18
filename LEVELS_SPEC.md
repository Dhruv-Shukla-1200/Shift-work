# Shift Work: Level Design Spec (5 levels)

> Give this file to the coding agent together with the current `main.py`.
> Goal: replace the current 2 near-identical levels with 5 distinct levels, each built around ONE idea, plus the small engine additions those levels need.
> **Do not change** `SPEED`, `GRAVITY`, `JUMP`, `MAX_FALL`, the 300 ms swap cooldown (18 frames at 60 FPS), or the player size (28x40). Every level below was designed against those exact numbers.

---

## 1. Why the old levels felt the same

Both old levels were "walk right, swap once, push the pillar, jump to a ledge", with different coordinates. The level data format only allows **one wall, one ledge, one anchor and one pest band**, so every level is forced into the same shape. A level feels different when the player has to *think* differently, so each level below teaches or combines a distinct idea:

| # | Name | Core idea |
|---|------|-----------|
| 1 | Walls Aren't Real | Swap to pass a wall, swap back to avoid a hazard (both directions) |
| 2 | Stairway Between Worlds | Vertical climb on platforms that alternate worlds, so you swap **mid-air** |
| 3 | Push It | The shared object: push the pillar in Chaos, use it as a staircase |
| 4 | Hold the Door | Pressure plate + gate: park the shared object on the plate to hold the door open |
| 5 | Overtime | Finale: wall crossing, pests, pushing, pillar staircase and a mid-air swap in one run |

---

## 2. Measured physics limits (design constraints)

Measured from the real jump code (`vy=-12`, gravity 0.6, `ceil/floor` stepping, 5 px/frame):

- Air time on flat ground: **40 frames**. Max rise: **126 px**. Max flat horizontal reach: **200 px**.
- Platform **80 px up**: about 23 frames above it, so roughly a **115 px** horizontal gap is crossable.
- Platform **100 px up**: about 17 frames above it, so roughly **85 px** gap.
- Swap cooldown: 300 ms, which is **18 frames** at 60 FPS.
- **Rules used for every level:** a single jump never needs more than 100 px of rise (comfort), nothing "required" is more than 126 px, and impossible shortcuts are deliberately 130 px or more.
- **HUD safe zone:** the HUD panel covers about x 6-211, y 6-158 (plus a message line at y 162). Do not place platforms, doors or hazards in x < 215, y < 180.
- Canvas stays **800 x 500** and the floor stays at `GROUND_Y = 440`. No camera needed.

---

## 3. Engine changes required

Keep the code simple and commented. Collision logic must stay rectangle-based. Items marked **(needed)** are required by the levels; **(nice)** can wait.

### E1 (needed): New level schema with world-tagged platforms

Replace the single `wall` / `ledge` / implicit floor with a list of platforms. Each platform is `(Rect, world)` where `world` is `BOTH`, `REAL` or `CHAOS`.

```python
BOTH, REAL, CHAOS = "both", "reality", "chaos"   # platform/hazard world tags
# dim values stay REALITY=0 / CHAOS=1; a tag is active in dim d when:
#   tag == BOTH, or (tag == REAL and d == REALITY), or (tag == CHAOS and d == CHAOS)

LEVEL = {
    "name":      "Walls Aren't Real",
    "hint":      "text shown on the intro card",
    "spawn":     (60, 400),
    "platforms": [ (pygame.Rect(0,440,800,60), BOTH), ... ],   # the floor is now just a platform
    "anchor":    {"x": 200, "cab_h": 50, "pil_h": 100} or None, # None = no pushable object
    "pests":     [ {"min": 250, "max": 370, "speed": 2, "count": 2} ],   # list of zones; [] for none
    "spikes":    [ (pygame.Rect(...), CHAOS) ],                 # optional
    "gate":      pygame.Rect(...)  or None,                     # optional (Level 4)
    "plate":     {"rect": pygame.Rect(...), "world": CHAOS} or None,   # optional (Level 4)
    "door":      pygame.Rect(...),
}
```

- `static_solids(level, dim)` returns every platform whose tag is active in `dim`, plus the gate if it is closed (E4).
- Everything that read `level["wall"]` / `level["ledge"]` must read the platform list instead.
- Pests keep their current behaviour (Chaos only, patrol on the floor at `GROUND_Y`, hit = lose a life). `count` pests are spread across `[min, max]` with alternating directions, exactly like the current spawn code. `min`/`max` are the pest's **left-edge** range (pest rect is 30 x 24).

### E2 (needed): Anchor can be `None`
Level 1 and 2 have no pushable object. `all_solids`, `move_x`, `draw`, and respawn must all skip the anchor when `level["anchor"] is None`. Cabinet height = `cab_h` (Reality), pillar height = `pil_h` (Chaos); width stays 40.

### E3 (needed): Spikes
A spike is a hazard rect tagged with a world. When `dim` matches the tag and the player rect overlaps it, call the existing `_player_hit(g)`. Draw as a row of triangles. Spikes do **not** block movement.

### E4 (needed): Pressure plate and gate (Level 4)
- `plate["rect"]` is a thin rect on the floor. `plate["world"]` is the world it is drawn "solid" in.
- **Pressed** each frame if either:
  1. `anchor_rect(level, plate_world, anchor_x)` overlaps the plate rect (the anchor holds it in **either** world, because it is the same object), or
  2. `g["dim"] == plate_world` and the player rect overlaps the plate rect.
- `gate` is a solid rect in **both** worlds while the plate is **not** pressed. When pressed it is not solid and is drawn open (faded or lowered).
- The swap-refusal check must include the closed gate (it is part of `all_solids`).
- Edge case: if the gate closes on top of the player, nudge the player out or count a hit. In Level 4 this should not happen, because the gate is far from the plate.

### E5 (needed): Ghost outlines for the *other* world
Anything tagged to only one world is invisible in the other, which makes Level 2 impossible to read. In each world, draw the other world's platforms, walls, spikes and plate as a **faint outline** (about 25-35% alpha, 1-2 px line, no fill). The player must be able to see where the next platform will be. Solid-in-this-world objects keep their normal full drawing.

### E6 (needed): Level intro card
When a level loads, show a centred card for about 2.5 seconds (or until the first key press): `Level N: <name>` and the `hint` line underneath. Gameplay may start immediately or after the card, but the card must not block input permanently.

### E7 (needed): Fall safety
Add `if g["player"].top > HEIGHT: _player_hit(g)` in `update`. No current level has a pit, but this prevents softlocks if one is added later.

### E8 (nice)
- `R` restarts the **current level** (keep score and lives reset rules as you see fit); a separate key or the title screen restarts the whole game.
- Per-level background tint or props (reception, library stacks, storage, server room, executive floor). Visual only.

---

## 4. Level data (exact coordinates)

All rects are `pygame.Rect(x, y, w, h)`. `F = (pygame.Rect(0, 440, 800, 60), BOTH)` is the floor in every level.

### Level 1: Walls Aren't Real

```python
{
  "name": "Walls Aren't Real",
  "hint": "Some walls exist in only one world. Some floors hurt in the other.",
  "spawn": (60, 400),
  "platforms": [ F,
      (pygame.Rect(300, 300, 30, 140), REAL),       # office partition, Reality only
  ],
  "anchor": None,
  "pests": [],
  "spikes": [ (pygame.Rect(420, 424, 220, 16), CHAOS) ],   # floor spikes, Chaos only
  "door": pygame.Rect(720, 390, 30, 50),
}
```

**Idea:** the first level teaches that swapping solves the problem in *both directions*.
**Solution:**
1. Walk right until blocked by the wall (it is 140 px tall; max jump is 126).
2. SPACE to Chaos. The wall is gone. Walk right past it.
3. The Chaos spikes start at x = 420 and are 220 px wide (too wide to jump over). Before reaching them, SPACE back to Reality. The spikes are harmless there.
4. Walk to the door.

**Comfort window:** after swapping to Chaos the player must walk about 18 frames (cooldown) before swapping back, which puts them at roughly x = 360-390, safely before the spikes at 420.
**Verified shortcuts that fail:** jumping over the wall, and jumping the spikes while staying in Chaos.

### Level 2: Stairway Between Worlds

```python
{
  "name": "Stairway Between Worlds",
  "hint": "Jump, then press SPACE in mid-air. Faint outlines show the other world.",
  "spawn": (60, 400),
  "platforms": [ F,
      (pygame.Rect(140, 350, 100, 16), REAL),       # P1  top y=350
      (pygame.Rect(290, 270, 100, 16), CHAOS),      # P2  top y=270
      (pygame.Rect(440, 190, 100, 16), REAL),       # P3  top y=190
      (pygame.Rect(590, 120, 210, 16), BOTH),       # P4  top y=120 (goal ledge)
  ],
  "anchor": None,
  "pests": [ {"min": 380, "max": 700, "speed": 2, "count": 1} ],  # punishes falling in Chaos
  "spikes": [],
  "door": pygame.Rect(740, 70, 30, 50),
}
```

**Idea:** platforms alternate worlds, so you cannot stand and swap (the platform under you would vanish). You must **jump first, then swap in mid-air** to land on the next platform. This is the level that makes the swap mechanic feel skillful.
**Solution:** floor to P1 (Reality). From P1 jump toward P2, swap to Chaos in the air, land on P2. From P2 jump toward P3, swap to Reality in the air, land on P3. From P3 jump to P4 (exists in both). Walk to the door.
**Notes:**
- Each step is 80 px of rise with a 50 px horizontal gap, within the comfortable limits.
- Falling is safe in Reality; falling in Chaos near x = 380-700 meets a pest, so players learn to swap while falling.
- Ghost outlines (E5) are **required** here; without them the player cannot see P2 while in Reality.
**Verified:** every stage is solvable with many timing combinations (thousands of working input combos per stage), and P1 to P2 and P1 to P3 are impossible without swapping.

### Level 3: Push It

```python
{
  "name": "Push It",
  "hint": "The cabinet and the pillar are the same object. Move one, move both.",
  "spawn": (60, 400),
  "platforms": [ F,
      (pygame.Rect(380, 300, 30, 140), REAL),       # Reality-only partition
      (pygame.Rect(650, 300, 150, 20), BOTH),       # high ledge, top y=300
  ],
  "anchor": {"x": 200, "cab_h": 50, "pil_h": 100},
  "pests": [],
  "spikes": [],
  "door": pygame.Rect(740, 250, 30, 50),
}
```

**Idea:** the signature twist. The cabinet (50 px) cannot be pushed past the wall in Reality (it stops at anchor x = 340), but in Chaos the wall does not exist, so the pillar can be pushed all the way across.
**Solution:**
1. SPACE to Chaos at the start, then push the pillar right until its x is about 600 (it sits just left of the ledge).
2. Stand at its left side and jump **straight up**, then move right once above its top (y = 340) so you land on it. (Pressing right while still beside it pushes it further.)
3. From the pillar top, jump right onto the ledge (rise 40 px).
4. Walk to the door.
**Notes:** pushing the pillar far under the ledge can trap it, and pressing R fixes it. Keep that behaviour.
**Verified:** solved headlessly.

### Level 4: Hold the Door

```python
{
  "name": "Hold the Door",
  "hint": "The gate stays open while something sits on the plate. Pests ignore you in Reality.",
  "spawn": (60, 400),
  "platforms": [ F,
      (pygame.Rect(220, 300, 30, 140), REAL),       # Reality-only partition
  ],
  "anchor": {"x": 120, "cab_h": 50, "pil_h": 100},
  "pests": [ {"min": 250, "max": 370, "speed": 2, "count": 2} ],
  "spikes": [],
  "gate":  pygame.Rect(560, 290, 20, 150),          # solid in both worlds while closed (150 px, cannot be jumped)
  "plate": {"rect": pygame.Rect(300, 436, 60, 4), "world": CHAOS},
  "door":  pygame.Rect(720, 390, 30, 50),
}
```

**Idea:** parking the shared object on the plate holds the gate open, so the player can walk away from it (standing on the plate would pin them in place).
**Solution:**
1. In Reality, push the cabinet right until the wall stops it (anchor x = 180).
2. SPACE to Chaos and keep pushing the pillar past the wall until the plate is pressed (anchor x > 260) **and** the player's left edge is at x >= 250 (clear of the wall column), then wait out the 300 ms cooldown.
3. Pests patrol the plate area in Chaos (left edge 250 to 370). Time the push, or swap to Reality to let a pest walk through you (pests are harmless in Reality), then swap back.
4. SPACE back to Reality, jump over the cabinet (it still holds the plate down, since it is the same anchor) and walk through the open gate to the door.
**Why Reality pushing cannot skip the puzzle:** the cabinet cannot get past the wall, so the plate can only be reached with the pillar in Chaos.
**Tuning (measured):** with 2 pests over 250-370 at speed 2, roughly **55%** of waiting times before the Chaos push succeed with a rigid bot, so a human who adapts has comfortable room. Do **not** widen the pest range toward the wall (230-330 with 2 pests dropped to about 4%, which is unfair). To make it easier, raise `min` or lower `count`.
**Verified:** the full route works (push, plate, gate, door) and the gate cannot be jumped.

### Level 5: Overtime (finale)

```python
{
  "name": "Overtime",
  "hint": "Everything you've learned. The pillar is your staircase.",
  "spawn": (60, 400),
  "platforms": [ F,
      (pygame.Rect(260, 300, 30, 140), REAL),       # Reality-only partition
      (pygame.Rect(560, 260, 120, 16), CHAOS),      # CP  top y=260 (Chaos only)
      (pygame.Rect(710, 180, 90, 16),  REAL),       # RP  top y=180 (Reality only, holds the door)
  ],
  "anchor": {"x": 120, "cab_h": 50, "pil_h": 100},
  "pests": [ {"min": 300, "max": 420, "speed": 2, "count": 2} ],
  "spikes": [],
  "door": pygame.Rect(750, 130, 30, 50),            # sits on RP (RP top = 180 = door bottom)
}
```

**Idea:** a recap of everything, in the order you learned it.
**Solution:**
1. Push the cabinet right in Reality until the wall stops it (anchor x = 220).
2. SPACE to Chaos and push the pillar past the wall. Pests patrol x = 300-420, so time the crossing, then SPACE back to Reality once your left edge is past x = 290 (wall column clear).
3. Keep pushing in Reality (pests are harmless there) until the anchor is at about x = 520, just left of the Chaos platform CP.
4. SPACE to Chaos, jump **straight up**, move right to land on the pillar (top y = 340).
5. From the pillar, jump straight up beside CP's left edge until above y = 260, then move right to land on CP. (CP is a slab; moving right too early bumps your head under it.)
6. From CP, jump right and SPACE in mid-air to Reality, landing on RP (Reality only).
7. Walk into the door.
**Why there is no shortcut:** CP is 180 px above the floor (impossible to jump), and using the cabinet as a stool needs 130 px of rise (limit is 126). RP is only reachable via CP.
**Verified:** the full route works. The wall crossing against 2 pests succeeds for about **66%** of waiting times (99 of 150), and each climb stage has thousands of working input combinations.

---

## 5. Honest verification statement

These levels were checked with a **headless replica of the game's physics** (same constants, same rect collision order, same push rule, same 18-frame swap cooldown), extended with the new features above. Scripted or brute-forced input sequences solved every level and confirmed the intended shortcuts fail. **This replica is not your `main.py`.** After implementing, the agent must still run each level in the real game, because small differences (for example timing from `clock.tick` and `now_ms`) can shift windows slightly. If a level feels unfair, change **pest `min`/`count`/`speed` first**, then the platform gaps by at most 10-20 px. Never change the physics constants to fix a level.

---

## 6. Acceptance checklist

- [ ] All five levels load in order, with an intro card and the correct `Level N / 5` HUD text.
- [ ] Level 1 cannot be finished without swapping both ways (jumping the wall and jumping the spikes both fail).
- [ ] Level 2 cannot be finished without mid-air swaps, and the other world's platforms show as faint outlines.
- [ ] Level 3 still works exactly as the original Level 1 did (push the pillar in Chaos, climb, ledge, door).
- [ ] Level 4: the gate opens when the anchor sits on the plate, stays open when the player walks away, and closes again if the anchor is pushed off.
- [ ] Level 5 is completable using only the route in Section 4.
- [ ] Spikes hurt only in their world; pests hurt only in Chaos.
- [ ] Nothing is placed in the HUD safe zone (x < 215, y < 180).
- [ ] Death, respawn, win, restart and the high score still work, and nothing crashes when spamming swap or restart.
- [ ] The README is updated with the 5 levels and the new mechanics (plate, gate, spikes, ghost outlines).

---

## 7. Prompt to give the agent

> Read `LEVELS_SPEC.md` and the current `main.py`. Implement the engine changes in Section 3 (E1-E7 first), then add the 5 levels from Section 4 using the exact coordinates given. Do not change SPEED, GRAVITY, JUMP, MAX_FALL, the swap cooldown or the player size. Keep collision rect-based and the code simple and commented. Keep the game runnable after each step, and explain each change in plain English so I can explain it in my evaluation. When finished, play each level yourself in a headless test where possible and report anything that is unsolvable or feels unfair, rather than changing physics values.
