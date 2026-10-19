import math
import random
import array
from pathlib import Path
import pygame

# ---------------------------------------------------------------------------
# Global constants -- screen size, physics, world IDs
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 500          # window dimensions in pixels
GROUND_Y = 440                    # y-coordinate of the ground surface

# World / dimension identifiers and tags (E1)
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

# Game feel constants (P1.1)
COYOTE_FRAMES       = 6
JUMP_BUFFER_FRAMES  = 6
INVULN_FRAMES       = 60          # P1.2 invulnerability after respawn

# Swap feedback constants
SWAP_COOLDOWN_MS = 300            # milliseconds before player can swap again
FLASH_FRAMES     = 8              # how many frames the swap white-flash lasts

# Screen-shake constants (visual only)
SHAKE_FRAMES = 10                 # frames of shake after a swap
SHAKE_MAG    = 5                  # maximum pixel offset during shake

# Particle constants (visual only)
PARTICLE_COUNT = 22               # particles spawned per successful swap
PARTICLE_LIFE  = 35               # max lifetime of each particle in frames


# ---------------------------------------------------------------------------
# Audio Synthesizer (P1.3 - procedurally generated sound effects)
# ---------------------------------------------------------------------------
AUDIO_MUTED = False
SOUNDS = {}

def init_audio():
    """Synthesize short sound effects procedurally without external files."""
    global AUDIO_MUTED, SOUNDS
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    except Exception:
        AUDIO_MUTED = True
        return

    def _make_sound(generator_fn, duration_sec):
        sample_rate = 22050
        n_samples = int(sample_rate * duration_sec)
        buf = array.array('h')
        for i in range(n_samples):
            t = i / sample_rate
            val = generator_fn(t, duration_sec)
            val = max(-32767, min(32767, int(val * 32767)))
            buf.append(val)
        try:
            snd = pygame.mixer.Sound(buffer=buf)
            snd.set_volume(0.3)
            return snd
        except Exception:
            return None

    # Sound generators
    SOUNDS["jump"] = _make_sound(lambda t, dur: math.sin(2 * math.pi * (300 + t * 400) * t) * (1 - t/dur), 0.12)
    SOUNDS["swap"] = _make_sound(lambda t, dur: math.sin(2 * math.pi * (200 + t * 800) * t) * (1 - t/dur), 0.15)
    SOUNDS["blocked"] = _make_sound(lambda t, dur: (1 if math.sin(2 * math.pi * 120 * t) > 0 else -1) * 0.4 * (1 - t/dur), 0.12)
    SOUNDS["hit"] = _make_sound(lambda t, dur: (random.uniform(-1, 1)) * (1 - t/dur) * 0.7, 0.2)
    SOUNDS["plate"] = _make_sound(lambda t, dur: math.sin(2 * math.pi * 500 * t) * (1 - t/dur), 0.06)
    SOUNDS["win"] = _make_sound(lambda t, dur: math.sin(2 * math.pi * (400 if t < 0.1 else 600 if t < 0.2 else 800) * t) * (1 - t/dur), 0.3)


def play_sound(name):
    """Play a procedural sound effect if audio is active and unmuted."""
    if AUDIO_MUTED or not pygame.mixer.get_init():
        return
    snd = SOUNDS.get(name)
    if snd:
        try:
            snd.play()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Level data (Section 4 + Level 6 Warden)
# ---------------------------------------------------------------------------
F = (pygame.Rect(0, 440, 800, 60), BOTH)   # standard floor in every level

LEVELS = [
    # -- Level 1: Walls Aren't Real -----------------------------------------
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
        "wardens":   [],
        "spikes":    [(pygame.Rect(420, 424, 220, 16), CHAOS)],   # floor spikes, Chaos only
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(720, 390, 30, 50),
    },
    # -- Level 2: Stairway Between Worlds -----------------------------------
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
        "wardens":   [],
        "spikes":    [],
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(740, 70, 30, 50),
    },
    # -- Level 3: Push It ---------------------------------------------------
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
        "wardens":   [],
        "spikes":    [],
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(740, 250, 30, 50),
    },
    # -- Level 4: Hold the Door ---------------------------------------------
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
        "wardens":   [],
        "spikes":    [],
        "gate":      pygame.Rect(560, 290, 20, 150),          # solid in both worlds while closed
        "plate":     {"rect": pygame.Rect(300, 436, 60, 4), "world": CHAOS},
        "door":      pygame.Rect(720, 390, 30, 50),
    },
    # -- Level 5: Overtime --------------------------------------------------
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
        "wardens":   [],
        "spikes":    [],
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(750, 130, 30, 50),            # sits on RP
    },
    # -- Level 6: Night Watch (P3 - Warden AI) ------------------------------
    {
        "name":      "Night Watch",
        "hint":      "The Warden only sees you in Chaos. Reality is your hiding place.",
        "spawn":     (60, 400),
        "platforms": [
            F,
            (pygame.Rect(300, 300, 30, 140), REAL),       # Reality-only partition
        ],
        "anchor":    None,
        "pests":     [],
        "wardens":   [{"patrol_min": 420, "patrol_max": 560, "leash_min": 340, "leash_max": 600}],
        "spikes":    [],
        "gate":      None,
        "plate":     None,
        "door":      pygame.Rect(720, 390, 30, 50),
    },
]


# ---------------------------------------------------------------------------
# Colour palettes
# ---------------------------------------------------------------------------
BG_TOP = ((18, 26, 44),  (42, 8, 68))
BG_BOT = ((48, 56, 76),  (68, 20, 100))

COL_GROUND     = ((62, 70, 88),   (90, 38, 125))
COL_LEDGE_FACE = ((135, 142, 158), (155, 95, 188))
COL_LEDGE_EDGE = ((95, 102, 118), (115, 65, 148))

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

COL_PLAYER_UNI = (52, 96, 170)
COL_PLAYER_CHO = (115, 55, 185)
COL_PLAYER_SKIN= (238, 196, 156)


# ---------------------------------------------------------------------------
# Sprite asset cache
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
# Background gradient cache
# ---------------------------------------------------------------------------
_BG_SURFS = [None, None]


def _make_gradient(w, h, top, bot):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))
    return surf


# ===========================================================================
# DRAWING FUNCTIONS
# ===========================================================================

def draw_background(surf, dim, tick, level=None):
    if _BG_SURFS[dim] is None:
        _BG_SURFS[dim] = _make_gradient(WIDTH, HEIGHT, BG_TOP[dim], BG_BOT[dim])
    surf.blit(_BG_SURFS[dim], (0, 0))
    if dim == REALITY:
        _draw_reality_decor(surf, tick, level)
    else:
        _draw_chaos_decor(surf, tick)


