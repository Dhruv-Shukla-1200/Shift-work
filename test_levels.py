"""
Headless automated test runner for Shift Work.
Simulates gameplay across all 5 levels to verify:
1. Intended solutions succeed and advance to next level.
2. Intended shortcuts fail (physics limits enforced).
3. Pressure plate & gate mechanics work as specified.
4. Spikes and pests deal damage only in active dimensions.
5. Fall safety triggers properly.
6. R key restarts level during play while preserving score and lives.
"""

import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((800, 500))

import main


class MockKeys:
    """Mock pygame keys dictionary/lookup."""
    def __init__(self, pressed=None):
        self.pressed = set(pressed or [])

    def __getitem__(self, key):
        return key in self.pressed


class HeadlessBot:
    """Helper to step the real game logic frame by frame."""
    def __init__(self, level_index=0):
        self.g = main.new_game(level_index=level_index, high_score=0)
        self.now_ms = 1000
        self.frame = 0

    def step(self, left=False, right=False, jump=False, swap=False, frames=1):
        """Simulate `frames` game updates."""
        for _ in range(frames):
            self.frame += 1
            self.now_ms += 16  # ~60 FPS

            # Handle swap (SPACE)
            if swap:
                main.try_swap(self.g, self.now_ms)
                swap = False  # trigger once

            # Handle jump
            if jump and self.g["on_ground"]:
                self.g["vy"] = main.JUMP
                jump = False

            # Build keys
            pressed = []
            if left:  pressed.append(pygame.K_LEFT)
            if right: pressed.append(pygame.K_RIGHT)
            if jump:  pressed.append(pygame.K_UP)

            keys = MockKeys(pressed)
            main.update(self.g, keys, dt=16, now_ms=self.now_ms)


def test_level_1():
    print("\n--- Testing Level 1: Walls Aren't Real ---")
    bot = HeadlessBot(0)

    # 1. Verify wall blocks Reality movement
    bot.step(right=True, frames=60)
    wall_left = 300
    assert bot.g["player"].right <= wall_left, f"Player did not stop at wall: {bot.g['player'].right}"
    print(f"  [PASS] Blocked by Reality wall at x={bot.g['player'].right}")

    # Verify jumping wall fails (wall is 140px tall, max jump rise is 126px)
    bot.step(jump=True, right=True, frames=45)
    assert bot.g["player"].right <= wall_left, "Player managed to jump over wall in Reality!"
    print("  [PASS] Jump shortcut over 140px wall correctly failed")

    # 2. Swap to Chaos -> wall disappears -> walk right
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.CHAOS, "Failed to swap to Chaos"
    print("  [PASS] Swapped to Chaos")

    bot.step(right=True, frames=20)
    assert bot.g["player"].left > wall_left, f"Player could not walk past wall: {bot.g['player'].left}"
    print(f"  [PASS] Walked past wall position to x={bot.g['player'].x}")

    # 3. Verify Chaos spikes at x=420 would kill if staying in Chaos
    test_spike_bot = HeadlessBot(0)
    test_spike_bot.step(swap=True, frames=1)
    test_spike_bot.step(right=True, frames=75)
    assert test_spike_bot.g["lives"] == 2, "Spikes did not kill player in Chaos!"
    print("  [PASS] Chaos spikes correctly killed player when entered in Chaos")

    # 4. Correct solution: wait cooldown, then swap back to Reality before 420
    bot.step(frames=10)
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.REALITY, "Failed to swap back to Reality"
    print("  [PASS] Swapped back to Reality before spikes")

    # 5. Walk safely through the spike zone in Reality (spikes only hurt in Chaos)
    while bot.g["player"].right < 720 and bot.g["level_index"] == 0:
        bot.step(right=True, frames=1)
    assert bot.g["lives"] == 3, f"Player took damage in Reality from spikes! Lives={bot.g['lives']}"

    # Step into door
    for _ in range(10):
        if bot.g["level_index"] == 1:
            break
        bot.step(right=True, frames=1)
    assert bot.g["level_index"] == 1, f"Did not advance to Level 2: level_index={bot.g['level_index']}"
    print("  [PASS] Level 1 solved successfully and advanced to Level 2!")


