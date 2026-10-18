# Shift Work

A 2D **dimension-swapping puzzle-platformer** built in Python + Pygame for the GDG On Campus VIT Vellore Tech Wildcard Game Development competition.

You play a night-shift custodian caught between two dimensions at once. Press **SPACE** to instantly swap between *Corporate Reality* (muted blue-grey office) and *Surreal Chaos* (dreamlike purple realm). Each world features unique obstacles, platforms, hazards, and shared objects — you must manipulate both realities in sync to clear each shift.

---

## Engine / Framework

- **Language:** Python 3 (tested with Python 3.13)
- **Library:** [Pygame](https://www.pygame.org/) 2.6+ (no external dependencies)
- **Graphics:** High-resolution transparent PNG sprites (self-made in Figma, exported via Pygame sprite generation tool at exact collision boundaries) with procedural vector shape fallbacks.

---

## How to Run

```bash
pip install -r requirements.txt
python main.py
```

> **Windows note:** If you have multiple Python versions installed, run `py -3.13 main.py`.
> To run the automated headless verification suite: `py -3.13 test_levels.py`.

---

## Controls

| Key | Action |
|---|---|
| Left / A | Move left |
| Right / D | Move right |
| Up / W | Jump (when grounded on a solid surface) |
| SPACE | Swap dimension (0.3s cooldown; blocked if solid would overlap) |
| R | Restart current level during play; restart game on Game Over / Win screen |
| Any key | Dismiss title screen / level intro card |

---

## The 5 Levels

The game features 5 hand-crafted levels, each introducing or mastering a distinct mechanic:

| # | Name | Core Concept | Solution Strategy |
|---|------|--------------|-------------------|
| **1** | **Walls Aren't Real** | Swapping in both directions | Walk right to the Reality wall; swap to Chaos to walk past it; swap back to Reality before the Chaos floor spikes; enter the exit door. |
| **2** | **Stairway Between Worlds** | Mid-air swaps & ghost platforms | Platforms alternate between Reality and Chaos. Jump from one platform and press SPACE in mid-air to land on the next using ghost outlines as guides. |
| **3** | **Push It** | Shared object manipulation | Cabinet (Reality) and stone pillar (Chaos) share one position. The wall blocks the cabinet in Reality, but in Chaos the pillar can be pushed all the way across to form a staircase up to the high ledge. |
| **4** | **Hold the Door** | Pressure plate & security gate | Park the shared object on the floor pressure plate to permanently hold the gate open. Swap between dimensions to bypass patrolling Chaos pests and jump through the open gate. |
| **5** | **Overtime** (Finale) | All mechanics combined | Push the cabinet to the wall; swap to Chaos and push past with pest timing; swap back to Reality to push the anchor to the staircase position; climb the pillar to the Chaos platform; jump and swap mid-air to the Reality goal ledge. |

---

## Core Engine Mechanics

### 1. Dimension-Tagged Platform System (E1)
Every platform in a level is tagged as `BOTH`, `REAL`, or `CHAOS`. Immovable solids are resolved dynamically based on current dimension:
```python
BOTH, REAL, CHAOS = "both", "reality", "chaos"
```
The floor is simply a platform tagged `BOTH`, allowing arbitrary platform layouts, ledges, and vertical partitions.

### 2. Ghost Outlines (E5)
Objects and hazards that exist only in the *other* dimension are rendered as faint, translucent outlines (~30% opacity). This provides essential visual telegraphing for mid-air jumps and spatial alignment.

### 3. Hazard Spikes (E3)
Spike strips are dimension-specific hazards. When the player steps into an active spike in that world, a life is lost. In the alternate dimension, spikes are harmless and appear as faint ghost outlines.

### 4. Pressure Plate & Security Gate (E4)
- **Pressure Plate:** Sits on the floor and activates when either the player stands on it (in the plate's dimension) or the shared pushable object is parked on it. Because the cabinet and pillar are the same physical object, parking the anchor holds the plate down in *both* worlds.
- **Security Gate:** Heavy solid barrier blocking both dimensions while closed. When the plate is held down, the gate opens and permits free passage.

### 5. Shared Anchor Object (E2)
In Corporate Reality, the anchor is a 50 px filing cabinet; in Surreal Chaos, it is a 100 px stone pillar. Levels can define custom cabinet/pillar heights or set `anchor: None` for pure platforming levels.

### 6. Level Intro Cards & Safe HUD (E6)
Each level begins with a centered frosted-glass card displaying the level number, name, and tactical hint. The card fades out after 2.5 seconds or immediately upon any key press. All level elements avoid the HUD panel safe zone (`x < 215, y < 180`).

### 7. Fall Safety & Dynamic Restarts (E7, E8)
- Falling below the screen immediately triggers a hazard hit and respawn to prevent softlocks.
- Pressing **R** during gameplay restarts the current level (resetting player and object positions while preserving score and lives). On Game Over or Win screens, **R** restarts the entire shift.

---

## Visual Polish & Aesthetics

- **Pre-baked vertical gradient backgrounds:** Deep corporate navy/grey in Reality, cosmic violet/magenta in Chaos.
- **World-specific decor:** Fluorescent strip lights, office desks, monitors, and motivational posters in Reality; twinkling stars, floating energy halos, rotating arcane triangles, and ground mist in Chaos.
- **Swap feedback:** 8-frame white screen flash, dynamic screen shake, and 22 burst particles matching world colors.
- **Detailed procedural sprites:** Uniformed custodian with animated eyes/cap, multi-legged bobbing pests with glowing eyes, beveled steel gates with indicator status LEDs, and glowing exit doors.
- **High score persistence:** Best score saved automatically to `highscore.txt`.

---

## Automated Verification

The repository includes a comprehensive headless test runner (`test_levels.py`) that tests all 5 levels and engine mechanics without requiring a display server:
```bash
py -3.13 test_levels.py
```
Verified checks:
- All 5 levels load in order and are solvable using intended mechanics.
- Shortcuts (e.g. jumping over 140px walls, clearing 220px spike strips, leaping over the 150px gate) fail physics limits.
- Gate remains locked until plate is pressed by anchor/player.
- Spikes and pests deal damage strictly in their designated dimensions.
- Level restart (`R`) and fall safety (`E7`) work as expected.

---

## Credits

- **Game Design & Code:** GDG On Campus VIT Vellore Tech Wildcard Entry.
- **Assets & Art:** Visual assets and sprite set created by the author — **self-made in Figma** (custom 2D sprites including reality custodian, chaos custodian, mirrored movement directions, filing cabinet, stone pillar, exit door, dimensional pests, floor spikes, pressure plates, security gates, HUD icons, logo wordmark, and title art). All visual sprites strictly adapt to the predefined physics collision rectangles without altering collision geometries.
