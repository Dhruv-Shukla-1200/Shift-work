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
import pygame

# ---------------------------------------------------------------------------
# Global constants -- screen size, physics, world IDs
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 500          # window dimensions in pixels
GROUND_Y = 440                    # y-coordinate of the ground surface
REALITY, CHAOS = 0, 1             # dimension identifiers (integers for easy toggle)

SPEED    = 5                      # horizontal pixels per frame
GRAVITY  = 0.6                    # pixels added to fall speed each frame
JUMP     = -12                    # initial upward velocity when jumping (negative = up)
MAX_FALL = 15                     # terminal (maximum) fall speed

# Swap feedback constants (P1)
SWAP_COOLDOWN_MS = 300            # milliseconds before player can swap again
FLASH_FRAMES     = 8              # how many frames the swap flash overlay lasts


# ---------------------------------------------------------------------------
# Level data  (P1: data-driven levels)
# ---------------------------------------------------------------------------
# Each level is a dictionary describing the full layout.
# Adding a new level is just adding a new dictionary here -- no code changes needed.
#
# Keys:
#   anchor_x    -- starting x position of the shared cabinet/pillar object
#   spawn       -- (x, y) where the player starts (top-left corner of player rect)
#   wall        -- pygame.Rect for the Reality-only wall (or None)
#   ledge       -- pygame.Rect for the shared ledge
#   door        -- pygame.Rect for the exit door (top of it rests on the ledge)
#   pest_min/max -- horizontal patrol range for pests (Chaos only)
#   pest_speed  -- base movement speed of pests (pixels per frame)
#   pest_count  -- how many pests spawn

LEVELS = [
    # -- Level 1 -------------------------------------------------------------
    # Tutorial-like: one wall, one ledge, two slow pests.
    # Solution: swap to Chaos to pass the wall, push the pillar right,
    #           jump onto it, then jump to the ledge and reach the door.
    {
        "anchor_x":   200,
        "spawn":      (60, 400),
        "wall":       pygame.Rect(380, 300, 30, 140),   # Reality-only office partition
        "ledge":      pygame.Rect(650, 300, 150, 20),   # shared ledge in both worlds
        "door":       pygame.Rect(740, 250, 30, 50),    # exit door on the ledge
        "pest_min":   420,
        "pest_max":   530,
        "pest_speed": 2,
        "pest_count": 2,
    },
    # -- Level 2 -------------------------------------------------------------
    # Harder: wall moved closer to spawn, ledge further right, faster pests,
    # pillar starts far left so the player must push it further.
    # Three pests instead of two.
    {
        "anchor_x":   150,
        "spawn":      (60, 400),
        "wall":       pygame.Rect(320, 280, 30, 160),   # taller wall, moved left
        "ledge":      pygame.Rect(620, 280, 180, 20),   # slightly further up and right
        "door":       pygame.Rect(750, 230, 30, 50),
        "pest_min":   380,
        "pest_max":   570,
        "pest_speed": 3,                                # faster than Level 1
        "pest_count": 3,
    },
]


# ---------------------------------------------------------------------------
# Colour palettes -- indexed by dimension (REALITY=0, CHAOS=1)
# ---------------------------------------------------------------------------
COL_BG      = ((34,  40,  56), (62,  22,  86))   # background fill
COL_GROUND  = ((70,  75,  90), (110, 50, 140))   # ground rect
COL_LEDGE   = ((120, 125, 140), (150, 90, 180))  # ledge rect
COL_WALL    = (150, 150, 160)                     # Reality wall (single colour)
COL_CABINET = (170, 175, 185)                     # filing cabinet (Reality)
COL_PILLAR  = (140, 110,  80)                     # stone pillar (Chaos)
COL_PEST    = (230,  70,  70)                     # pest (Chaos)
COL_DOOR    = (240, 200,  60)                     # door / exit
COL_PLAYER  = (90,  210, 130)                     # player character


# ---------------------------------------------------------------------------
# Helper: build the list of solid rectangles for a given dimension
# ---------------------------------------------------------------------------

def static_solids(level, dim):
    """Return a list of immovable solid Rects for the current dimension.

    The ground and ledge exist in both worlds.
    The wall only exists in Reality (Corporate office partition).
    In Chaos the wall is gone, but pests appear instead.
    """
    result = [
        pygame.Rect(0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y),  # floor -- always present
        level["ledge"],                                        # raised platform -- always present
    ]
    if dim == REALITY and level["wall"] is not None:
        result.append(level["wall"])   # office wall -- Reality only
    return result