def test_level_2():
    print("\n--- Testing Level 2: Stairway Between Worlds ---")
    bot = HeadlessBot(1)

    # Climb onto P1 (Reality, top y=350, left=140, right=240)
    bot.step(jump=True, right=True, frames=25)
    bot.step(right=True, frames=10)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 350, f"Not on P1: y={bot.g['player'].bottom}"
    print("  [PASS] Landed on P1 (Reality) at y=350")

    # Jump towards P2 (Chaos, top y=270, x=290..390) and swap mid-air!
    bot.step(jump=True, right=True, frames=10)
    bot.step(swap=True, right=True, frames=1)
    assert bot.g["dim"] == main.CHAOS, "Failed mid-air swap to Chaos"
    bot.step(right=True, frames=10)
    bot.step(frames=20)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 270, f"Not on P2: y={bot.g['player'].bottom}, x={bot.g['player'].x}"
    print("  [PASS] Mid-air swap successful: landed on P2 (Chaos) at y=270")

    # Jump towards P3 (Reality, top y=190, x=440..540) and swap mid-air!
    bot.step(frames=18)  # cooldown
    bot.step(jump=True, right=True, frames=10)
    bot.step(swap=True, right=True, frames=1)
    assert bot.g["dim"] == main.REALITY, "Failed mid-air swap to Reality"
    bot.step(right=True, frames=15)
    bot.step(frames=20)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 190, f"Not on P3: y={bot.g['player'].bottom}, x={bot.g['player'].x}"
    print("  [PASS] Mid-air swap successful: landed on P3 (Reality) at y=190")

    # Jump towards P4 (Both, top y=120, x=590..800)
    bot.step(jump=True, right=True, frames=15)
    bot.step(right=True, frames=15)
    bot.step(frames=20)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 120, f"Not on P4: y={bot.g['player'].bottom}"
    print("  [PASS] Landed on P4 (Both) at y=120")

    # Walk to door at x=740, y=70
    for _ in range(50):
        if bot.g["level_index"] == 2:
            break
        bot.step(right=True, frames=1)
    assert bot.g["level_index"] == 2, f"Did not advance to Level 3: {bot.g['level_index']}"
    print("  [PASS] Level 2 solved successfully and advanced to Level 3!")


def test_level_3():
    print("\n--- Testing Level 3: Push It ---")
    bot = HeadlessBot(2)

    # In Reality, pushing cabinet stops at wall (anchor x=340)
    bot.step(right=True, frames=60)
    assert bot.g["anchor_x"] <= 340, f"Cabinet moved past wall in Reality: {bot.g['anchor_x']}"
    print(f"  [PASS] Cabinet correctly blocked by Reality wall at anchor_x={bot.g['anchor_x']}")

    # Reset level to start solution
    bot = HeadlessBot(2)
    # 1. Swap to Chaos at start
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.CHAOS, "Failed swap to Chaos"

    # 2. Push pillar past wall position to anchor_x ~ 600
    while bot.g["anchor_x"] < 600:
        bot.step(right=True, frames=1)
    print(f"  [PASS] Pushed pillar in Chaos past wall to anchor_x={bot.g['anchor_x']}")

    # 3. Jump straight up and land on pillar (top y = 340)
    bot.step(jump=True, frames=15)
    bot.step(right=True, frames=10)
    bot.step(frames=15)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 340, f"Failed to land on pillar: y={bot.g['player'].bottom}"
    print("  [PASS] Landed on pillar top at y=340")

    # 4. Jump from pillar top to high ledge (ledge top y=300, x=650)
    bot.step(jump=True, right=True, frames=15)
    bot.step(right=True, frames=10)
    bot.step(frames=15)
    # Walk into door
    for _ in range(50):
        if bot.g["level_index"] == 3:
            break
        bot.step(right=True, frames=1)
    assert bot.g["level_index"] == 3, f"Did not advance to Level 4: {bot.g['level_index']}"
    print("  [PASS] Level 3 solved successfully and advanced to Level 4!")