def _draw_reality_decor(surf, tick, level=None):
    """Corporate Reality decorations with P0.4 spawn/interactable filtering."""
    for lx in (80, 265, 445, 620):
        pygame.draw.rect(surf, (46, 52, 66), (lx - 3, 0, 86, 8))
        pygame.draw.rect(surf, (232, 238, 208), (lx, 0, 80, 5))
        glow = pygame.Surface((80, 28), pygame.SRCALPHA)
        glow.fill((232, 238, 208, 32))
        surf.blit(glow, (lx, 5))

    for cx in range(0, WIDTH, 60):
        pygame.draw.line(surf, (28, 34, 48), (cx, 0), (cx, 38), 1)
    pygame.draw.line(surf, (28, 34, 48), (0, 38), (WIDTH, 38), 1)

    pygame.draw.rect(surf, (44, 50, 64), (0, GROUND_Y - 7, WIDTH, 7))

    # P0.4 Desk safety checks: avoid overlap with level objects and spawn
    blocked_rects = []
    if level:
        sx, sy = level.get("spawn", (60, 400))
        blocked_rects.append(pygame.Rect(sx, sy, 28, 40).inflate(60, 60))
        blocked_rects.append(level["door"].inflate(60, 60))
        for p, _ in level.get("platforms", []):
            if p.y < GROUND_Y:
                blocked_rects.append(p.inflate(30, 30))

    for dx in (30, 535):
        desk_rect = pygame.Rect(dx, GROUND_Y - 86, 100, 86)
        if not any(desk_rect.colliderect(br) for br in blocked_rects):
            _draw_desk(surf, dx, GROUND_Y)

    # Poster
    pygame.draw.rect(surf, (68, 74, 90), (468, GROUND_Y - 205, 64, 84))
    pygame.draw.rect(surf, (78, 84, 100), (473, GROUND_Y - 200, 54, 64))
    for iy in range(4):
        pygame.draw.rect(surf, (92, 98, 115), (476, GROUND_Y - 196 + iy * 14, 48 - iy * 8, 6))


def _draw_desk(surf, x, ground_y):
    pygame.draw.rect(surf, (48, 36, 24), (x, ground_y - 40, 100, 10))
    pygame.draw.rect(surf, (62, 48, 34), (x, ground_y - 42, 100, 4))
    pygame.draw.rect(surf, (36, 26, 16), (x + 6,  ground_y - 30, 8, 30))
    pygame.draw.rect(surf, (36, 26, 16), (x + 86, ground_y - 30, 8, 30))
    pygame.draw.rect(surf, (22, 28, 44), (x + 28, ground_y - 86, 44, 36))
    pygame.draw.rect(surf, (36, 152, 228), (x + 31, ground_y - 83, 38, 26))
    for il in range(3):
        pygame.draw.rect(surf, (80, 196, 255), (x + 34, ground_y - 80 + il * 7, 24 - il * 4, 3))
    pygame.draw.rect(surf, (36, 36, 44), (x + 46, ground_y - 50, 8, 10))
    pygame.draw.rect(surf, (36, 36, 44), (x + 40, ground_y - 42, 20, 4))


def _draw_chaos_decor(surf, tick):
    """Chaos background decor (P0.3: filled low-alpha shapes, no faint outlines)."""
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

    orbs = [
        (138, 218, 20, (158, 58, 208)),
        (438, 158, 14, (98,  48, 192)),
        (668, 238, 18, (188, 78, 242)),
        (288, 128, 11, (138, 38, 188)),
        (568, 188, 10, (168, 58, 232)),
    ]
    for ox, oy, r, col in orbs:
        float_y = int(oy + 9 * math.sin(ox * 0.04 + tick * 0.025))
        halo = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*col, 30), (r * 3, r * 3), r * 3)
        surf.blit(halo, (ox - r * 3, float_y - r * 3))
        pygame.draw.circle(surf, col, (ox, float_y), r)

    # Filled low-alpha polygons (no outlines)
    poly_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for tx, ty, size, col, spd in [
        (192, 308, 22, (98, 28, 148, 35), 0.018),
        (548, 208, 17, (88, 22, 138, 35), 0.025),
        (712, 348, 13, (118, 38, 162, 35), 0.032),
    ]:
        angle = tick * spd + tx * 0.01
        pts = [(int(tx + size * math.cos(angle + i * 2 * math.pi / 3)),
                int(ty + size * math.sin(angle + i * 2 * math.pi / 3)))
               for i in range(3)]
        pygame.draw.polygon(poly_surf, col, pts)
    surf.blit(poly_surf, (0, 0))

    mist = pygame.Surface((WIDTH, 28), pygame.SRCALPHA)
    mist.fill((108, 38, 158, 38))
    surf.blit(mist, (0, GROUND_Y - 28))


def draw_ground(surf, dim):
    col  = COL_GROUND[dim]
    hi   = tuple(min(c + 28, 255) for c in col)
    crack= tuple(max(c - 18, 0)   for c in col)
    pygame.draw.rect(surf, col, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surf, hi,    (0, GROUND_Y),     (WIDTH, GROUND_Y),     2)
    pygame.draw.line(surf, hi,    (0, GROUND_Y + 2), (WIDTH, GROUND_Y + 2), 1)
    for cx in range(28, WIDTH, 56):
        pygame.draw.line(surf, crack, (cx, GROUND_Y + 4), (cx, GROUND_Y + 14), 1)


def draw_ledge(surf, dim, ledge_rect):
    pygame.draw.rect(surf, COL_GROUND[dim], ledge_rect)
    pygame.draw.rect(surf, COL_LEDGE_FACE[dim], (ledge_rect.x, ledge_rect.y, ledge_rect.w, 4))
    pygame.draw.rect(surf, COL_LEDGE_EDGE[dim], (ledge_rect.x, ledge_rect.bottom - 3, ledge_rect.w, 3))


def draw_wall(surf, wall_rect, dim=REALITY):
    if dim == REALITY:
        pygame.draw.rect(surf, COL_WALL_MAIN, wall_rect)
        pygame.draw.rect(surf, COL_WALL_HI, (wall_rect.left, wall_rect.top, 3, wall_rect.h))
        pygame.draw.rect(surf, COL_WALL_SH, (wall_rect.right - 3, wall_rect.top, 3, wall_rect.h))
        pygame.draw.rect(surf, COL_WALL_HI, (wall_rect.x, wall_rect.y, wall_rect.w, 5))
        for sy in range(wall_rect.top + 38, wall_rect.bottom - 5, 42):
            pygame.draw.line(surf, COL_WALL_SH, (wall_rect.left + 3, sy), (wall_rect.right - 3, sy), 1)
    else:
        pygame.draw.rect(surf, (85, 38, 122), wall_rect)
        pygame.draw.rect(surf, (155, 78, 205), (wall_rect.left, wall_rect.top, 3, wall_rect.h))
        pygame.draw.rect(surf, (48, 18, 72), (wall_rect.right - 3, wall_rect.top, 3, wall_rect.h))
        pygame.draw.rect(surf, (155, 78, 205), (wall_rect.x, wall_rect.y, wall_rect.w, 5))