def anchor_rect(level, dim, x):
    """Return the Rect of the shared pushable object at horizontal position x.

    In Reality  -> short filing cabinet (height 50 px)
    In Chaos    -> tall stone pillar    (height 100 px, can be jumped onto from ground)

    Both share the same anchor_x, so pushing in one world moves it in the other.
    """
    h = 50 if dim == REALITY else 100
    return pygame.Rect(int(x), GROUND_Y - h, 40, h)


def all_solids(g, dim):
    """Return static solids PLUS the anchored object -- everything the player collides with."""
    return static_solids(g["level"], dim) + [anchor_rect(g["level"], dim, g["anchor_x"])]


# ---------------------------------------------------------------------------
# Game-state factory
# ---------------------------------------------------------------------------

def new_game(level_index=0, score=0, lives=3, high_score=0):
    """Create and return a fresh game-state dictionary for the given level.

    We pass score and lives in so that level progression preserves them.
    high_score is kept across restarts (it lives in memory, not here).
    """
    level = LEVELS[level_index]
    sx, sy = level["spawn"]

    # Build pest list from level data: alternate directions, spread across patrol range
    pests = []
    count = level["pest_count"]
    span  = level["pest_max"] - level["pest_min"]
    for i in range(count):
        px        = level["pest_min"] + (span * i // max(count - 1, 1))
        direction = 1 if i % 2 == 0 else -1
        pests.append({"x": float(px), "dir": direction})

    return {
        # World state
        "dim":          REALITY,          # start in Corporate Reality
        "level_index":  level_index,
        "level":        level,            # current level dict

        # Player
        "player":       pygame.Rect(sx, sy, 28, 40),  # player rectangle
        "vy":           0.0,              # vertical velocity
        "on_ground":    False,            # True when standing on a solid

        # Pushable object
        "anchor_x":     float(level["anchor_x"]),  # shared x for cabinet/pillar

        # Enemies
        "pests":        pests,            # list of pest dicts {"x", "dir"}

        # Scoring and lives (P1)
        "score":        float(score),     # carry score across levels
        "lives":        lives,            # remaining lives
        "high_score":   high_score,       # best score this session

        # Game-flow
        "state":        "play",           # "play" | "lose" | "win"
        "msg_timer":    0,                # frames left to show swap-blocked message

        # Swap feedback (P1)
        "flash_frames": 0,                # frames left in swap flash overlay
        "last_swap_ms": -SWAP_COOLDOWN_MS,  # time of last swap (ensures first swap works)
    }


# ---------------------------------------------------------------------------
# Movement helpers
# ---------------------------------------------------------------------------

def move_x(g, dx):
    """Move the player horizontally by dx pixels, then resolve collisions.

    Collision order:
      1. Try to push the anchor object if we walk into it.
      2. Resolve overlap with static walls.
      3. Clamp player to screen edges.

    The anchor is pushed by exactly dx pixels if the destination is free.
    If blocked, the player stops at the anchor's edge instead.
    """
    p   = g["player"]
    dim = g["dim"]

    p.x += dx   # tentatively move the player

    # -- Anchor collision and push --
    a = anchor_rect(g["level"], dim, g["anchor_x"])
    if dx and p.colliderect(a):
        nx   = g["anchor_x"] + dx                  # proposed new anchor position
        test = anchor_rect(g["level"], dim, nx)     # anchor rect at new position
        # Push succeeds only if anchor stays on screen and doesn't enter a static solid
        blocked = any(test.colliderect(s) for s in static_solids(g["level"], dim))
        if 0 <= nx <= WIDTH - 40 and not blocked:
            g["anchor_x"] = nx                     # move anchor!
        elif dx > 0:
            p.right = a.left                       # player stopped by anchor on the right
        else:
            p.left  = a.right                      # player stopped by anchor on the left

    # -- Static solid collision --
    for s in static_solids(g["level"], dim):
        if p.colliderect(s):
            if dx > 0:
                p.right = s.left
            else:
                p.left  = s.right

    # -- Screen boundary clamp --
    p.left  = max(0, p.left)
    p.right = min(WIDTH, p.right)


def move_y(g):
    """Apply gravity, move the player vertically, and resolve vertical collisions.

    Uses math.ceil for downward motion to avoid on_ground flicker:
    a fractional pixel of penetration could make the player leave the ground
    for one frame, resetting on_ground incorrectly.
    """
    p = g["player"]

    # Apply gravity (accelerate downward, cap at MAX_FALL)
    g["vy"] = min(g["vy"] + GRAVITY, MAX_FALL)

    # Round velocity: ceil when falling, floor when rising
    dy = math.ceil(g["vy"]) if g["vy"] > 0 else math.floor(g["vy"])
    p.y += dy

    g["on_ground"] = False   # reset; set True below if we land on something

    for s in all_solids(g, g["dim"]):
        if p.colliderect(s):
            if g["vy"] > 0:        # falling -- land on top of solid
                p.bottom       = s.top
                g["on_ground"] = True
            else:                  # rising -- bump head on bottom of solid
                p.top = s.bottom
            g["vy"] = 0            # stop vertical motion on impact


# ---------------------------------------------------------------------------
# Dimension swap  (P1: cooldown + flash)
# ---------------------------------------------------------------------------

def try_swap(g, now_ms):
    """Attempt to swap the player's current dimension.

    Refuses the swap if:
      - The cooldown hasn't expired yet (prevents spamming).
      - The player would overlap a solid in the target world.

    On success: changes dim, starts the visual flash, records the swap time.
    """
    # Cooldown check (P1): now_ms is pygame.time.get_ticks()
    if now_ms - g["last_swap_ms"] < SWAP_COOLDOWN_MS:
        return   # too soon, silently ignore

    new_dim = 1 - g["dim"]   # toggle: 0 becomes 1, 1 becomes 0

    # Overlap check: refuse swap if the player would be inside a solid
    if any(g["player"].colliderect(s) for s in all_solids(g, new_dim)):
        g["msg_timer"] = 90   # show "can't swap" message for 90 frames (~1.5 s)
        return

    # Success: swap the world
    g["dim"]          = new_dim
    g["flash_frames"] = FLASH_FRAMES   # start visual flash (P1)
    g["last_swap_ms"] = now_ms         # record time for cooldown (P1)


# ---------------------------------------------------------------------------
# Main update  (called every frame while state == "play")
# ---------------------------------------------------------------------------

def update(g, keys, dt, now_ms):
    """Update all game logic for one frame.

    Parameters:
      g      -- game state dict (mutated in place)
      keys   -- result of pygame.key.get_pressed()
      dt     -- milliseconds since last frame (from clock.tick)
      now_ms -- absolute time in ms (from pygame.time.get_ticks)
    """
    if g["state"] != "play":
        return

    # -- Player horizontal movement --
    dx = 0
    if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= SPEED
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += SPEED
    if dx:
        move_x(g, dx)

    # -- Gravity and vertical collision --
    move_y(g)

    # -- Pest movement and collision --
    level = g["level"]
    for pest in g["pests"]:
        pest["x"] += level["pest_speed"] * pest["dir"]
        # Reverse direction at patrol boundaries
        if pest["x"] <= level["pest_min"] or pest["x"] >= level["pest_max"]:
            pest["dir"] *= -1
        # Pests only exist (and can kill) in Chaos
        pest_rect = pygame.Rect(int(pest["x"]), GROUND_Y - 24, 30, 24)
        if g["dim"] == CHAOS and g["player"].colliderect(pest_rect):
            _player_hit(g)   # lose a life (P1)

    # -- Door / level-complete check --
    if g["player"].colliderect(level["door"]):
        g["score"] += 1000       # bonus for reaching the exit
        _advance_level(g)        # move to next level or win (P1)

    # -- Time-based score (10 points per second while alive) --
    g["score"] += dt / 1000 * 10

    # -- Decrement timers --
    if g["msg_timer"]    > 0: g["msg_timer"]    -= 1
    if g["flash_frames"] > 0: g["flash_frames"] -= 1


# ---------------------------------------------------------------------------
# Lives / level progression helpers  (P1)
# ---------------------------------------------------------------------------

def _player_hit(g):
    """Deduct one life. Respawn at level start, or trigger game-over if lives reach 0."""
    g["lives"] -= 1
    if g["lives"] <= 0:
        g["state"] = "lose"
        g["high_score"] = max(g["high_score"], int(g["score"]))
        _save_high_score(g["high_score"])
    else:
        # Respawn at the start of the current level, keeping score and remaining lives
        level  = g["level"]
        sx, sy = level["spawn"]
        g["player"].topleft = (sx, sy)              # reset position
        g["vy"]             = 0.0
        g["dim"]            = REALITY               # always respawn in Reality
        g["anchor_x"]       = float(level["anchor_x"])  # reset anchor position
        g["msg_timer"]      = 0
        g["flash_frames"]   = 0


def _advance_level(g):
    """Move to the next level, or set state to 'win' if all levels are done."""
    next_index = g["level_index"] + 1
    if next_index >= len(LEVELS):
        # All levels complete!
        g["state"]      = "win"
        g["high_score"] = max(g["high_score"], int(g["score"]))
        _save_high_score(g["high_score"])
    else:
        # Keep score and lives; load the next level layout
        score      = g["score"]
        lives      = g["lives"]
        high_score = g["high_score"]
        g.update(new_game(next_index, score, lives, high_score))


# ---------------------------------------------------------------------------
# High score persistence  (P1)
# ---------------------------------------------------------------------------
# File I/O is always wrapped in try/except so a missing file or permission
# error never crashes the game.

HIGH_SCORE_FILE = "highscore.txt"


def _load_high_score():
    """Read the high score from disk. Returns 0 if the file doesn't exist."""
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def _save_high_score(score):
    """Write the high score to disk. Silently ignores any write errors."""
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw(screen, font, big, g):
    """Render the entire frame.

    Drawing order (back to front):
      background -> ground -> ledge -> wall/anchor -> door -> pests -> player
      -> HUD text -> overlay messages -> swap flash
    """
    dim   = g["dim"]
    level = g["level"]

    # Background fill (colour depends on dimension)
    screen.fill(COL_BG[dim])

    # Ground and ledge
    ground_rect = pygame.Rect(0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y)
    pygame.draw.rect(screen, COL_GROUND[dim], ground_rect)
    pygame.draw.rect(screen, COL_LEDGE[dim],  level["ledge"])

    # Door is always visible as a goal landmark
    pygame.draw.rect(screen, COL_DOOR, level["door"])

    # Dimension-specific objects
    if dim == REALITY:
        if level["wall"] is not None:
            pygame.draw.rect(screen, COL_WALL, level["wall"])          # office partition
        pygame.draw.rect(screen, COL_CABINET,
                         anchor_rect(level, REALITY, g["anchor_x"]))   # filing cabinet
    else:
        pygame.draw.rect(screen, COL_PILLAR,
                         anchor_rect(level, CHAOS, g["anchor_x"]))     # stone pillar
        for pest in g["pests"]:
            pygame.draw.rect(screen, COL_PEST,
                             pygame.Rect(int(pest["x"]), GROUND_Y - 24, 30, 24))

    # Player
    pygame.draw.rect(screen, COL_PLAYER, g["player"])

    # HUD -- top-left info panel
    world_name = "Corporate Reality" if dim == REALITY else "Surreal Chaos"
    hud_lines = [
        f"World: {world_name}",
        f"Score: {int(g['score'])}",
        f"Level: {g['level_index'] + 1} / {len(LEVELS)}",
        f"Lives: {g['lives']}",
        f"Best:  {g['high_score']}",
    ]
    for i, line in enumerate(hud_lines):
        surf = font.render(line, True, (255, 255, 255))
        screen.blit(surf, (10, 10 + i * 28))

    # Bottom hint bar
    hint = font.render(
        "Arrows/WASD: move+jump  |  SPACE: swap world  |  R: restart",
        True, (180, 180, 180)
    )
    screen.blit(hint, (10, HEIGHT - 28))

    # Swap-blocked warning (shown for ~1.5 s)
    if g["msg_timer"] > 0:
        msg = font.render("Can't swap -- something solid is in the way!",
                          True, (255, 220, 100))
        screen.blit(msg, (10, 10 + len(hud_lines) * 28))

    # Game-over or win overlay
    if g["state"] != "play":
        headline = ("SHIFT COMPLETE -- ALL LEVELS DONE!"
                    if g["state"] == "win" else "GAME OVER")
        t = big.render(headline, True, (255, 255, 255))
        screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 150))

        score_surf = font.render(
            f"Final score: {int(g['score'])}   Best: {g['high_score']}",
            True, (255, 220, 100)
        )
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 215))

        restart_surf = font.render("Press R to restart", True, (200, 200, 200))
        screen.blit(restart_surf, (WIDTH // 2 - restart_surf.get_width() // 2, 250))

    # Swap flash overlay (P1): white screen tint that fades over FLASH_FRAMES frames
    if g["flash_frames"] > 0:
        alpha = int(200 * g["flash_frames"] / FLASH_FRAMES)  # fade from ~200 to 0
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        screen.blit(flash, (0, 0))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    """Initialise pygame and run the game loop."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Shift Work")
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont(None, 28)   # regular UI font
    big   = pygame.font.SysFont(None, 56)   # large font for win/lose headline

    # Load the persistent high score from disk (P1)
    saved_hs = _load_high_score()
    g = new_game(level_index=0, high_score=saved_hs)

    running = True
    while running:
        dt     = clock.tick(60)              # target 60 FPS; dt = ms since last frame
        now_ms = pygame.time.get_ticks()     # absolute time used for swap cooldown

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Full restart: back to level 1, keep high score in memory
                    hs = g["high_score"]
                    g  = new_game(level_index=0, high_score=hs)

                elif g["state"] == "play":
                    if event.key == pygame.K_SPACE:
                        try_swap(g, now_ms)        # dimension swap (with cooldown)
                    elif event.key in (pygame.K_UP, pygame.K_w) and g["on_ground"]:
                        g["vy"] = JUMP             # jump (only when standing on solid)

        update(g, pygame.key.get_pressed(), dt, now_ms)
        draw(screen, font, big, g)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