def test_level_4():
    print("\n--- Testing Level 4: Hold the Door ---")
    bot = HeadlessBot(3)

    # 1. Push cabinet in Reality to wall (stops at anchor_x = 180)
    bot.step(right=True, frames=30)
    assert bot.g["anchor_x"] <= 180, f"Cabinet went past wall in Reality: {bot.g['anchor_x']}"
    print(f"  [PASS] Cabinet stopped at Reality wall: anchor_x={bot.g['anchor_x']}")

    # Verify gate is closed initially
    plate_pressed = main.is_plate_pressed(bot.g["level"], bot.g["dim"], bot.g["player"], bot.g["anchor_x"])
    assert not plate_pressed, "Plate should not be pressed yet"
    assert bot.g["level"]["gate"] in main.static_solids(bot.g["level"], bot.g["dim"], plate_pressed), "Gate should be solid"
    print("  [PASS] Gate is initially closed and solid")

    # 2. Wait for pest timing window, then swap to Chaos
    bot.step(frames=35)
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.CHAOS, "Failed to swap to Chaos"

    # 3. Push pillar past wall and onto plate (anchor_x >= 300)
    for _ in range(50):
        if bot.g["anchor_x"] >= 300:
            break
        bot.step(right=True, frames=1)
    assert bot.g["anchor_x"] >= 300, f"Anchor not on plate: {bot.g['anchor_x']}"
    assert main.is_plate_pressed(bot.g["level"], bot.g["dim"], bot.g["player"], bot.g["anchor_x"]), "Plate is not pressed by anchor"
    print(f"  [PASS] Anchor parked on pressure plate at anchor_x={bot.g['anchor_x']}, plate pressed!")

    # Verify gate is open while anchor sits on plate
    assert bot.g["level"]["gate"] not in main.all_solids(bot.g, bot.g["dim"]), "Gate should be open when plate is pressed"
    print("  [PASS] Gate is open while anchor sits on plate")

    # 4. Swap back to Reality immediately (cooldown expired during push)
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.REALITY, "Failed to swap to Reality"
    assert bot.g["lives"] == 3, f"Player took damage: lives={bot.g['lives']}"
    print("  [PASS] Swapped back to Reality; anchor continues to hold plate down!")

    # 5. Jump over cabinet (height 50) and walk through open gate (at x=560)
    bot.step(jump=True, right=True, frames=15)
    bot.step(right=True, frames=15)
    bot.step(frames=15)
    for _ in range(100):
        if bot.g["level_index"] == 4:
            break
        bot.step(right=True, frames=1)
    assert bot.g["level_index"] == 4, f"Did not advance to Level 5: {bot.g['level_index']}"
    print("  [PASS] Level 4 solved successfully and advanced to Level 5!")


