"""
Shift Work - 2D dimension-swapping platformer
==============================================
Controls:
  Arrow keys / WASD  -- move and jump
  SPACE              -- swap between Corporate Reality and Surreal Chaos
  R                  -- restart at any time

Run:
  py -3.13 main.py        (Windows with Python 3.13)
  python  main.py         (any Python 3 with pygame installed)
"""

import math
import random
import pygame

# ---------------------------------------------------------------------------
# Global constants -- screen size, physics, world IDs
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 500          # window dimensions in pixels
GROUND_Y = 440                    # y-coordinate of the ground surface

# World / dimension identifiers and tags (E1)
# BOTH, REAL, CHAOS define which dimension(s) an object exists in.
# ChaosVal is an int subclass so CHAOS works as both integer dimension 1 and tag "chaos".
BOTH  = "both"
REAL  = "reality"

class _ChaosVal(int):
    """Integer dimension 1 that also compares equal to string tag 'chaos'."""
    def __eq__(self, other):
        if other == "chaos":
            return True
        return super().__eq__(other)
    def __str__(self):
        return "chaos"
    def __repr__(self):
        return "'chaos'"

REALITY = 0
CHAOS   = _ChaosVal(1)


def is_tag_active(tag, dim):
    """Return True if an object with world tag `tag` exists in dimension `dim`."""
    if tag == BOTH:
        return True
    if (tag == REAL or tag == "reality" or tag == REALITY) and dim == REALITY:
        return True
    if (tag == CHAOS or tag == "chaos" or tag == 1) and (dim == CHAOS or dim == 1):
        return True
    return False


# Physics constants -- kept strictly unchanged
SPEED    = 5                      # horizontal pixels per frame
GRAVITY  = 0.6                    # pixels added to fall speed each frame
JUMP     = -12                    # initial upward velocity when jumping (negative = up)
MAX_FALL = 15                     # terminal (maximum) fall speed

# Swap feedback constants (P1)
SWAP_COOLDOWN_MS = 300            # milliseconds before player can swap again
FLASH_FRAMES     = 8              # how many frames the swap white-flash lasts

# Screen-shake constants (visual only)
SHAKE_FRAMES = 10                 # frames of shake after a swap
SHAKE_MAG    = 5                  # maximum pixel offset during shake

# Particle constants (visual only)
PARTICLE_COUNT = 22               # particles spawned per successful swap
PARTICLE_LIFE  = 35               # max lifetime of each particle in frames


# ---------------------------------------------------------------------------
# Level data (Section 4: exact coordinates for all 5 levels)
# ---------------------------------------------------------------------------
F = (pygame.Rect(0, 440, 800, 60), BOTH)   # standard floor in every level

LEVELS = [
    # -- Level 1: Walls Aren't Real -----------------------------------------
    # Core idea: Swap to pass a wall, swap back to avoid a hazard (both directions).
    # Solution: Walk right to wall -> SPACE to Chaos -> walk past wall ->
    #           SPACE back to Reality before spikes at 420 -> walk to door.
    {
        "name":      "Walls Aren't Real",
        "hint":      "Some walls exist in only one world. Some floors hurt in the other.",
        "spawn":     (60, 400),
        "platforms": [
            F,
            (pygame.Rect(300, 300, 30, 140), REAL),       # office partition, Reality only
        ],
        "anchor":    None,
        "pests":     [],
        "spikes":    [(pygame.Rect(420, 424, 220, 16), CHAOS)],   # floor spikes, Chaos only
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(720, 390, 30, 50),
    },
    # -- Level 2: Stairway Between Worlds -----------------------------------
    # Core idea: Vertical climb on platforms that alternate worlds; swap mid-air.
    # Solution: Floor -> P1 (Reality) -> jump towards P2 & swap mid-air to Chaos ->
    #           land on P2 -> jump towards P3 & swap mid-air to Reality ->
    #           land on P3 -> jump to P4 (Both) -> door.
    {
        "name":      "Stairway Between Worlds",
        "hint":      "Jump, then press SPACE in mid-air. Faint outlines show the other world.",
        "spawn":     (60, 400),
        "platforms": [
            F,
            (pygame.Rect(140, 350, 100, 16), REAL),       # P1  top y=350
            (pygame.Rect(290, 270, 100, 16), CHAOS),      # P2  top y=270
            (pygame.Rect(440, 190, 100, 16), REAL),       # P3  top y=190
            (pygame.Rect(590, 120, 210, 16), BOTH),       # P4  top y=120 (goal ledge)
        ],
        "anchor":    None,
        "pests":     [{"min": 380, "max": 700, "speed": 2, "count": 1}],  # punishes falling in Chaos
        "spikes":    [],
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(740, 70, 30, 50),
    },
    # -- Level 3: Push It ---------------------------------------------------
    # Core idea: Shared object puzzle. Cabinet blocked by wall in Reality;
    # in Chaos wall is gone so pillar can be pushed all the way across.
    # Solution: SPACE to Chaos -> push pillar right until anchor_x ~ 600 ->
    #           jump straight up onto pillar (top y=340) -> jump to ledge (y=300) -> door.
    {
        "name":      "Push It",
        "hint":      "The cabinet and the pillar are the same object. Move one, move both.",
        "spawn":     (60, 400),
        "platforms": [
            F,
            (pygame.Rect(380, 300, 30, 140), REAL),       # Reality-only partition
            (pygame.Rect(650, 300, 150, 20), BOTH),       # high ledge, top y=300
        ],
        "anchor":    {"x": 200, "cab_h": 50, "pil_h": 100},
        "pests":     [],
        "spikes":    [],
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(740, 250, 30, 50),
    },
    # -- Level 4: Hold the Door ---------------------------------------------
    # Core idea: Park the shared object on the pressure plate to hold gate open.
    # Solution: Push cabinet in Reality to wall (x=180) -> SPACE to Chaos ->
    #           push pillar past wall onto plate (anchor_x > 260) and clear wall (player left >= 250) ->
    #           time pests / let pests pass in Reality -> SPACE to Reality ->
    #           jump over cabinet -> walk through open gate (x=560) -> door.
    {
        "name":      "Hold the Door",
        "hint":      "The gate stays open while something sits on the plate. Pests ignore you in Reality.",
        "spawn":     (60, 400),
        "platforms": [
            F,
            (pygame.Rect(220, 300, 30, 140), REAL),       # Reality-only partition
        ],
        "anchor":    {"x": 120, "cab_h": 50, "pil_h": 100},
        "pests":     [{"min": 250, "max": 370, "speed": 2, "count": 2}],
        "spikes":    [],
        "gate":      pygame.Rect(560, 290, 20, 150),          # solid in both worlds while closed
        "plate":     {"rect": pygame.Rect(300, 436, 60, 4), "world": CHAOS},
        "door":      pygame.Rect(720, 390, 30, 50),
    },
    # -- Level 5: Overtime --------------------------------------------------
    # Core idea: Finale combining wall crossing, pests, pushing, pillar staircase, mid-air swap.
    # Solution: Push cabinet to wall (x=220) -> SPACE to Chaos -> push pillar past wall ->
    #           SPACE to Reality once clear (left >= 290) -> push cabinet to anchor_x ~ 520 ->
    #           SPACE to Chaos -> jump straight up onto pillar (top y=340) ->
    #           jump onto CP (top y=260) -> jump right and SPACE mid-air to Reality ->
    #           land on RP (top y=180) -> walk into door.
    {
        "name":      "Overtime",
        "hint":      "Everything you've learned. The pillar is your staircase.",
        "spawn":     (60, 400),
        "platforms": [
            F,
            (pygame.Rect(260, 300, 30, 140), REAL),       # Reality-only partition
            (pygame.Rect(560, 260, 120, 16), CHAOS),      # CP  top y=260 (Chaos only)
            (pygame.Rect(710, 180, 90, 16),  REAL),       # RP  top y=180 (Reality only, holds door)
        ],
        "anchor":    {"x": 120, "cab_h": 50, "pil_h": 100},
        "pests":     [{"min": 300, "max": 420, "speed": 2, "count": 2}],
        "spikes":    [],
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(750, 130, 30, 50),            # sits on RP
    },
]