def draw_ghost_rect(surf, rect, obj_world, tick=0):
    """Draw a readable dashed, pulsing ghost outline for objects in the other dimension (P0.2)."""
    base_col = (115, 175, 245) if obj_world == REAL else (205, 115, 250)
    pulse = int(30 * math.sin(tick * 0.08))
    alpha = max(100, min(200, 150 + pulse))

    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    # Faint shape fill
    s.fill((*base_col, 25))

    # Pulsing dashed border
    dash_length = 6
    border_color = (*base_col, alpha)
    # Horizontal borders
    for x in range(0, rect.w, dash_length * 2):
        w = min(dash_length, rect.w - x)
        pygame.draw.rect(s, border_color, (x, 0, w, 2))
        pygame.draw.rect(s, border_color, (x, rect.h - 2, w, 2))
    # Vertical borders
    for y in range(0, rect.h, dash_length * 2):
        h = min(dash_length, rect.h - y)
        pygame.draw.rect(s, border_color, (0, y, 2, h))
        pygame.draw.rect(s, border_color, (rect.w - 2, y, 2, h))

    surf.blit(s, rect.topleft)


def draw_spike_strip(surf, rect, dim, is_ghost=False, tick=0):
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
        base_col = (205, 115, 250) if dim == CHAOS else (115, 175, 245)
        pulse = int(30 * math.sin(tick * 0.08))
        alpha = max(100, min(200, 150 + pulse))
        ghost_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)

        for i in range(count):
            x0 = int(i * actual_w)
            x1 = int((i + 0.5) * actual_w)
            x2 = int((i + 1) * actual_w)
            pts = [(x0, rect.h), (x1, 0), (x2, rect.h)]
            pygame.draw.polygon(ghost_surf, (*base_col, alpha), pts, 2)
        surf.blit(ghost_surf, rect.topleft)
    else:
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


def draw_pressure_plate(surf, plate_rect, plate_world, pressed):
    pr = plate_rect
    if pressed and "pressure_plate_glow" in ASSETS:
        sprite = ASSETS["pressure_plate_glow"]
        surf.blit(sprite, (pr.x, pr.bottom - sprite.get_height()))
        return
    elif not pressed and "pressure_plate" in ASSETS:
        surf.blit(ASSETS["pressure_plate"], pr.topleft)
        return

    if pressed:
        glow_col = (90, 255, 210) if plate_world == CHAOS else (255, 225, 70)
        depressed_rect = pygame.Rect(pr.x, pr.bottom - 2, pr.w, 2)
        pygame.draw.rect(surf, glow_col, depressed_rect)
        glow = pygame.Surface((pr.w + 16, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*glow_col, 75), (0, 0, pr.w + 16, 12))
        surf.blit(glow, (pr.x - 8, pr.bottom - 8))
    else:
        base_col = (112, 52, 155) if plate_world == CHAOS else (72, 92, 132)
        hi_col   = (192, 112, 245) if plate_world == CHAOS else (122, 162, 225)
        pygame.draw.rect(surf, base_col, pr)
        pygame.draw.rect(surf, hi_col, (pr.x, pr.y, pr.w, 1))
        dot_col = (255, 180, 80) if plate_world == CHAOS else (160, 210, 255)
        pygame.draw.circle(surf, dot_col, (pr.centerx, pr.centery), 2)


def draw_gate(surf, gate_rect, dim, pressed):
    if pressed and "gate_open" in ASSETS:
        surf.blit(ASSETS["gate_open"], gate_rect.topleft)
        return
    elif not pressed and "gate_closed" in ASSETS:
        surf.blit(ASSETS["gate_closed"], gate_rect.topleft)
        return

    if pressed:
        open_surf = pygame.Surface((gate_rect.w, gate_rect.h), pygame.SRCALPHA)
        open_surf.fill((40, 220, 120, 35))
        pygame.draw.rect(open_surf, (80, 255, 160, 90), (0, 0, gate_rect.w, gate_rect.h), 1)
        surf.blit(open_surf, gate_rect.topleft)
        pygame.draw.rect(surf, (42, 50, 62), (gate_rect.x, gate_rect.y, gate_rect.w, 8))
        pygame.draw.circle(surf, (80, 255, 130), (gate_rect.centerx, gate_rect.y + 4), 3)
    else:
        body_col = (54, 60, 72) if dim == REALITY else (72, 34, 92)
        bar_col  = (86, 96, 116) if dim == REALITY else (122, 64, 152)
        pygame.draw.rect(surf, body_col, gate_rect)
        for gx in range(gate_rect.left + 4, gate_rect.right - 2, 6):
            pygame.draw.line(surf, bar_col, (gx, gate_rect.top + 8), (gx, gate_rect.bottom - 8), 2)
        pygame.draw.rect(surf, (38, 42, 52), (gate_rect.x, gate_rect.y, gate_rect.w, 10))
        pygame.draw.rect(surf, (38, 42, 52), (gate_rect.x, gate_rect.bottom - 10, gate_rect.w, 10))
        pygame.draw.circle(surf, (255, 55, 55), (gate_rect.centerx, gate_rect.y + 5), 3)
        pygame.draw.circle(surf, (255, 55, 55), (gate_rect.centerx, gate_rect.bottom - 5), 3)


def draw_intro_card(surf, font, big, g):
    level = g["level"]
    name = level.get("name", f"Level {g['level_index'] + 1}")
    hint = level.get("hint", "")
    card_w, card_h = 580, 110
    card_x = (WIDTH - card_w) // 2
    card_y = (HEIGHT - card_h) // 2

    alpha = min(225, int(225 * (g["intro_timer"] / 20))) if g["intro_timer"] < 20 else 225
    card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    card.fill((12, 16, 28, alpha))
    pygame.draw.rect(card, (115, 145, 215, min(255, alpha + 30)), (0, 0, card_w, card_h), 2)
    surf.blit(card, (card_x, card_y))

    title_text = f"Level {g['level_index'] + 1}: {name}"
    title_sh = font.render(title_text, True, (40, 45, 60))
    title_surf = font.render(title_text, True, (255, 225, 95))
    surf.blit(title_sh, (card_x + 23, card_y + 19))
    surf.blit(title_surf, (card_x + 22, card_y + 18))

    hint_surf = font.render(hint, True, (215, 230, 250))
    surf.blit(hint_surf, (card_x + 22, card_y + 50))

    dismiss_surf = font.render("(Press any key to dismiss)", True, (135, 150, 175))
    surf.blit(dismiss_surf, (card_x + card_w - dismiss_surf.get_width() - 20, card_y + 80))