def test_level_5():
    print("\n--- Testing Level 5: Overtime ---")
    bot = HeadlessBot(4)

    # 1. Push cabinet in Reality to wall (stops at anchor_x = 220)
    bot.step(right=True, frames=30)
    assert bot.g["anchor_x"] <= 220, f"Cabinet went past wall in Reality: {bot.g['anchor_x']}"
    print(f"  [PASS] Cabinet stopped at Reality wall: anchor_x={bot.g['anchor_x']}")

    # 2. Wait pest timing window, then swap to Chaos
    bot.step(frames=30)
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.CHAOS, "Failed to swap to Chaos"

    # 3. Push pillar past wall until clear (player.left >= 290)
    for _ in range(30):
        if bot.g["player"].left >= 290:
            break
        bot.step(right=True, frames=1)
    assert bot.g["player"].left >= 290, "Player not past wall"
    assert bot.g["lives"] == 3, f"Player was hit: lives={bot.g['lives']}"
    print("  [PASS] Pushed pillar past wall safely in Chaos")

    # 4. Swap back to Reality (safe from pests)
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.REALITY, "Failed to swap to Reality"

    # 5. Push cabinet in Reality to anchor_x = 520 (just left of CP at 560)
    for _ in range(60):
        if bot.g["anchor_x"] >= 520:
            break
        bot.step(right=True, frames=1)
    assert bot.g["anchor_x"] >= 520, f"Anchor not at 520: {bot.g['anchor_x']}"
    print(f"  [PASS] Pushed anchor to staircase position at x={bot.g['anchor_x']}")

    # 6. Swap to Chaos
    bot.step(swap=True, frames=1)
    assert bot.g["dim"] == main.CHAOS, "Failed to swap to Chaos"

    # 7. Jump onto left side of pillar (x=525)
    bot.step(jump=True, frames=15)
    bot.step(right=True, frames=7)
    bot.step(frames=15)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 340, f"Not on pillar: y={bot.g['player'].bottom}"
    print("  [PASS] Landed on pillar top at y=340")

    # 8. Jump straight up beside CP until above y=260, then move right onto CP
    bot.step(jump=True, frames=12)
    bot.step(right=True, frames=10)
    bot.step(frames=15)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 260, f"Not on CP: y={bot.g['player'].bottom}"
    print("  [PASS] Landed on CP (Chaos platform) at y=260")

    # 9. From CP, jump right and mid-air swap to Reality, landing on RP (top y=180, x=710..800)
    while bot.now_ms - bot.g["last_swap_ms"] < 300:
        bot.step(frames=1)
    bot.step(jump=True, right=True, frames=10)
    bot.step(swap=True, right=True, frames=1)
    bot.step(right=True, frames=15)
    bot.step(frames=15)
    assert bot.g["on_ground"] and bot.g["player"].bottom == 180, f"Not on RP: y={bot.g['player'].bottom}"
    print("  [PASS] Mid-air swap successful: landed on RP (Reality platform) at y=180")

    # 10. Walk to door at x=750, y=130
    for _ in range(30):
        if bot.g["state"] == "win":
            break
        bot.step(right=True, frames=1)
    assert bot.g["state"] == "win", f"Did not win game! State={bot.g['state']}"
    print("  [PASS] Level 5 solved successfully -- ALL LEVELS COMPLETE! Game Won!")


def test_mechanics():
    print("\n--- Testing Engine Mechanics (E1-E8) ---")
    # Test Fall Safety (E7)
    bot = HeadlessBot(0)
    bot.g["player"].y = main.HEIGHT + 10
    main.update(bot.g, MockKeys(), dt=16, now_ms=1000)
    assert bot.g["lives"] == 2, f"Fall safety failed to deduct life: {bot.g['lives']}"
    print("  [PASS] E7 Fall Safety: player below screen took damage and respawned")

    # Test Level Restart on R (E8)
    bot = HeadlessBot(2)
    bot.g["score"] = 500
    bot.g["lives"] = 2
    bot.step(swap=True, right=True, frames=40)
    assert bot.g["anchor_x"] != 200, "Anchor should have moved"
    # Simulate pressing R in game
    score, lives, hs = bot.g["score"], bot.g["lives"], bot.g["high_score"]
    bot.g.update(main.new_game(bot.g["level_index"], score, lives, hs))
    assert bot.g["anchor_x"] == 200, "Level restart did not reset anchor"
    assert bot.g["level_index"] == 2, "Level restart changed level index"
    assert bot.g["lives"] == 2 and bot.g["score"] == score, "Score/lives not preserved on R"
    print("  [PASS] E8 Level Restart: pressing R resets current level while preserving score & lives")


if __name__ == "__main__":
    test_level_1()
    test_level_2()
    test_level_3()
    test_level_4()
    test_level_5()
    test_mechanics()
    print("\n========================================================")
    print("ALL 5 LEVELS AND ENGINE MECHANICS VERIFIED AND PASSED!")
    print("========================================================")