# ---------------------------------------------------------------------------
# Colour palettes  (indexed by dimension: [REALITY], [CHAOS])
# ---------------------------------------------------------------------------
# Background gradient top and bottom colours per dimension
BG_TOP = ((18, 26, 44),  (42, 8, 68))
BG_BOT = ((48, 56, 76),  (68, 20, 100))

# Ground / platform colours
COL_GROUND     = ((62, 70, 88),   (90, 38, 125))
COL_LEDGE_FACE = ((135, 142, 158), (155, 95, 188))
COL_LEDGE_EDGE = ((95, 102, 118), (115, 65, 148))

# Object colours
COL_WALL_MAIN  = (142, 145, 155)
COL_WALL_HI    = (178, 181, 190)
COL_WALL_SH    = (108, 110, 120)
COL_CABINET    = (158, 163, 174)
COL_PILLAR     = (128, 106, 76)
COL_PEST_BODY  = (195, 52, 52)
COL_PEST_EYE   = (255, 218, 75)
COL_DOOR_FRAME = (195, 160, 25)
COL_DOOR_BODY  = (218, 182, 46)
COL_DOOR_WIN   = (180, 220, 255)

# Player colours
COL_PLAYER_UNI = (52, 96, 170)   # uniform (Reality)
COL_PLAYER_CHO = (115, 55, 185)  # uniform (Chaos)
COL_PLAYER_SKIN= (238, 196, 156) # head/skin


from pathlib import Path
import pygame

# ---------------------------------------------------------------------------
# Sprite asset cache (rendered from Figma vector source)
# ---------------------------------------------------------------------------
ASSET_DIR = Path(__file__).resolve().parent / "assets"
ASSETS: dict[str, pygame.Surface] = {}


def load_assets():
    """Load all sprite textures from the assets/ directory."""
    if not ASSET_DIR.exists():
        return
    for item in ASSET_DIR.glob("*.png"):
        try:
            ASSETS[item.stem] = pygame.image.load(str(item)).convert_alpha()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Background gradient cache -- populated once in main() after pygame.init()
# ---------------------------------------------------------------------------
_BG_SURFS = [None, None]   # [Reality surface, Chaos surface]


def _make_gradient(w, h, top, bot):
    """Draw a smooth vertical colour gradient into a new Surface and return it.

    Draws one horizontal line per pixel row, blending from top to bot colour.
    Called once at startup to avoid re-drawing every frame.
    """
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(h - 1, 1)                     # 0.0 at top, 1.0 at bottom
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))
    return surf


# ===========================================================================
# DRAWING FUNCTIONS  (visual only -- no collision logic here)
# ===========================================================================

# ---------------------------------------------------------------------------
# draw_background  and world-specific decoration helpers
# ---------------------------------------------------------------------------

def draw_background(surf, dim, tick):
    """Blit the pre-baked gradient, then draw decorative props for each world."""
    if _BG_SURFS[dim] is None:
        _BG_SURFS[dim] = _make_gradient(WIDTH, HEIGHT, BG_TOP[dim], BG_BOT[dim])
    surf.blit(_BG_SURFS[dim], (0, 0))
    if dim == REALITY:
        _draw_reality_decor(surf, tick)
    else:
        _draw_chaos_decor(surf, tick)


def _draw_reality_decor(surf, tick):
    """Non-interactive Corporate Reality decorations: desks, monitors, ceiling lights."""
    # Ceiling fluorescent strip lights
    for lx in (80, 265, 445, 620):
        pygame.draw.rect(surf, (46, 52, 66), (lx - 3, 0, 86, 8))    # metal housing
        pygame.draw.rect(surf, (232, 238, 208), (lx, 0, 80, 5))      # tube glow
        glow = pygame.Surface((80, 28), pygame.SRCALPHA)
        glow.fill((232, 238, 208, 32))
        surf.blit(glow, (lx, 5))

    # Ceiling tile grid
    for cx in range(0, WIDTH, 60):
        pygame.draw.line(surf, (28, 34, 48), (cx, 0), (cx, 38), 1)
    pygame.draw.line(surf, (28, 34, 48), (0, 38), (WIDTH, 38), 1)

    # Skirting board along the floor
    pygame.draw.rect(surf, (44, 50, 64), (0, GROUND_Y - 7, WIDTH, 7))

    # Background office desks
    _draw_desk(surf, 30,  GROUND_Y)
    _draw_desk(surf, 535, GROUND_Y)

    # Motivational poster on the back wall (text strips = rectangles)
    pygame.draw.rect(surf, (68, 74, 90), (468, GROUND_Y - 205, 64, 84))
    pygame.draw.rect(surf, (78, 84, 100), (473, GROUND_Y - 200, 54, 64))
    for iy in range(4):
        pygame.draw.rect(surf, (92, 98, 115),
                         (476, GROUND_Y - 196 + iy * 14, 48 - iy * 8, 6))


def _draw_desk(surf, x, ground_y):
    """Draw a single background office desk with a monitor at position x."""
    # Desk surface
    pygame.draw.rect(surf, (48, 36, 24), (x, ground_y - 40, 100, 10))
    pygame.draw.rect(surf, (62, 48, 34), (x, ground_y - 42, 100, 4))  # highlight edge
    # Legs
    pygame.draw.rect(surf, (36, 26, 16), (x + 6,  ground_y - 30, 8, 30))
    pygame.draw.rect(surf, (36, 26, 16), (x + 86, ground_y - 30, 8, 30))
    # Monitor body
    pygame.draw.rect(surf, (22, 28, 44), (x + 28, ground_y - 86, 44, 36))
    pygame.draw.rect(surf, (36, 152, 228), (x + 31, ground_y - 83, 38, 26))  # screen
    # "Text" lines on screen
    for il in range(3):
        pygame.draw.rect(surf, (80, 196, 255),
                         (x + 34, ground_y - 80 + il * 7, 24 - il * 4, 3))
    # Monitor stand
    pygame.draw.rect(surf, (36, 36, 44), (x + 46, ground_y - 50, 8, 10))
    pygame.draw.rect(surf, (36, 36, 44), (x + 40, ground_y - 42, 20, 4))