def draw_cabinet(surf, level, anchor_x):
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

    pygame.draw.rect(surf, COL_CABINET, r)
    pygame.draw.rect(surf, (185, 190, 200), (r.left, r.top, 3, r.h))
    pygame.draw.rect(surf, (118, 123, 133), (r.right - 3, r.top, 3, r.h))
    pygame.draw.rect(surf, (175, 180, 190), (r.left, r.top, r.w, 4))
    dh = (r.h - 10) // 3
    for i in range(3):
        dy = r.top + 6 + i * (dh + 2)
        pygame.draw.rect(surf, (142, 147, 158), (r.left + 4, dy, r.w - 8, dh))
        pygame.draw.line(surf, (115, 120, 130), (r.left + 4, dy + dh - 1), (r.right - 4, dy + dh - 1), 1)
        hx = r.left + r.w // 2 - 6
        hy = dy + dh // 2 - 2
        pygame.draw.rect(surf, (95, 100, 110), (hx, hy, 12, 4))
        pygame.draw.rect(surf, (168, 173, 183), (hx + 1, hy + 1, 10, 2))


def draw_pillar(surf, level, anchor_x):
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

    pygame.draw.rect(surf, COL_PILLAR, r)
    pygame.draw.rect(surf, (158, 132, 98), (r.left, r.top, 5, r.h))
    pygame.draw.rect(surf, (96, 76, 52), (r.right - 5, r.top, 5, r.h))
    for by in range(r.top + 22, r.bottom - 5, 22):
        pygame.draw.line(surf, (106, 84, 60), (r.left + 3, by), (r.right - 3, by), 2)
    pygame.draw.line(surf, (96, 76, 52), (r.left + 8, r.top + 8), (r.left + 20, r.top + 34), 1)
    pygame.draw.line(surf, (96, 76, 52), (r.left + 22, r.top + 52), (r.left + 30, r.top + 78), 1)
    pygame.draw.rect(surf, (152, 128, 92), (r.left, r.top, r.w, 5))


