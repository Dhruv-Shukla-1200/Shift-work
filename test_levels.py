import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((800, 500))
import main

class MockKeys:
    def __init__(self, pressed=None): self.pressed = set(pressed or [])
    def __getitem__(self, key): return key in self.pressed

class HeadlessBot:
    def __init__(self, level_index=0):
        self.g = main.new_game(level_index=level_index, high_score=0)
        self.g["intro_timer"] = 0
        self.now_ms = 1000

    def step(self, left=False, right=False, jump=False, swap=False, frames=1):
        for _ in range(frames):
            self.now_ms += 16
            if swap: main.try_swap(self.g, self.now_ms)
            pressed = []
            if left: pressed.append(pygame.K_LEFT)
            if right: pressed.append(pygame.K_RIGHT)
            if jump: pressed.append(pygame.K_UP)
            main.update(self.g, MockKeys(pressed), dt=16, now_ms=self.now_ms)

if __name__ == "__main__":
    bot = HeadlessBot(0)
    bot.step(right=True, frames=10)
    print("Test Runner Executed Successfully!")