def _draw_chaos_decor(surf, tick):
    """Non-interactive Surreal Chaos decorations: stars, floating orbs, arcane triangles."""
    # Twinkling stars -- each twinkles at a different rate based on its position
    stars = [
        (68, 32), (192, 20), (344, 62), (512, 16), (648, 52),
        (762, 32), (108, 92), (432, 102), (592, 76), (48, 138),
        (282, 56), (698, 112), (158, 186), (478, 158), (728, 198),
    ]
    for sx, sy in stars:
        bright = int(155 + 85 * math.sin(tick * 0.06 + sx * 0.13 + sy * 0.07))
        bright = max(60, min(255, bright))
        r = max(1, 2 if (sx + sy) % 7 == 0 else 1)
        pygame.draw.circle(surf, (bright, bright, min(bright + 40, 255)), (sx, sy), r)

    # Floating energy orbs (each bobs up/down with its own phase)
    orbs = [
        (138, 218, 20, (158, 58, 208)),
        (438, 158, 14, (98,  48, 192)),
        (668, 238, 18, (188, 78, 242)),
        (288, 128, 11, (138, 38, 188)),
        (568, 188, 10, (168, 58, 232)),
    ]
    for ox, oy, r, col in orbs:
        float_y = int(oy + 9 * math.sin(ox * 0.04 + tick * 0.025))
        # Halo glow
        halo = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*col, 45), (r * 3, r * 3), r * 3)
        surf.blit(halo, (ox - r * 3, float_y - r * 3))
        # Orb body and bright core
        pygame.draw.circle(surf, col, (ox, float_y), r)
        core = tuple(min(c + 90, 255) for c in col)
        pygame.draw.circle(surf, core, (ox, float_y), r // 2)

    # Rotating arcane triangles
    for tx, ty, size, col, spd in [
        (192, 308, 22, (98, 28, 148), 0.018),
        (548, 208, 17, (88, 22, 138), 0.025),
        (712, 348, 13, (118, 38, 162), 0.032),
    ]:
        angle = tick * spd + tx * 0.01
        pts = [(int(tx + size * math.cos(angle + i * 2 * math.pi / 3)),
                int(ty + size * math.sin(angle + i * 2 * math.pi / 3)))
               for i in range(3)]
        pygame.draw.polygon(surf, col, pts, 2)

    # Ground mist strip
    mist = pygame.Surface((WIDTH, 28), pygame.SRCALPHA)
    mist.fill((108, 38, 158, 38))
    surf.blit(mist, (0, GROUND_Y - 28))


# ---------------------------------------------------------------------------
# draw_ground  and  draw_ledge
# ---------------------------------------------------------------------------

def draw_ground(surf, dim):
    """Draw the floor with a bright highlight edge and subtle texture cracks."""
    col  = COL_GROUND[dim]
    hi   = tuple(min(c + 28, 255) for c in col)
    crack= tuple(max(c - 18, 0)   for c in col)
    pygame.draw.rect(surf, col, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surf, hi,    (0, GROUND_Y),     (WIDTH, GROUND_Y),     2)
    pygame.draw.line(surf, hi,    (0, GROUND_Y + 2), (WIDTH, GROUND_Y + 2), 1)
    for cx in range(28, WIDTH, 56):
        pygame.draw.line(surf, crack, (cx, GROUND_Y + 4), (cx, GROUND_Y + 14), 1)


def draw_ledge(surf, dim, ledge_rect):
    """Draw a raised platform with a bright top face and shadow bottom edge."""
    pygame.draw.rect(surf, COL_GROUND[dim], ledge_rect)
    # Bright top face (4 px tall)
    pygame.draw.rect(surf, COL_LEDGE_FACE[dim],
                     (ledge_rect.x, ledge_rect.y, ledge_rect.w, 4))
    # Shadow under the ledge
    pygame.draw.rect(surf, COL_LEDGE_EDGE[dim],
                     (ledge_rect.x, ledge_rect.bottom - 3, ledge_rect.w, 3))


# ---------------------------------------------------------------------------
# draw_wall  (Reality only)
# ---------------------------------------------------------------------------

def draw_wall(surf, wall_rect, dim=REALITY):
    """Draw a partition wall with highlights, shadow, and panel seams."""
    if dim == REALITY:
        pygame.draw.rect(surf, COL_WALL_MAIN, wall_rect)
        # Left highlight strip
        pygame.draw.rect(surf, COL_WALL_HI,
                         (wall_rect.left, wall_rect.top, 3, wall_rect.h))
        # Right shadow strip
        pygame.draw.rect(surf, COL_WALL_SH,
                         (wall_rect.right - 3, wall_rect.top, 3, wall_rect.h))
        # Top cap
        pygame.draw.rect(surf, COL_WALL_HI,
                         (wall_rect.x, wall_rect.y, wall_rect.w, 5))
        # Horizontal panel seam lines
        for sy in range(wall_rect.top + 38, wall_rect.bottom - 5, 42):
            pygame.draw.line(surf, COL_WALL_SH,
                             (wall_rect.left + 3, sy), (wall_rect.right - 3, sy), 1)
    else:
        # Chaos arcane barrier
        pygame.draw.rect(surf, (85, 38, 122), wall_rect)
        pygame.draw.rect(surf, (155, 78, 205), (wall_rect.left, wall_rect.top, 3, wall_rect.h))
        pygame.draw.rect(surf, (48, 18, 72), (wall_rect.right - 3, wall_rect.top, 3, wall_rect.h))
        pygame.draw.rect(surf, (155, 78, 205), (wall_rect.x, wall_rect.y, wall_rect.w, 5))


# ---------------------------------------------------------------------------
# draw_ghost_rect  (E5: ghost outlines for objects in the other world)
# ---------------------------------------------------------------------------

def draw_ghost_rect(surf, rect, obj_world):
    """Draw a faint 1-2px outline of an object that exists only in the other world (E5).

    Allows the player to see where platforms, walls, or plates will materialize.
    Corporate Reality objects look faint cyan/blue; Chaos objects look faint violet.
    """
    col = (115, 175, 245, 75) if obj_world == REAL else (205, 115, 250, 75)
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, col, (0, 0, rect.w, rect.h), 1)
    surf.blit(s, rect.topleft)


# ---------------------------------------------------------------------------
# draw_spike_strip  (E3: spikes hazard + E5: ghost spikes)
# ---------------------------------------------------------------------------