def draw_door(surf, door_rect, tick):
    pulse  = int(4 * math.sin(tick * 0.12))
    g_rect = door_rect.inflate(8 + pulse, 8 + pulse)
    glow   = pygame.Surface((g_rect.w, g_rect.h), pygame.SRCALPHA)
    glow.fill((255, 230, 100, 70))
    surf.blit(glow, g_rect.topleft)

    if "exit_door" in ASSETS:
        surf.blit(ASSETS["exit_door"], door_rect.topleft)
        return

    pygame.draw.rect(surf, COL_DOOR_FRAME, door_rect.inflate(6, 6))
    pygame.draw.rect(surf, COL_DOOR_BODY, door_rect)
    win = pygame.Rect(door_rect.x + 4, door_rect.y + 4, door_rect.w - 8, door_rect.h // 2 - 4)
    pygame.draw.rect(surf, COL_DOOR_WIN, win)
    pygame.draw.rect(surf, COL_DOOR_BODY, win.inflate(-4, -4))
    lo = pygame.Rect(door_rect.x + 4, door_rect.y + door_rect.h // 2 + 2, door_rect.w - 8, door_rect.h // 2 - 6)
    pygame.draw.rect(surf, (COL_DOOR_FRAME[0] - 20, COL_DOOR_FRAME[1] - 20, max(COL_DOOR_FRAME[2] - 10, 0)), lo)
    pygame.draw.circle(surf, (178, 138, 18), (door_rect.right - 7, door_rect.centery), 3)
    pygame.draw.circle(surf, (220, 188, 58), (door_rect.right - 8, door_rect.centery - 1), 2)


def draw_player(surf, player_rect, dim, tick, facing_right=True, invuln=0):
    """Draw custodian player with P1.2 invulnerability blinking."""
    if invuln > 0 and (invuln // 4) % 2 == 1:
        return  # Blink invisible every other 4 frames

    pr = player_rect
    cx = pr.centerx

    if dim == CHAOS:
        aura = pygame.Surface((pr.w + 20, pr.h + 20), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (*COL_PLAYER_CHO, 48), (0, 0, pr.w + 20, pr.h + 20))
        surf.blit(aura, (pr.left - 10, pr.top - 10))

    sprite_key = "custodian_reality" if dim == REALITY else "custodian_chaos"
    if not facing_right:
        sprite_key += "_mirrored"
    if sprite_key in ASSETS:
        surf.blit(ASSETS[sprite_key], pr.topleft)
        return

    uni  = COL_PLAYER_UNI if dim == REALITY else COL_PLAYER_CHO
    uni_hi = tuple(min(c + 24, 255) for c in uni)
    uni_sh = tuple(max(c - 30, 0)   for c in uni)

    pygame.draw.rect(surf, uni_sh, (pr.left + 5, pr.bottom - 14, pr.w - 10, 14))
    pygame.draw.rect(surf, (28, 28, 34), (pr.left + 2,       pr.bottom - 5, 10, 5))
    pygame.draw.rect(surf, (28, 28, 34), (pr.right - 12,     pr.bottom - 5, 10, 5))

    pygame.draw.rect(surf, uni,    (pr.left + 3, pr.top + 12, pr.w - 6, pr.h - 24))
    pygame.draw.rect(surf, uni_hi, (pr.left + 3, pr.top + 12, 3, pr.h - 24))
    pygame.draw.rect(surf, uni_sh, (pr.right - 6, pr.top + 12, 3, pr.h - 24))
    pygame.draw.rect(surf, uni_sh, (pr.left + 3, pr.centery - 2, pr.w - 6, 3))
    pygame.draw.rect(surf, (192, 196, 208), (cx - 5, pr.top + 15, 10, 6))

    pygame.draw.rect(surf, uni_sh, (pr.left - 2,  pr.top + 14, 6, 12))
    pygame.draw.rect(surf, uni_sh, (pr.right - 4, pr.top + 14, 6, 12))

    hcy = pr.top + 8
    pygame.draw.circle(surf, COL_PLAYER_SKIN, (cx, hcy), 9)

    pygame.draw.rect(surf, uni_sh, (cx - 10, hcy - 9, 20, 6))
    pygame.draw.rect(surf, uni,    (cx - 8,  hcy - 7, 16, 5))
    pygame.draw.rect(surf, uni_sh, (cx - 12, hcy - 3, 5, 3))

    for ex in (cx - 3, cx + 3):
        pygame.draw.circle(surf, (34, 28, 24), (ex, hcy + 2), 2)
        pygame.draw.circle(surf, (220, 220, 232), (ex, hcy + 1), 1)


def draw_pest(surf, pest, tick):
    px  = int(pest["x"])
    bob = int(2 * math.sin(tick * 0.15 + px * 0.05))
    py  = GROUND_Y - 24 + bob
    cy  = py + 9

    if "pest" in ASSETS:
        sprite = ASSETS["pest"]
        if pest.get("dir", 1) > 0:
            surf.blit(pygame.transform.flip(sprite, True, False), (px, py))
        else:
            surf.blit(sprite, (px, py))
        return

    pygame.draw.ellipse(surf, COL_PEST_BODY, (px, py, 30, 18))
    pygame.draw.ellipse(surf, (228, 75, 75), (px + 3, py + 2, 13, 7))

    for i, lx in enumerate((px + 5, px + 13, px + 21)):
        pygame.draw.line(surf, (162, 38, 38), (lx, cy), (lx - 6, cy + 8), 1)
        pygame.draw.line(surf, (162, 38, 38), (lx, cy), (lx - 6, cy - 6), 1)

    pygame.draw.line(surf, (188, 48, 48), (px + 6, py + 2), (px - 2, py - 6), 1)
    pygame.draw.line(surf, (188, 48, 48), (px + 11, py + 2), (px + 9, py - 7), 1)
    pygame.draw.circle(surf, (255, 96, 96), (px - 2, py - 6), 2)
    pygame.draw.circle(surf, (255, 96, 96), (px + 9, py - 7), 2)

    for ex in (px + 5, px + 14):
        pygame.draw.circle(surf, COL_PEST_EYE, (ex, cy - 2), 3)
        pygame.draw.circle(surf, (38, 18, 8),  (ex + 1, cy - 2), 1)


def draw_warden(surf, warden, font, tick):
    """Draw Warden enemy (P3 - Task 2) with distinct state visual feedback."""
    wx = int(warden["x"])
    wy = GROUND_Y - 28
    w_rect = pygame.Rect(wx, wy, 36, 28)
    state = warden["state"]

    # Visual state styling
    if state == "PATROL":
        body_col = (230, 140, 30)      # Orange
        eye_col  = (255, 230, 100)
    elif state == "CHASE":
        body_col = (230, 30, 30)       # Bright Red
        eye_col  = (255, 255, 200)
    else:  # RETURN
        body_col = (130, 110, 120)     # Dimmed / Greyed
        eye_col  = (180, 180, 180)

    # Body
    pygame.draw.ellipse(surf, body_col, w_rect)
    pygame.draw.ellipse(surf, (min(255, body_col[0] + 40), min(255, body_col[1] + 40), min(255, body_col[2] + 40)),
                        (wx + 4, wy + 3, 16, 8))

    # Glowing eyes
    for ex in (wx + 8, wx + 20):
        pygame.draw.circle(surf, eye_col, (ex, wy + 10), 3)
        pygame.draw.circle(surf, (20, 10, 10), (ex + (1 if warden.get("dir", 1) > 0 else -1), wy + 10), 1)

    # Alert "!" when spotted
    if warden["alert_timer"] > 0:
        alert = font.render("!", True, (255, 50, 50))
        surf.blit(alert, (wx + 14, wy - 22))


def draw_pests(surf, g, font, tick):
    if g["dim"] != CHAOS:
        return
    for pest in g["pests"]:
        draw_pest(surf, pest, tick)
    for warden in g["wardens"]:
        draw_warden(surf, warden, font, tick)


def _spawn_particles(g):
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
            "vy":       math.sin(angle) * speed - 1.5,
            "life":     life,
            "max_life": life,
            "col":      random.choice(colours),
            "size":     random.randint(2, 5),
        })


def _spawn_hit_particles(g):
    """P1.2 Hit particle burst."""
    cx, cy = g["player"].centerx, g["player"].centery
    for _ in range(16):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 6.0)
        g["particles"].append({
            "x":        float(cx),
            "y":        float(cy),
            "vx":       math.cos(angle) * speed,
            "vy":       math.sin(angle) * speed,
            "life":     20,
            "max_life": 20,
            "col":      (255, 60, 60),
            "size":     random.randint(3, 6),
        })


def _update_particles(g):
    alive = []
    for p in g["particles"]:
        p["x"]  += p["vx"]
        p["y"]  += p["vy"]
        p["vy"] += 0.15
        p["life"] -= 1
        if p["life"] > 0:
            alive.append(p)
    g["particles"] = alive


def draw_particles(surf, particles):
    for p in particles:
        if p["life"] <= 0:
            continue
        frac  = p["life"] / p["max_life"]
        alpha = int(255 * frac)
        size  = max(1, int(p["size"] * frac))
        d = size * 2 + 2
        circle_surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(circle_surf, (*p["col"], alpha), (size + 1, size + 1), size)
        surf.blit(circle_surf, (int(p["x"]) - size - 1, int(p["y"]) - size - 1))


def draw_hud(surf, font, g):
    panel_w, panel_h = 205, 172
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((8, 8, 18, 168))
    pygame.draw.rect(panel, (88, 112, 175, 170), (0, 0, panel_w, panel_h), 1)
    surf.blit(panel, (6, 6))

    dot_key = "world_dot_chaos" if g["dim"] == CHAOS else "world_dot_reality"
    if dot_key in ASSETS:
        surf.blit(ASSETS[dot_key], (10, 10))
    else:
        dot_col = (75, 155, 252) if g["dim"] == REALITY else (198, 75, 252)
        pygame.draw.circle(surf, dot_col,         (18, 22), 5)
        pygame.draw.circle(surf, (255, 255, 255), (18, 22), 5, 1)

    world = "Corporate Reality" if g["dim"] == REALITY else "Surreal Chaos"
    surf.blit(font.render(world, True, (205, 218, 242)), (36, 14))

    pygame.draw.line(surf, (58, 78, 128), (10, 37), (205, 37), 1)

    surf.blit(font.render(f"Score  {int(g['score'])}", True, (195, 228, 255)), (12, 44))

    level_str = f"Level  {g['level_index'] + 1} / {len(LEVELS)}"
    surf.blit(font.render(level_str, True, (195, 228, 255)), (12, 70))

    # P2.1 Display Level Time in HUD
    secs = int(g["seconds_on_level"])
    surf.blit(font.render(f"Time   {secs}s", True, (195, 228, 255)), (12, 94))

    # Lives
    surf.blit(font.render("Lives", True, (195, 228, 255)), (12, 118))
    if "heart_full" in ASSETS and "heart_empty" in ASSETS:
        for i in range(3):
            h_key = "heart_full" if i < g["lives"] else "heart_empty"
            surf.blit(ASSETS[h_key], (70 + i * 26, 114))
    else:
        for i in range(g["lives"]):
            hx = 82 + i * 24
            pygame.draw.circle(surf, (218, 55, 78), (hx + 5, 126), 7)
            pygame.draw.circle(surf, (252, 98, 118), (hx + 3, 123), 3)

    surf.blit(font.render(f"Best   {g['high_score']}", True, (175, 198, 228)), (12, 144))

    # Bottom hints with mute & pause notes
    mute_txt = " (Muted)" if AUDIO_MUTED else ""
    hint = font.render(f"SPACE swap  |  ESC pause  |  M mute{mute_txt}", True, (128, 140, 162))
    surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 24))