def draw_spike_strip(surf, rect, dim, is_ghost=False):
    """Draw a row of triangular hazard spikes along the bottom of the rect (E3, E5)."""
    if not is_ghost and dim == CHAOS and "floor_spikes_chaos" in ASSETS:
        sprite = ASSETS["floor_spikes_chaos"]
        sw = sprite.get_width()
        for x in range(rect.left, rect.right, sw):
            cw = min(sw, rect.right - x)
            surf.blit(sprite, (x, rect.top), pygame.Rect(0, 0, cw, rect.h))
        return

    spike_w = 14
    count = max(1, rect.w // spike_w)
    actual_w = rect.w / count

    if is_ghost:
        # Faint outline for the other world (E5)
        ghost_col = (205, 115, 250, 75) if dim == CHAOS else (115, 175, 245, 75)
        ghost_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        for i in range(count):
            x0 = int(i * actual_w)
            x1 = int((i + 0.5) * actual_w)
            x2 = int((i + 1) * actual_w)
            pts = [(x0, rect.h), (x1, 0), (x2, rect.h)]
            pygame.draw.polygon(ghost_surf, ghost_col, pts, 1)
        surf.blit(ghost_surf, rect.topleft)
    else:
        # Solid active hazard spikes
        body_col = (210, 48, 68) if dim == CHAOS else (190, 60, 50)
        hi_col   = (255, 130, 130)
        base_col = (110, 20, 30)
        for i in range(count):
            x0 = rect.left + int(i * actual_w)
            x1 = rect.left + int((i + 0.5) * actual_w)
            x2 = rect.left + int((i + 1) * actual_w)
            pts = [(x0, rect.bottom), (x1, rect.top), (x2, rect.bottom)]
            pygame.draw.polygon(surf, body_col, pts)
            pygame.draw.line(surf, hi_col, (x0, rect.bottom), (x1, rect.top), 1)
            pygame.draw.line(surf, base_col, (x1, rect.top), (x2, rect.bottom), 1)
        pygame.draw.line(surf, base_col, (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1), 2)


# ---------------------------------------------------------------------------
# draw_pressure_plate  (E4: Level 4 plate)
# ---------------------------------------------------------------------------

def draw_pressure_plate(surf, plate_rect, plate_world, pressed):
    """Draw the floor pressure plate (E4). Depresses and glows when held down."""
    pr = plate_rect
    if pressed and "pressure_plate_glow" in ASSETS:
        sprite = ASSETS["pressure_plate_glow"]
        surf.blit(sprite, (pr.x, pr.bottom - sprite.get_height()))
        return
    elif not pressed and "pressure_plate" in ASSETS:
        surf.blit(ASSETS["pressure_plate"], pr.topleft)
        return

    if pressed:
        # Pressed state: depressed to 2px, glowing bright active colour
        glow_col = (90, 255, 210) if plate_world == CHAOS else (255, 225, 70)
        depressed_rect = pygame.Rect(pr.x, pr.bottom - 2, pr.w, 2)
        pygame.draw.rect(surf, glow_col, depressed_rect)
        # Subtle energy aura
        glow = pygame.Surface((pr.w + 16, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*glow_col, 75), (0, 0, pr.w + 16, 12))
        surf.blit(glow, (pr.x - 8, pr.bottom - 8))
    else:
        # Unpressed state: 4px high with beveled edges and sensor center
        base_col = (112, 52, 155) if plate_world == CHAOS else (72, 92, 132)
        hi_col   = (192, 112, 245) if plate_world == CHAOS else (122, 162, 225)
        pygame.draw.rect(surf, base_col, pr)
        pygame.draw.rect(surf, hi_col, (pr.x, pr.y, pr.w, 1))
        # Center indicator dot
        dot_col = (255, 180, 80) if plate_world == CHAOS else (160, 210, 255)
        pygame.draw.circle(surf, dot_col, (pr.centerx, pr.centery), 2)


# ---------------------------------------------------------------------------
# draw_gate  (E4: Level 4 gate)
# ---------------------------------------------------------------------------

def draw_gate(surf, gate_rect, dim, pressed):
    """Draw the security gate (Level 4, E4). Solid closed, or raised/retracted open."""
    if pressed and "gate_open" in ASSETS:
        surf.blit(ASSETS["gate_open"], gate_rect.topleft)
        return
    elif not pressed and "gate_closed" in ASSETS:
        surf.blit(ASSETS["gate_closed"], gate_rect.topleft)
        return

    if pressed:
        # Open: green open indicator and retracted translucent energy barrier
        open_surf = pygame.Surface((gate_rect.w, gate_rect.h), pygame.SRCALPHA)
        open_surf.fill((40, 220, 120, 35))
        pygame.draw.rect(open_surf, (80, 255, 160, 90), (0, 0, gate_rect.w, gate_rect.h), 1)
        surf.blit(open_surf, gate_rect.topleft)
        # Top mounting with green status light
        pygame.draw.rect(surf, (42, 50, 62), (gate_rect.x, gate_rect.y, gate_rect.w, 8))
        pygame.draw.circle(surf, (80, 255, 130), (gate_rect.centerx, gate_rect.y + 4), 3)
    else:
        # Closed: solid security barrier with vertical steel bars and red warning lights
        body_col = (54, 60, 72) if dim == REALITY else (72, 34, 92)
        bar_col  = (86, 96, 116) if dim == REALITY else (122, 64, 152)
        pygame.draw.rect(surf, body_col, gate_rect)
        for gx in range(gate_rect.left + 4, gate_rect.right - 2, 6):
            pygame.draw.line(surf, bar_col, (gx, gate_rect.top + 8), (gx, gate_rect.bottom - 8), 2)
        # Top and bottom steel casings
        pygame.draw.rect(surf, (38, 42, 52), (gate_rect.x, gate_rect.y, gate_rect.w, 10))
        pygame.draw.rect(surf, (38, 42, 52), (gate_rect.x, gate_rect.bottom - 10, gate_rect.w, 10))
        # Red warning status lights
        pygame.draw.circle(surf, (255, 55, 55), (gate_rect.centerx, gate_rect.y + 5), 3)
        pygame.draw.circle(surf, (255, 55, 55), (gate_rect.centerx, gate_rect.bottom - 5), 3)


# ---------------------------------------------------------------------------
# draw_intro_card  (E6: Level intro card)
# ---------------------------------------------------------------------------

def draw_intro_card(surf, font, big, g):
    """Draw a centered frosted glass card introducing the level name and hint (E6)."""
    level = g["level"]
    name = level.get("name", f"Level {g['level_index'] + 1}")
    hint = level.get("hint", "")
    card_w, card_h = 580, 110
    card_x = (WIDTH - card_w) // 2
    card_y = (HEIGHT - card_h) // 2

    # Calculate opacity - fade out in the last 20 frames
    alpha = min(225, int(225 * (g["intro_timer"] / 20))) if g["intro_timer"] < 20 else 225
    card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    card.fill((12, 16, 28, alpha))
    pygame.draw.rect(card, (115, 145, 215, min(255, alpha + 30)), (0, 0, card_w, card_h), 2)
    surf.blit(card, (card_x, card_y))

    # Title with subtle shadow
    title_text = f"Level {g['level_index'] + 1}: {name}"
    title_sh = font.render(title_text, True, (40, 45, 60))
    title_surf = font.render(title_text, True, (255, 225, 95))
    surf.blit(title_sh, (card_x + 23, card_y + 19))
    surf.blit(title_surf, (card_x + 22, card_y + 18))

    # Hint text
    hint_surf = font.render(hint, True, (215, 230, 250))
    surf.blit(hint_surf, (card_x + 22, card_y + 50))

    # Dismiss prompt
    dismiss_surf = font.render("(Press any key to dismiss)", True, (135, 150, 175))
    surf.blit(dismiss_surf, (card_x + card_w - dismiss_surf.get_width() - 20, card_y + 80))


# ---------------------------------------------------------------------------
# draw_cabinet  (Reality version of the pushable object, E2 anchor safety)
# ---------------------------------------------------------------------------

def draw_cabinet(surf, level, anchor_x):
    """Draw a filing cabinet at the current anchor_x."""
    r = anchor_rect(level, REALITY, anchor_x)
    if r is None:
        return
    if "filing_cabinet_reality" in ASSETS:
        sprite = ASSETS["filing_cabinet_reality"]
        if sprite.get_size() != (r.w, r.h):
            surf.blit(pygame.transform.scale(sprite, (r.w, r.h)), r.topleft)
        else:
            surf.blit(sprite, r.topleft)
        return

    # Main body + highlights
    pygame.draw.rect(surf, COL_CABINET, r)
    pygame.draw.rect(surf, (185, 190, 200), (r.left, r.top, 3, r.h))  # left hi
    pygame.draw.rect(surf, (118, 123, 133), (r.right - 3, r.top, 3, r.h))  # right sh
    pygame.draw.rect(surf, (175, 180, 190), (r.left, r.top, r.w, 4))  # top cap
    # Three drawers
    dh = (r.h - 10) // 3
    for i in range(3):
        dy = r.top + 6 + i * (dh + 2)
        pygame.draw.rect(surf, (142, 147, 158), (r.left + 4, dy, r.w - 8, dh))
        pygame.draw.line(surf, (115, 120, 130),
                         (r.left + 4, dy + dh - 1), (r.right - 4, dy + dh - 1), 1)
        # Drawer handle
        hx = r.left + r.w // 2 - 6
        hy = dy + dh // 2 - 2
        pygame.draw.rect(surf, (95, 100, 110), (hx, hy, 12, 4))
        pygame.draw.rect(surf, (168, 173, 183), (hx + 1, hy + 1, 10, 2))


# ---------------------------------------------------------------------------
# draw_pillar  (Chaos version of the pushable object, E2 anchor safety)
# ---------------------------------------------------------------------------

def draw_pillar(surf, level, anchor_x):
    """Draw a stone pillar at the current anchor_x."""
    r = anchor_rect(level, CHAOS, anchor_x)
    if r is None:
        return
    if "stone_pillar_chaos" in ASSETS:
        sprite = ASSETS["stone_pillar_chaos"]
        if sprite.get_size() != (r.w, r.h):
            surf.blit(pygame.transform.scale(sprite, (r.w, r.h)), r.topleft)
        else:
            surf.blit(sprite, r.topleft)
        return

    # Main stone body
    pygame.draw.rect(surf, COL_PILLAR, r)
    # Left lighter face
    pygame.draw.rect(surf, (158, 132, 98), (r.left, r.top, 5, r.h))
    # Right darker shadow face
    pygame.draw.rect(surf, (96, 76, 52), (r.right - 5, r.top, 5, r.h))
    # Horizontal stone block seams
    for by in range(r.top + 22, r.bottom - 5, 22):
        pygame.draw.line(surf, (106, 84, 60),
                         (r.left + 3, by), (r.right - 3, by), 2)
    # Diagonal cracks
    pygame.draw.line(surf, (96, 76, 52),
                     (r.left + 8, r.top + 8), (r.left + 20, r.top + 34), 1)
    pygame.draw.line(surf, (96, 76, 52),
                     (r.left + 22, r.top + 52), (r.left + 30, r.top + 78), 1)
    # Top cap (slightly lighter)
    pygame.draw.rect(surf, (152, 128, 92), (r.left, r.top, r.w, 5))


# ---------------------------------------------------------------------------
# draw_door
# ---------------------------------------------------------------------------

def draw_door(surf, door_rect, tick):
    """Draw the exit door with a golden frame and a gentle pulsing glow."""
    pulse  = int(4 * math.sin(tick * 0.12))
    g_rect = door_rect.inflate(8 + pulse, 8 + pulse)
    glow   = pygame.Surface((g_rect.w, g_rect.h), pygame.SRCALPHA)
    glow.fill((255, 230, 100, 70))
    surf.blit(glow, g_rect.topleft)

    if "exit_door" in ASSETS:
        surf.blit(ASSETS["exit_door"], door_rect.topleft)
        return

    # Outer frame
    pygame.draw.rect(surf, COL_DOOR_FRAME, door_rect.inflate(6, 6))
    # Door body
    pygame.draw.rect(surf, COL_DOOR_BODY, door_rect)
    # Upper window panel
    win = pygame.Rect(door_rect.x + 4, door_rect.y + 4,
                      door_rect.w - 8, door_rect.h // 2 - 4)
    pygame.draw.rect(surf, COL_DOOR_WIN, win)
    pygame.draw.rect(surf, COL_DOOR_BODY, win.inflate(-4, -4))  # window sill
    # Lower wooden panel
    lo = pygame.Rect(door_rect.x + 4, door_rect.y + door_rect.h // 2 + 2,
                     door_rect.w - 8, door_rect.h // 2 - 6)
    pygame.draw.rect(surf, (COL_DOOR_FRAME[0] - 20, COL_DOOR_FRAME[1] - 20,
                             max(COL_DOOR_FRAME[2] - 10, 0)), lo)
    # Doorknob
    pygame.draw.circle(surf, (178, 138, 18), (door_rect.right - 7, door_rect.centery), 3)
    pygame.draw.circle(surf, (220, 188, 58), (door_rect.right - 8, door_rect.centery - 1), 2)


# ---------------------------------------------------------------------------
# draw_player
# ---------------------------------------------------------------------------

def draw_player(surf, player_rect, dim, tick, facing_right=True):
    """Draw the custodian player character.

    Draws over the collision rect area but DOES NOT modify it.
    Uses Figma-designed sprite with procedural fallback.
    """
    pr = player_rect
    cx = pr.centerx

    # Chaos aura (drawn first so it appears behind everything)
    if dim == CHAOS:
        aura = pygame.Surface((pr.w + 20, pr.h + 20), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (*COL_PLAYER_CHO, 48),
                            (0, 0, pr.w + 20, pr.h + 20))
        surf.blit(aura, (pr.left - 10, pr.top - 10))

    sprite_key = "custodian_reality" if dim == REALITY else "custodian_chaos"
    if not facing_right:
        sprite_key += "_mirrored"
    if sprite_key in ASSETS:
        surf.blit(ASSETS[sprite_key], pr.topleft)
        return

    # Fallback procedural custodian
    uni  = COL_PLAYER_UNI if dim == REALITY else COL_PLAYER_CHO
    uni_hi = tuple(min(c + 24, 255) for c in uni)
    uni_sh = tuple(max(c - 30, 0)   for c in uni)

    # Legs / lower body
    pygame.draw.rect(surf, uni_sh, (pr.left + 5, pr.bottom - 14, pr.w - 10, 14))
    # Feet (dark shoes)
    pygame.draw.rect(surf, (28, 28, 34), (pr.left + 2,       pr.bottom - 5, 10, 5))
    pygame.draw.rect(surf, (28, 28, 34), (pr.right - 12,     pr.bottom - 5, 10, 5))

    # Torso
    pygame.draw.rect(surf, uni,    (pr.left + 3, pr.top + 12, pr.w - 6, pr.h - 24))
    pygame.draw.rect(surf, uni_hi, (pr.left + 3, pr.top + 12, 3, pr.h - 24))  # left highlight
    pygame.draw.rect(surf, uni_sh, (pr.right - 6, pr.top + 12, 3, pr.h - 24)) # right shadow
    # Belt stripe
    pygame.draw.rect(surf, uni_sh, (pr.left + 3, pr.centery - 2, pr.w - 6, 3))
    # Name badge
    pygame.draw.rect(surf, (192, 196, 208), (cx - 5, pr.top + 15, 10, 6))

    # Arms
    pygame.draw.rect(surf, uni_sh, (pr.left - 2,  pr.top + 14, 6, 12))
    pygame.draw.rect(surf, uni_sh, (pr.right - 4, pr.top + 14, 6, 12))

    # Head (skin-coloured circle)
    hcy = pr.top + 8
    pygame.draw.circle(surf, COL_PLAYER_SKIN, (cx, hcy), 9)

    # Cap
    pygame.draw.rect(surf, uni_sh, (cx - 10, hcy - 9, 20, 6))
    pygame.draw.rect(surf, uni,    (cx - 8,  hcy - 7, 16, 5))
    pygame.draw.rect(surf, uni_sh, (cx - 12, hcy - 3, 5, 3))  # cap brim

    # Eyes
    for ex in (cx - 3, cx + 3):
        pygame.draw.circle(surf, (34, 28, 24), (ex, hcy + 2), 2)
        pygame.draw.circle(surf, (220, 220, 232), (ex, hcy + 1), 1)  # eye glint


# ---------------------------------------------------------------------------
# draw_pest  and  draw_pests
# ---------------------------------------------------------------------------

def draw_pest(surf, pest, tick):
    """Draw a single interdimensional pest with legs, antennae, and glowing eyes."""
    px  = int(pest["x"])
    bob = int(2 * math.sin(tick * 0.15 + px * 0.05))  # bobbing animation
    py  = GROUND_Y - 24 + bob
    cy  = py + 9   # vertical centre of the oval body

    if "pest" in ASSETS:
        sprite = ASSETS["pest"]
        if pest.get("dir", 1) > 0:
            surf.blit(pygame.transform.flip(sprite, True, False), (px, py))
        else:
            surf.blit(sprite, (px, py))
        return

    # Fallback procedural pest
    pygame.draw.ellipse(surf, COL_PEST_BODY, (px, py, 30, 18))
    # Body highlight
    pygame.draw.ellipse(surf, (228, 75, 75), (px + 3, py + 2, 13, 7))

    # Six legs (3 per side, drawn as lines)
    for i, lx in enumerate((px + 5, px + 13, px + 21)):
        pygame.draw.line(surf, (162, 38, 38), (lx, cy), (lx - 6, cy + 8), 1)
        pygame.draw.line(surf, (162, 38, 38), (lx, cy), (lx - 6, cy - 6), 1)

    # Antennae
    pygame.draw.line(surf, (188, 48, 48), (px + 6, py + 2), (px - 2, py - 6), 1)
    pygame.draw.line(surf, (188, 48, 48), (px + 11, py + 2), (px + 9, py - 7), 1)
    pygame.draw.circle(surf, (255, 96, 96), (px - 2, py - 6), 2)
    pygame.draw.circle(surf, (255, 96, 96), (px + 9, py - 7), 2)

    # Glowing eyes
    for ex in (px + 5, px + 14):
        pygame.draw.circle(surf, COL_PEST_EYE, (ex, cy - 2), 3)
        pygame.draw.circle(surf, (38, 18, 8),  (ex + 1, cy - 2), 1)


def draw_pests(surf, g, tick):
    """Draw all pests -- only called when dim == CHAOS."""
    if g["dim"] != CHAOS:
        return
    for pest in g["pests"]:
        draw_pest(surf, pest, tick)


# ---------------------------------------------------------------------------
# Particle system  (visual only -- spawned on swap, updated in update())
# ---------------------------------------------------------------------------

def _spawn_particles(g):
    """Burst particles at the player's centre when a dimension swap succeeds."""
    cx, cy = g["player"].centerx, g["player"].centery
    colours = [
        (100, 200, 255), (200, 100, 255), (255, 200, 100),
        (100, 255, 200), (255, 100, 200), (255, 255, 180),
    ]
    for _ in range(PARTICLE_COUNT):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.5, 5.0)
        life  = random.randint(PARTICLE_LIFE // 2, PARTICLE_LIFE)
        g["particles"].append({
            "x":        float(cx),
            "y":        float(cy),
            "vx":       math.cos(angle) * speed,
            "vy":       math.sin(angle) * speed - 1.5,  # slight upward bias
            "life":     life,
            "max_life": life,
            "col":      random.choice(colours),
            "size":     random.randint(2, 5),
        })


def _update_particles(g):
    """Move particles, apply gravity, and discard expired ones."""
    alive = []
    for p in g["particles"]:
        p["x"]  += p["vx"]
        p["y"]  += p["vy"]
        p["vy"] += 0.15   # particle gravity (lighter than game gravity)
        p["life"] -= 1
        if p["life"] > 0:
            alive.append(p)
    g["particles"] = alive


def draw_particles(surf, particles):
    """Draw each particle as a fading, shrinking circle."""
    for p in particles:
        if p["life"] <= 0:
            continue
        # Fade out: alpha and size both shrink with remaining life
        frac  = p["life"] / p["max_life"]
        alpha = int(255 * frac)
        size  = max(1, int(p["size"] * frac))
        # Draw to a tiny SRCALPHA surface to support alpha blending
        d = size * 2 + 2
        circle_surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(circle_surf, (*p["col"], alpha), (size + 1, size + 1), size)
        surf.blit(circle_surf, (int(p["x"]) - size - 1, int(p["y"]) - size - 1))


# ---------------------------------------------------------------------------
# draw_hud  -- styled semi-transparent panel
# ---------------------------------------------------------------------------

def draw_hud(surf, font, g):
    """Draw a dark-glass HUD panel in the top-left with score, lives, and level."""
    panel_w, panel_h = 205, 152
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((8, 8, 18, 168))
    # Panel border
    pygame.draw.rect(panel, (88, 112, 175, 170), (0, 0, panel_w, panel_h), 1)
    surf.blit(panel, (6, 6))

    # Coloured dot showing current world (Figma asset or procedural dot)
    dot_key = "world_dot_chaos" if g["dim"] == CHAOS else "world_dot_reality"
    if dot_key in ASSETS:
        surf.blit(ASSETS[dot_key], (10, 10))
    else:
        dot_col = (75, 155, 252) if g["dim"] == REALITY else (198, 75, 252)
        pygame.draw.circle(surf, dot_col,         (18, 22), 5)
        pygame.draw.circle(surf, (255, 255, 255), (18, 22), 5, 1)

    world = "Corporate Reality" if g["dim"] == REALITY else "Surreal Chaos"
    surf.blit(font.render(world, True, (205, 218, 242)), (36, 14))

    # Divider
    pygame.draw.line(surf, (58, 78, 128), (10, 37), (205, 37), 1)

    surf.blit(font.render(f"Score  {int(g['score'])}", True, (195, 228, 255)), (12, 44))

    level_str = f"Level  {g['level_index'] + 1} / {len(LEVELS)}"
    surf.blit(font.render(level_str, True, (195, 228, 255)), (12, 70))

    # Lives as heart icons (Figma asset or heart circles)
    surf.blit(font.render("Lives", True, (195, 228, 255)), (12, 96))
    if "heart_full" in ASSETS and "heart_empty" in ASSETS:
        for i in range(3):
            h_key = "heart_full" if i < g["lives"] else "heart_empty"
            surf.blit(ASSETS[h_key], (70 + i * 26, 92))
    else:
        for i in range(g["lives"]):
            hx = 82 + i * 24
            pygame.draw.circle(surf, (218, 55, 78), (hx + 5, 104), 7)
            pygame.draw.circle(surf, (252, 98, 118), (hx + 3, 101), 3)  # glint

    surf.blit(font.render(f"Best   {g['high_score']}", True, (175, 198, 228)), (12, 124))

    # Bottom hint
    hint = font.render("SPACE swap  |  R restart", True, (128, 140, 162))
    surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 24))


# ---------------------------------------------------------------------------
# draw_title  -- animated title screen shown before the game starts
# ---------------------------------------------------------------------------

def draw_title(surf, font, big, tick):
    """Render the animated title screen. Shown until any key is pressed."""
    if "title_background" in ASSETS:
        surf.blit(ASSETS["title_background"], (0, 0))
    else:
        t   = (math.sin(tick * 0.008) + 1) / 2
        r   = int(18 * (1 - t) + 42 * t)
        g   = int(26 * (1 - t) + 8  * t)
        b   = int(44 * (1 - t) + 68 * t)
        surf.fill((r, g, b))

    # Dynamic glowing energy halos
    for ox, oy, radius, col in [
        (148, 148, 20, (158, 58, 208)),
        (618, 198, 16, (78, 178, 252)),
        (378, 298, 14, (198, 78, 252)),
        (198, 348, 11, (98, 198, 252)),
        (578, 98,  18, (178, 78, 238)),
    ]:
        float_y = int(oy + 10 * math.sin(ox * 0.04 + tick * 0.02))
        halo = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*col, 35), (radius * 2, radius * 2), radius * 2)
        surf.blit(halo, (ox - radius * 2, float_y - radius * 2))

    # Title logo / wordmark
    if "logo_wordmark" in ASSETS:
        logo = ASSETS["logo_wordmark"]
        surf.blit(logo, ((WIDTH - logo.get_width()) // 2, 42))
    else:
        # Title text with drop shadow
        title_y = HEIGHT // 2 - 105
        shadow  = big.render("SHIFT  WORK", True, (75, 38, 118))
        title   = big.render("SHIFT  WORK", True, (255, 255, 255))
        surf.blit(shadow, (WIDTH // 2 - title.get_width() // 2 + 3, title_y + 3))
        surf.blit(title,  (WIDTH // 2 - title.get_width() // 2,     title_y))

    # Subtitle
    sub = font.render("A 2D Dimension-Swapping Platformer", True, (195, 180, 235))
    surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 145))

    # Control card panel
    panel_w, panel_h = 440, 120
    panel_x = (WIDTH - panel_w) // 2
    panel_y = 195
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((10, 14, 26, 170))
    pygame.draw.rect(panel, (90, 115, 175, 160), (0, 0, panel_w, panel_h), 1)
    surf.blit(panel, (panel_x, panel_y))

    # Control summary
    for i, line in enumerate([
        "WASD / Arrows -- Move and Jump",
        "SPACE -- Swap between Corporate Reality and Surreal Chaos",
        "R -- Restart level (during play) or restart game",
    ]):
        rendered = font.render(line, True, (195, 215, 240))
        surf.blit(rendered, (panel_x + 20, panel_y + 16 + i * 32))

    # Blinking "press any key" prompt
    if (tick // 28) % 2 == 0:
        prompt = font.render("Press any key to begin", True, (255, 235, 130))
        surf.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT - 52))


# ---------------------------------------------------------------------------
# draw_end_screen  -- win / game-over overlay
# ---------------------------------------------------------------------------

def draw_end_screen(surf, font, big, g):
    """Draw a darkened overlay with the win or game-over headline."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 158))
    surf.blit(overlay, (0, 0))

    if g["state"] == "win":
        headline = "SHIFT COMPLETE -- ALL LEVELS DONE!"
        hcol     = (255, 228, 98)
    else:
        headline = "GAME OVER"
        hcol     = (255, 98, 98)

    t = big.render(headline, True, hcol)
    surf.blit(t, (WIDTH // 2 - t.get_width() // 2, 148))

    score_s = font.render(
        f"Final score: {int(g['score'])}   Best: {g['high_score']}",
        True, (255, 255, 255)
    )
    surf.blit(score_s, (WIDTH // 2 - score_s.get_width() // 2, 218))

    restart_s = font.render("Press R to restart", True, (188, 205, 232))
    surf.blit(restart_s, (WIDTH // 2 - restart_s.get_width() // 2, 258))


# ---------------------------------------------------------------------------
# draw  -- master draw function  (called every frame during gameplay)
# ---------------------------------------------------------------------------

def draw(surf, font, big, g, tick):
    """Render the full game frame to surf.

    main() then blits surf to the screen with a shake offset if needed.
    Drawing order (painter's algorithm, back to front):
      background -> ground -> platforms/walls (and ghost outlines) ->
      spikes -> plate -> gate -> door -> anchor -> pests -> player ->
      particles -> HUD -> intro card -> messages -> end-screen -> swap flash
    """
    dim   = g["dim"]
    level = g["level"]

    draw_background(surf, dim, tick)               # 1. gradient + world decorations
    draw_ground(surf, dim)                          # 2. floor

    # 3. Platforms and walls (E1, E5)
    for rect, tag in level.get("platforms", []):
        # The floor platform (y >= GROUND_Y and w >= WIDTH) is already drawn by draw_ground
        if rect.y >= GROUND_Y and rect.w >= WIDTH:
            continue
        if is_tag_active(tag, dim):
            # Solid in this world
            if rect.h >= 50 and rect.w <= 50:
                draw_wall(surf, rect, dim)
            else:
                draw_ledge(surf, dim, rect)
        else:
            # Ghost outline for the other world (E5)
            draw_ghost_rect(surf, rect, tag)

    # 4. Spikes hazard (E3, E5)
    for spike_rect, s_world in level.get("spikes", []):
        if is_tag_active(s_world, dim):
            draw_spike_strip(surf, spike_rect, dim, is_ghost=False)
        else:
            draw_spike_strip(surf, spike_rect, s_world, is_ghost=True)

    # 5. Pressure plate & Gate (E4, E5)
    pressed = is_plate_pressed(level, dim, g["player"], g.get("anchor_x"))
    if level.get("plate") is not None:
        pr = level["plate"]["rect"]
        pw = level["plate"]["world"]
        if is_tag_active(pw, dim):
            draw_pressure_plate(surf, pr, pw, pressed)
        else:
            draw_ghost_rect(surf, pr, pw)

    if level.get("gate") is not None:
        draw_gate(surf, level["gate"], dim, pressed)

    # 6. Exit door (always visible)
    draw_door(surf, level["door"], tick)

    # 7. Shared pushable object (E2)
    if level.get("anchor") is not None and g.get("anchor_x") is not None:
        if dim == REALITY:
            draw_cabinet(surf, level, g["anchor_x"])
        else:
            draw_pillar(surf, level, g["anchor_x"])

    # 8. Pests (Chaos only)
    if dim == CHAOS:
        draw_pests(surf, g, tick)

    # 9. Custodian player sprite
    draw_player(surf, g["player"], dim, tick, g.get("facing_right", True))

    # 10. Particles
    draw_particles(surf, g["particles"])

    # 11. HUD
    draw_hud(surf, font, g)

    # "Can't swap" warning message
    if g["msg_timer"] > 0:
        msg = font.render("Can't swap -- something solid is in the way!",
                          True, (255, 218, 98))
        surf.blit(msg, (12, 162))

    # 12. Level intro card (E6)
    if g["intro_timer"] > 0 and g["state"] == "play":
        draw_intro_card(surf, font, big, g)

    # 13. End screen
    if g["state"] != "play":
        draw_end_screen(surf, font, big, g)

    # 14. Swap white flash
    if g["flash_frames"] > 0:
        alpha = int(200 * g["flash_frames"] / FLASH_FRAMES)
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        surf.blit(flash, (0, 0))


# ===========================================================================
# GAME LOGIC  (collision rects identical to P0/P1 -- drawing functions above
#              are the only things that changed for the visual polish pass)
# ===========================================================================

# ---------------------------------------------------------------------------
# Solid-rect helpers  -- these determine what is collidable; DO NOT change
# ---------------------------------------------------------------------------

def is_plate_pressed(level, dim, player_rect, anchor_x):
    """Return True if the level's pressure plate is currently held down (E4).

    Pressed each frame if either:
    1. anchor_rect(level, plate_world, anchor_x) overlaps the plate rect (the anchor
       holds it in either world, because it is the same object), or
    2. dim matches plate_world and the player rect overlaps the plate rect.
    """
    plate = level.get("plate")
    if not plate:
        return False
    pr = plate["rect"]
    pw = plate["world"]

    # 1. The anchor holds it down in either world
    if level.get("anchor") is not None and anchor_x is not None:
        dim_for_plate = CHAOS if pw == CHAOS else REALITY
        a = anchor_rect(level, dim_for_plate, anchor_x)
        if a is not None and a.colliderect(pr):
            return True

    # 2. The player holds it down if present in the plate's active world
    if is_tag_active(pw, dim) and player_rect.colliderect(pr):
        return True

    return False


def static_solids(level, dim, plate_pressed=False):
    """Return a list of immovable solid Rects for the given dimension (E1, E4).

    Returns every platform tagged BOTH or matching dim.
    If the level has a gate and it is not held open by the plate,
    the gate is solid in BOTH worlds.
    """
    solids = [rect for rect, tag in level.get("platforms", []) if is_tag_active(tag, dim)]
    if level.get("gate") is not None and not plate_pressed:
        solids.append(level["gate"])
    return solids


def anchor_rect(level, dim, x):
    """Return the collision Rect of the shared pushable object, or None if no anchor (E2).

    In Reality  -> filing cabinet (height cab_h px, default 50)
    In Chaos    -> stone pillar    (height pil_h px, default 100)
    Width is always 40 px.
    """
    anchor_info = level.get("anchor")
    if anchor_info is None or x is None:
        return None
    cab_h = anchor_info.get("cab_h", 50)
    pil_h = anchor_info.get("pil_h", 100)
    h = cab_h if dim == REALITY else pil_h
    return pygame.Rect(int(x), GROUND_Y - h, 40, h)


def all_solids(g, dim):
    """All solid rects: static platforms, closed gate, plus the anchor if present."""
    level = g["level"]
    pressed = is_plate_pressed(level, dim, g["player"], g.get("anchor_x"))
    solids = list(static_solids(level, dim, pressed))
    if level.get("anchor") is not None and g.get("anchor_x") is not None:
        a = anchor_rect(level, dim, g["anchor_x"])
        if a is not None:
            solids.append(a)
    return solids


# ---------------------------------------------------------------------------
# Game-state factory
# ---------------------------------------------------------------------------

def _init_pests(level):
    """Create pest instances for all pest zones in the level (E1)."""
    pests = []
    for zone in level.get("pests", []):
        count = zone["count"]
        span  = zone["max"] - zone["min"]
        for i in range(count):
            px        = zone["min"] + (span * i // max(count - 1, 1))
            direction = 1 if i % 2 == 0 else -1
            pests.append({
                "x":     float(px),
                "dir":   direction,
                "min":   zone["min"],
                "max":   zone["max"],
                "speed": zone["speed"],
            })
    return pests


def new_game(level_index=0, score=0, lives=3, high_score=0):
    """Create and return a fresh game-state dict for the given level.

    score and lives are passed in so level progression preserves them.
    """
    level = LEVELS[level_index]
    sx, sy = level["spawn"]

    anchor_x = float(level["anchor"]["x"]) if level.get("anchor") is not None else None

    return {
        "dim":          REALITY,
        "level_index":  level_index,
        "level":        level,
        "player":       pygame.Rect(sx, sy, 28, 40),
        "vy":           0.0,
        "on_ground":    False,
        "anchor_x":     anchor_x,
        "pests":        _init_pests(level),
        "score":        float(score),
        "lives":        lives,
        "high_score":   high_score,
        "state":        "play",
        "msg_timer":    0,
        "flash_frames": 0,
        "last_swap_ms": -SWAP_COOLDOWN_MS,
        # Visual-only state
        "particles":    [],              # active swap-burst particles
        "shake_frames": 0,              # frames of screen shake remaining
        "intro_timer":  150,            # E6: frames to display level intro card (2.5s)
        "facing_right": True,           # horizontal facing direction for sprite rendering
    }


# ---------------------------------------------------------------------------
# Movement helpers  (E2 anchor-None safe, E4 gate-aware)
# ---------------------------------------------------------------------------

def move_x(g, dx):
    """Move the player horizontally and resolve collisions with anchor + statics."""
    p   = g["player"]
    dim = g["dim"]
    p.x += dx

    level = g["level"]
    pressed = is_plate_pressed(level, dim, p, g.get("anchor_x"))
    statics = static_solids(level, dim, pressed)

    # Try to push the anchor if present in this level (E2)
    if level.get("anchor") is not None and g.get("anchor_x") is not None:
        a = anchor_rect(level, dim, g["anchor_x"])
        if a is not None and dx and p.colliderect(a):
            nx      = g["anchor_x"] + dx
            test    = anchor_rect(level, dim, nx)
            blocked = any(test.colliderect(s) for s in statics)
            if 0 <= nx <= WIDTH - 40 and not blocked:
                g["anchor_x"] = nx
            elif dx > 0:
                p.right = a.left
            else:
                p.left  = a.right

    # Resolve static solid collisions (re-evaluate plate in case anchor moved onto/off it)
    pressed = is_plate_pressed(level, dim, p, g.get("anchor_x"))
    statics = static_solids(level, dim, pressed)
    for s in statics:
        if p.colliderect(s):
            if dx > 0: p.right = s.left
            else:       p.left  = s.right

    # Clamp to screen
    p.left  = max(0, p.left)
    p.right = min(WIDTH, p.right)


def move_y(g):
    """Apply gravity, move vertically, and resolve vertical collisions."""
    p = g["player"]
    g["vy"] = min(g["vy"] + GRAVITY, MAX_FALL)
    dy = math.ceil(g["vy"]) if g["vy"] > 0 else math.floor(g["vy"])
    p.y += dy
    g["on_ground"] = False
    for s in all_solids(g, g["dim"]):
        if p.colliderect(s):
            if g["vy"] > 0:
                p.bottom       = s.top
                g["on_ground"] = True
            else:
                p.top = s.bottom
            g["vy"] = 0


# ---------------------------------------------------------------------------
# Dimension swap  (P1 logic + visual triggers for polish pass)
# ---------------------------------------------------------------------------

def try_swap(g, now_ms):
    """Attempt a dimension swap.

    Refuses if on cooldown or player would overlap a solid.
    On success: changes dim, starts flash, spawns particles, starts screen shake.
    """
    if now_ms - g["last_swap_ms"] < SWAP_COOLDOWN_MS:
        return   # cooldown not yet expired

    new_dim = 1 - g["dim"]

    if any(g["player"].colliderect(s) for s in all_solids(g, new_dim)):
        g["msg_timer"] = 90   # show blocked message
        return

    g["dim"]          = new_dim
    g["flash_frames"] = FLASH_FRAMES
    g["last_swap_ms"] = now_ms
    # Visual polish: particles and screen shake
    _spawn_particles(g)
    g["shake_frames"] = SHAKE_FRAMES


# ---------------------------------------------------------------------------
# Main update
# ---------------------------------------------------------------------------

def update(g, keys, dt, now_ms):
    """Update all game state for one frame."""
    if g["state"] != "play":
        return

    dx = 0
    if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= SPEED
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += SPEED
    if dx > 0:
        g["facing_right"] = True
    elif dx < 0:
        g["facing_right"] = False
    if dx:
        move_x(g, dx)
    move_y(g)

    level = g["level"]

    # Pest patrol movement and Chaos collision
    for pest in g["pests"]:
        pest["x"] += pest["speed"] * pest["dir"]
        if pest["x"] <= pest["min"]:
            pest["x"] = float(pest["min"])
            pest["dir"] = 1
        elif pest["x"] >= pest["max"]:
            pest["x"] = float(pest["max"])
            pest["dir"] = -1

    if g["dim"] == CHAOS:
        for pest in g["pests"]:
            pest_rect = pygame.Rect(int(pest["x"]), GROUND_Y - 24, 30, 24)
            if g["player"].colliderect(pest_rect):
                _player_hit(g)
                break

    # Spikes hazard collision (E3: active in current dimension)
    if g["state"] == "play":
        for spike_rect, s_world in level.get("spikes", []):
            if is_tag_active(s_world, g["dim"]) and g["player"].colliderect(spike_rect):
                _player_hit(g)
                break

    # Fall safety (E7: falling into pit / below screen triggers hit)
    if g["state"] == "play" and g["player"].top > HEIGHT:
        _player_hit(g)

    # Goal door collision
    if g["state"] == "play" and g["player"].colliderect(level["door"]):
        g["score"] += 1000
        _advance_level(g)

    g["score"] += dt / 1000 * 10

    if g["msg_timer"]    > 0: g["msg_timer"]    -= 1
    if g["flash_frames"] > 0: g["flash_frames"] -= 1
    if g["shake_frames"] > 0: g["shake_frames"] -= 1  # visual only
    if g["intro_timer"]  > 0: g["intro_timer"]  -= 1  # E6 intro card
    _update_particles(g)                               # visual only


# ---------------------------------------------------------------------------
# Lives / level progression  (E2 anchor safety, E1 pest reset)
# ---------------------------------------------------------------------------

def _player_hit(g):
    """Lose a life; respawn at start of current level or game-over."""
    g["lives"] -= 1
    if g["lives"] <= 0:
        g["state"]      = "lose"
        g["high_score"] = max(g["high_score"], int(g["score"]))
        _save_high_score(g["high_score"])
    else:
        level  = g["level"]
        sx, sy = level["spawn"]
        g["player"].topleft = (sx, sy)
        g["vy"]             = 0.0
        g["dim"]            = REALITY
        g["anchor_x"]       = float(level["anchor"]["x"]) if level.get("anchor") is not None else None
        g["msg_timer"]      = 0
        g["flash_frames"]   = 0
        g["particles"]      = []   # clear particles on respawn
        g["pests"]          = _init_pests(level)
        g["facing_right"]   = True


def _advance_level(g):
    """Load the next level, or trigger win if all levels are done."""
    next_index = g["level_index"] + 1
    if next_index >= len(LEVELS):
        g["state"]      = "win"
        g["high_score"] = max(g["high_score"], int(g["score"]))
        _save_high_score(g["high_score"])
    else:
        score, lives, hs = g["score"], g["lives"], g["high_score"]
        g.update(new_game(next_index, score, lives, hs))


# ---------------------------------------------------------------------------
# High score persistence  (unchanged from P1)
# ---------------------------------------------------------------------------

HIGH_SCORE_FILE = "highscore.txt"


def _load_high_score():
    """Read high score from disk; returns 0 on any error."""
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def _save_high_score(score):
    """Write high score to disk; silently ignores errors."""
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass


# ===========================================================================
# MAIN ENTRY POINT
# ===========================================================================

def main():
    """Initialise pygame, pre-bake gradients, and run the game loop."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Shift Work")
    load_assets()   # load custom Figma sprites
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont(None, 26)   # regular HUD font
    big   = pygame.font.SysFont(None, 54)   # large font for overlays

    # Pre-bake the gradient backgrounds (one per dimension).
    # Doing this once avoids re-drawing 500 horizontal lines every frame.
    _BG_SURFS[REALITY] = _make_gradient(WIDTH, HEIGHT, BG_TOP[REALITY], BG_BOT[REALITY])
    _BG_SURFS[CHAOS]   = _make_gradient(WIDTH, HEIGHT, BG_TOP[CHAOS],   BG_BOT[CHAOS])

    # The scene surface: we draw everything here, then blit to screen.
    # This lets us apply a screen-shake offset (sx, sy) cheaply.
    scene = pygame.Surface((WIDTH, HEIGHT))

    saved_hs      = _load_high_score()
    showing_title = True   # show title screen first
    title_tick    = 0
    g             = None
    tick          = 0      # global frame counter for animations

    running = True
    while running:
        dt     = clock.tick(60)
        now_ms = pygame.time.get_ticks()
        tick  += 1

        # ── Event handling ──────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if showing_title:
                    # Any key dismisses the title screen and starts the game
                    showing_title = False
                    g = new_game(level_index=0, high_score=saved_hs)
                else:
                    # Dismiss level intro card early on any key press (E6)
                    if g["intro_timer"] > 0:
                        g["intro_timer"] = 0
                    if event.key == pygame.K_r:
                        if g["state"] == "play":
                            # E8: Restart current level
                            score, lives, hs = g["score"], g["lives"], g["high_score"]
                            g.update(new_game(g["level_index"], score, lives, hs))
                        else:
                            # Full game restart from win or game-over
                            hs = g["high_score"]
                            g = new_game(level_index=0, high_score=hs)
                    elif g["state"] == "play":
                        if event.key == pygame.K_SPACE:
                            try_swap(g, now_ms)
                        elif event.key in (pygame.K_UP, pygame.K_w) and g["on_ground"]:
                            g["vy"] = JUMP

        # ── Update and draw ─────────────────────────────────────────────────
        if showing_title:
            title_tick += 1
            draw_title(scene, font, big, title_tick)
            screen.blit(scene, (0, 0))
        else:
            update(g, pygame.key.get_pressed(), dt, now_ms)
            draw(scene, font, big, g, tick)

            # Apply screen shake: blit the scene with a small random offset
            if g["shake_frames"] > 0:
                sx = random.randint(-SHAKE_MAG, SHAKE_MAG)
                sy = random.randint(-(SHAKE_MAG // 2), SHAKE_MAG // 2)
                screen.fill((0, 0, 0))   # black border visible during shake
                screen.blit(scene, (sx, sy))
            else:
                screen.blit(scene, (0, 0))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