def draw_title(surf, font, big, tick):
    """P0.1 Title screen text fitting & prompt formatting."""
    if "title_background" in ASSETS:
        surf.blit(ASSETS["title_background"], (0, 0))
    else:
        t   = (math.sin(tick * 0.008) + 1) / 2
        r   = int(18 * (1 - t) + 42 * t)
        g   = int(26 * (1 - t) + 8  * t)
        b   = int(44 * (1 - t) + 68 * t)
        surf.fill((r, g, b))

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

    if "logo_wordmark" in ASSETS:
        logo = ASSETS["logo_wordmark"]
        surf.blit(logo, ((WIDTH - logo.get_width()) // 2, 42))
    else:
        title_y = HEIGHT // 2 - 105
        shadow  = big.render("SHIFT  WORK", True, (75, 38, 118))
        title   = big.render("SHIFT  WORK", True, (255, 255, 255))
        surf.blit(shadow, (WIDTH // 2 - title.get_width() // 2 + 3, title_y + 3))
        surf.blit(title,  (WIDTH // 2 - title.get_width() // 2,     title_y))

    sub = font.render("A 2D Dimension-Swapping Platformer", True, (195, 180, 235))
    surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 145))

    # P0.1 Dynamically sized control panel
    lines = [
        "WASD / Arrows -- Move and Jump",
        "SPACE -- Swap worlds",
        "R -- Restart  |  ESC -- Quit",
    ]
    panel_w = max(font.size(line)[0] for line in lines) + 40
    panel_h = 120
    panel_x = (WIDTH - panel_w) // 2
    panel_y = 195
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((10, 14, 26, 170))
    pygame.draw.rect(panel, (90, 115, 175, 160), (0, 0, panel_w, panel_h), 1)
    surf.blit(panel, (panel_x, panel_y))

    for i, line in enumerate(lines):
        rendered = font.render(line, True, (195, 215, 240))
        surf.blit(rendered, (panel_x + 20, panel_y + 16 + i * 32))

    # P0.1 Blinking prompt
    if (tick // 28) % 2 == 0:
        prompt = font.render("Press any key to start", True, (255, 235, 130))
        surf.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT - 52))


def draw_end_screen(surf, font, big, g):
    """P2.2 Retrying game over overlay."""
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

    score_s = font.render(f"Final score: {int(g['score'])}   Best: {g['high_score']}", True, (255, 255, 255))
    surf.blit(score_s, (WIDTH // 2 - score_s.get_width() // 2, 218))

    if g["state"] == "lose":
        restart_s = font.render("R: retry this level   N: new game", True, (188, 205, 232))
    else:
        restart_s = font.render("Press R to start new shift", True, (188, 205, 232))
    surf.blit(restart_s, (WIDTH // 2 - restart_s.get_width() // 2, 258))


def draw_pause_screen(surf, font, big):
    """P1.4 Pause screen overlay."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))

    t = big.render("PAUSED", True, (255, 255, 255))
    surf.blit(t, (WIDTH // 2 - t.get_width() // 2, 160))

    sub = font.render("ESC: resume   |   R: restart level   |   Q: quit", True, (200, 220, 255))
    surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 230))


def draw(surf, font, big, g, tick):
    dim   = g["dim"]
    level = g["level"]

    draw_background(surf, dim, tick, level)
    draw_ground(surf, dim)

    for rect, tag in level.get("platforms", []):
        if rect.y >= GROUND_Y and rect.w >= WIDTH:
            continue
        if is_tag_active(tag, dim):
            if rect.h >= 50 and rect.w <= 50:
                draw_wall(surf, rect, dim)
            else:
                draw_ledge(surf, dim, rect)
        else:
            draw_ghost_rect(surf, rect, tag, tick)

    for spike_rect, s_world in level.get("spikes", []):
        if is_tag_active(s_world, dim):
            draw_spike_strip(surf, spike_rect, dim, is_ghost=False, tick=tick)
        else:
            draw_spike_strip(surf, spike_rect, s_world, is_ghost=True, tick=tick)

    pressed = is_plate_pressed(level, dim, g["player"], g.get("anchor_x"))
    if level.get("plate") is not None:
        pr = level["plate"]["rect"]
        pw = level["plate"]["world"]
        if is_tag_active(pw, dim):
            draw_pressure_plate(surf, pr, pw, pressed)
        else:
            draw_ghost_rect(surf, pr, pw, tick)

    if level.get("gate") is not None:
        draw_gate(surf, level["gate"], dim, pressed)

    draw_door(surf, level["door"], tick)

    if level.get("anchor") is not None and g.get("anchor_x") is not None:
        if dim == REALITY:
            draw_cabinet(surf, level, g["anchor_x"])
        else:
            draw_pillar(surf, level, g["anchor_x"])

    draw_pests(surf, g, font, tick)

    # Custodian player (P1.2 invulnerability blinking)
    draw_player(surf, g["player"], dim, tick, g.get("facing_right", True), g.get("invuln", 0))

    draw_particles(surf, g["particles"])
    draw_hud(surf, font, g)

    if g["msg_timer"] > 0:
        msg = font.render("Can't swap -- something solid is in the way!", True, (255, 218, 98))
        surf.blit(msg, (12, 184))

    if g["intro_timer"] > 0 and g["state"] == "play":
        draw_intro_card(surf, font, big, g)

    # P1.2 Red hit flash overlay
    if g.get("hit_flash", 0) > 0:
        flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash_surf.fill((255, 0, 0, 90))
        surf.blit(flash_surf, (0, 0))

    if g["state"] == "pause":
        draw_pause_screen(surf, font, big)
    elif g["state"] != "play":
        draw_end_screen(surf, font, big, g)

    if g["flash_frames"] > 0:
        alpha = int(200 * g["flash_frames"] / FLASH_FRAMES)
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        surf.blit(flash, (0, 0))


# ===========================================================================
# GAME LOGIC
# ===========================================================================

def is_plate_pressed(level, dim, player_rect, anchor_x):
    plate = level.get("plate")
    if not plate:
        return False
    pr = plate["rect"]
    pw = plate["world"]

    if level.get("anchor") is not None and anchor_x is not None:
        dim_for_plate = CHAOS if pw == CHAOS else REALITY
        a = anchor_rect(level, dim_for_plate, anchor_x)
        if a is not None and a.colliderect(pr):
            return True

    if is_tag_active(pw, dim) and player_rect.colliderect(pr):
        return True

    return False


def static_solids(level, dim, plate_pressed=False):
    solids = [rect for rect, tag in level.get("platforms", []) if is_tag_active(tag, dim)]
    if level.get("gate") is not None and not plate_pressed:
        solids.append(level["gate"])
    return solids


def anchor_rect(level, dim, x):
    anchor_info = level.get("anchor")
    if anchor_info is None or x is None:
        return None
    cab_h = anchor_info.get("cab_h", 50)
    pil_h = anchor_info.get("pil_h", 100)
    h = cab_h if dim == REALITY else pil_h
    return pygame.Rect(int(x), GROUND_Y - h, 40, h)


def all_solids(g, dim):
    level = g["level"]
    pressed = is_plate_pressed(level, dim, g["player"], g.get("anchor_x"))
    solids = list(static_solids(level, dim, pressed))
    if level.get("anchor") is not None and g.get("anchor_x") is not None:
        a = anchor_rect(level, dim, g["anchor_x"])
        if a is not None:
            solids.append(a)
    return solids


def _init_pests(level):
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


def _init_wardens(level):
    """P3 Warden AI initialization."""
    wardens = []
    for w in level.get("wardens", []):
        wardens.append({
            "x": float(w["patrol_min"]),
            "dir": 1,
            "state": "PATROL",
            "patrol_min": w["patrol_min"],
            "patrol_max": w["patrol_max"],
            "leash_min": w["leash_min"],
            "leash_max": w["leash_max"],
            "patrol_speed": 2.0,
            "chase_speed": 3.0,
            "alert_timer": 0,
        })
    return wardens


def new_game(level_index=0, score=0, lives=3, high_score=0):
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
        "wardens":      _init_wardens(level),
        "score":        float(score),
        "level_start_score": float(score),
        "lives":        lives,
        "high_score":   high_score,
        "state":        "play",
        "msg_timer":    0,
        "flash_frames": 0,
        "last_swap_ms": -SWAP_COOLDOWN_MS,
        "particles":    [],
        "shake_frames": 0,
        "intro_timer":  150,
        "facing_right": True,
        # P1.1 / P1.2 Mechanics
        "coyote_timer": 0,
        "jump_buffer":  0,
        "invuln":       0,
        "hit_flash":    0,
        "seconds_on_level": 0.0,
    }


def move_x(g, dx):
    p   = g["player"]
    dim = g["dim"]
    p.x += dx

    level = g["level"]
    pressed = is_plate_pressed(level, dim, p, g.get("anchor_x"))
    statics = static_solids(level, dim, pressed)

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

    pressed = is_plate_pressed(level, dim, p, g.get("anchor_x"))
    statics = static_solids(level, dim, pressed)
    for s in statics:
        if p.colliderect(s):
            if dx > 0: p.right = s.left
            else:       p.left  = s.right

    p.left  = max(0, p.left)
    p.right = min(WIDTH, p.right)


def move_y(g):
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


def try_swap(g, now_ms):
    if now_ms - g["last_swap_ms"] < SWAP_COOLDOWN_MS:
        return

    new_dim = 1 - g["dim"]

    if any(g["player"].colliderect(s) for s in all_solids(g, new_dim)):
        g["msg_timer"] = 90
        play_sound("blocked")
        return

    g["dim"]          = new_dim
    g["flash_frames"] = FLASH_FRAMES
    g["last_swap_ms"] = now_ms
    play_sound("swap")
    _spawn_particles(g)
    g["shake_frames"] = SHAKE_FRAMES


def update_wardens(g):
    """P3 Warden State Machine update."""
    px = g["player"].centerx
    py = g["player"].centery
    in_chaos = (g["dim"] == CHAOS)

    for w in g["wardens"]:
        if w["alert_timer"] > 0:
            w["alert_timer"] -= 1

        dist_x = abs(px - w["x"])
        dist_y = abs(py - (GROUND_Y - 14))

        # State Transitions
        if w["state"] == "PATROL":
            if in_chaos and dist_x <= 170 and dist_y < 60:
                w["state"] = "CHASE"
                w["alert_timer"] = 30

        elif w["state"] == "CHASE":
            if not in_chaos or dist_x > 210 or dist_y >= 60:
                w["state"] = "RETURN"

        elif w["state"] == "RETURN":
            if in_chaos and dist_x <= 170 and dist_y < 60:
                w["state"] = "CHASE"
                w["alert_timer"] = 30

        # State Behaviors
        if w["state"] == "PATROL":
            w["x"] += w["patrol_speed"] * w["dir"]
            if w["x"] <= w["patrol_min"]:
                w["x"] = float(w["patrol_min"])
                w["dir"] = 1
            elif w["x"] >= w["patrol_max"]:
                w["x"] = float(w["patrol_max"])
                w["dir"] = -1

        elif w["state"] == "CHASE":
            if px > w["x"]:
                w["dir"] = 1
                w["x"] += w["chase_speed"]
            else:
                w["dir"] = -1
                w["x"] -= w["chase_speed"]
            w["x"] = max(float(w["leash_min"]), min(float(w["leash_max"]), w["x"]))

        elif w["state"] == "RETURN":
            target = w["patrol_min"] if abs(w["x"] - w["patrol_min"]) < abs(w["x"] - w["patrol_max"]) else w["patrol_max"]
            if abs(w["x"] - target) <= w["patrol_speed"]:
                w["x"] = float(target)
                w["state"] = "PATROL"
            elif target > w["x"]:
                w["dir"] = 1
                w["x"] += w["patrol_speed"]
            else:
                w["dir"] = -1
                w["x"] -= w["patrol_speed"]


def update(g, keys, dt, now_ms):
    """Update all game state for one frame."""
    if g["state"] != "play":
        return

    # P2.3 Intro card pauses gameplay timer & physics
    if g["intro_timer"] > 0:
        g["intro_timer"] -= 1
        return

    g["seconds_on_level"] += dt / 1000.0

    if g["invuln"] > 0: g["invuln"] -= 1
    if g["hit_flash"] > 0: g["hit_flash"] -= 1

    # P1.1 Coyote time & Jump buffering
    if g["on_ground"]:
        g["coyote_timer"] = COYOTE_FRAMES
    elif g["coyote_timer"] > 0:
        g["coyote_timer"] -= 1

    if keys[pygame.K_UP] or keys[pygame.K_w]:
        g["jump_buffer"] = JUMP_BUFFER_FRAMES
    elif g["jump_buffer"] > 0:
        g["jump_buffer"] -= 1

    # Jump Execution
    if g["jump_buffer"] > 0 and g["coyote_timer"] > 0:
        g["vy"] = JUMP
        g["coyote_timer"] = 0
        g["jump_buffer"] = 0
        play_sound("jump")

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

    # Pests & Warden logic
    for pest in g["pests"]:
        pest["x"] += pest["speed"] * pest["dir"]
        if pest["x"] <= pest["min"]:
            pest["x"] = float(pest["min"])
            pest["dir"] = 1
        elif pest["x"] >= pest["max"]:
            pest["x"] = float(pest["max"])
            pest["dir"] = -1

    update_wardens(g)

    # Hazard collisions (only when not invulnerable)
    if g["dim"] == CHAOS and g["invuln"] <= 0:
        for pest in g["pests"]:
            pest_rect = pygame.Rect(int(pest["x"]), GROUND_Y - 24, 30, 24)
            if g["player"].colliderect(pest_rect):
                _player_hit(g)
                break

        if g["state"] == "play" and g["invuln"] <= 0:
            for w in g["wardens"]:
                w_rect = pygame.Rect(int(w["x"]), GROUND_Y - 28, 36, 28)
                if g["player"].colliderect(w_rect):
                    _player_hit(g)
                    break

    if g["state"] == "play" and g["invuln"] <= 0:
        for spike_rect, s_world in level.get("spikes", []):
            if is_tag_active(s_world, g["dim"]) and g["player"].colliderect(spike_rect):
                _player_hit(g)
                break

    # Fall safety
    if g["state"] == "play" and g["player"].top > HEIGHT:
        _player_hit(g)

    # Goal door collision & P2.1 Score calculation
    if g["state"] == "play" and g["player"].colliderect(level["door"]):
        time_bonus = max(0, 60 - int(g["seconds_on_level"])) * 10
        g["score"] += 500 + time_bonus
        play_sound("win")
        _advance_level(g)

    if g["msg_timer"]    > 0: g["msg_timer"]    -= 1
    if g["flash_frames"] > 0: g["flash_frames"] -= 1
    if g["shake_frames"] > 0: g["shake_frames"] -= 1
    _update_particles(g)


def _player_hit(g):
    """P1.2 Hit feedback, invulnerability, and P2.1 score deduction."""
    play_sound("hit")
    g["hit_flash"] = 6
    g["shake_frames"] = SHAKE_FRAMES
    _spawn_hit_particles(g)

    g["lives"] -= 1
    g["score"] = max(0, g["score"] - 100)

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
        g["particles"]      = []
        g["pests"]          = _init_pests(level)
        g["wardens"]        = _init_wardens(level)
        g["facing_right"]   = True
        g["invuln"]         = INVULN_FRAMES


def _advance_level(g):
    next_index = g["level_index"] + 1
    if next_index >= len(LEVELS):
        g["state"]      = "win"
        g["high_score"] = max(g["high_score"], int(g["score"]))
        _save_high_score(g["high_score"])
    else:
        score, lives, hs = g["score"], g["lives"], g["high_score"]
        g.update(new_game(next_index, score, lives, hs))


# ---------------------------------------------------------------------------
# High score persistence (P0.5 resolved path)
# ---------------------------------------------------------------------------
HIGH_SCORE_FILE = Path(__file__).resolve().parent / "highscore.txt"


def _load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def _save_high_score(score):
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
    global AUDIO_MUTED
    pygame.init()
    init_audio()

    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Shift Work")
    load_assets()
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont(None, 26)
    big   = pygame.font.SysFont(None, 54)

    _BG_SURFS[REALITY] = _make_gradient(WIDTH, HEIGHT, BG_TOP[REALITY], BG_BOT[REALITY])
    _BG_SURFS[CHAOS]   = _make_gradient(WIDTH, HEIGHT, BG_TOP[CHAOS],   BG_BOT[CHAOS])

    scene = pygame.Surface((WIDTH, HEIGHT))

    saved_hs      = _load_high_score()
    showing_title = True
    title_tick    = 0
    g             = None
    tick          = 0

    running = True
    while running:
        dt     = clock.tick(60)
        now_ms = pygame.time.get_ticks()
        tick  += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    AUDIO_MUTED = not AUDIO_MUTED

                if showing_title:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        showing_title = False
                        g = new_game(level_index=0, high_score=saved_hs)
                else:
                    if event.key == pygame.K_ESCAPE:
                        if g["state"] == "play":
                            g["state"] = "pause"
                        elif g["state"] == "pause":
                            g["state"] = "play"

                    elif g["state"] == "pause":
                        if event.key == pygame.K_q:
                            running = False
                        elif event.key == pygame.K_r:
                            g.update(new_game(g["level_index"], g["level_start_score"], 3, g["high_score"]))

                    elif g["intro_timer"] > 0:
                        g["intro_timer"] = 0

                    elif event.key == pygame.K_r:
                        if g["state"] in ("play", "lose"):
                            g.update(new_game(g["level_index"], g["level_start_score"], 3, g["high_score"]))
                        elif g["state"] == "win":
                            g = new_game(level_index=0, high_score=g["high_score"])

                    elif g["state"] == "lose" and event.key == pygame.K_n:
                        g = new_game(level_index=0, high_score=g["high_score"])

                    elif g["state"] == "play":
                        if event.key == pygame.K_SPACE:
                            try_swap(g, now_ms)

            elif event.type == pygame.KEYUP:
                # P1.1 Variable jump height
                if g and g["state"] == "play" and event.key in (pygame.K_UP, pygame.K_w):
                    if g["vy"] < -4:
                        g["vy"] = -4

        if showing_title:
            title_tick += 1
            draw_title(scene, font, big, title_tick)
            screen.blit(scene, (0, 0))
        else:
            update(g, pygame.key.get_pressed(), dt, now_ms)
            draw(scene, font, big, g, tick)

            if g["shake_frames"] > 0:
                sx = random.randint(-SHAKE_MAG, SHAKE_MAG)
                sy = random.randint(-(SHAKE_MAG // 2), SHAKE_MAG // 2)
                screen.fill((0, 0, 0))
                screen.blit(scene, (sx, sy))
            else:
                screen.blit(scene, (0, 0))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()