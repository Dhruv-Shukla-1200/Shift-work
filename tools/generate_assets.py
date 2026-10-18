"""Generate the Shift Work sprite set with Pygame.

Run:
    python tools/generate_assets.py

All game sprites are exported at 1x with per-pixel alpha. The atlas is a
presentation sheet; source sprites remain separate and transparently backed.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Iterable, Sequence

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

S = 4
ROOT = Path(__file__).resolve().parents[1]
OUT_ASSETS = ROOT / "assets"
OUT_PUBLIC = ROOT / "public" / "assets"

C = {
    "ink": "#171726",
    "white": "#F4F1F7",
    "reality_dark": "#121A2C",
    "reality_light": "#30384C",
    "reality_floor": "#3E4658",
    "reality_top": "#878E9E",
    "chaos_dark": "#2A0844",
    "chaos_light": "#441464",
    "chaos_floor": "#5A267D",
    "chaos_top": "#9B5FBC",
    "uniform_reality": "#3460AA",
    "uniform_chaos": "#7337B9",
    "skin": "#EEC49C",
    "cabinet": "#9EA3AE",
    "pillar": "#806A4C",
    "partition": "#8E919B",
    "pest": "#C33434",
    "eye": "#FFDA4B",
    "door": "#DAB62E",
    "door_frame": "#C3A019",
    "window": "#B4DCFF",
}


def color(value: str | tuple[int, ...], alpha: int | None = None) -> pygame.Color:
    result = pygame.Color(value)
    if alpha is not None:
        result.a = alpha
    return result


class Pen:
    def __init__(self, width: int, height: int, background: str | None = None):
        flags = pygame.SRCALPHA
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width * S, height * S), flags)
        self.surface.fill(color(background) if background else (0, 0, 0, 0))

    @staticmethod
    def r(rect: Sequence[float]) -> pygame.Rect:
        return pygame.Rect(*(round(value * S) for value in rect))

    @staticmethod
    def p(points: Iterable[Sequence[float]]) -> list[tuple[int, int]]:
        return [(round(x * S), round(y * S)) for x, y in points]

    def rect(self, fill: str | tuple[int, ...], rect: Sequence[float], radius: int = 0, outline: str | None = None, stroke: int = 2):
        pygame.draw.rect(self.surface, color(fill), self.r(rect), border_radius=radius * S)
        if outline:
            pygame.draw.rect(self.surface, color(outline), self.r(rect), stroke * S, border_radius=radius * S)

    def ellipse(self, fill: str | tuple[int, ...], rect: Sequence[float], outline: str | None = None, stroke: int = 2):
        pygame.draw.ellipse(self.surface, color(fill), self.r(rect))
        if outline:
            pygame.draw.ellipse(self.surface, color(outline), self.r(rect), stroke * S)

    def circle(self, fill: str | tuple[int, ...], center: Sequence[float], radius: float, outline: str | None = None, stroke: int = 2):
        c = (round(center[0] * S), round(center[1] * S))
        pygame.draw.circle(self.surface, color(fill), c, round(radius * S))
        if outline:
            pygame.draw.circle(self.surface, color(outline), c, round(radius * S), stroke * S)

    def poly(self, fill: str | tuple[int, ...], points: Iterable[Sequence[float]], outline: str | None = None, stroke: int = 2):
        pts = self.p(points)
        pygame.draw.polygon(self.surface, color(fill), pts)
        if outline:
            pygame.draw.polygon(self.surface, color(outline), pts, stroke * S)

    def line(self, fill: str | tuple[int, ...], start: Sequence[float], end: Sequence[float], stroke: int = 2):
        pygame.draw.line(self.surface, color(fill), self.p([start])[0], self.p([end])[0], stroke * S)

    def text(self, text: str, size: int, position: Sequence[float], fill: str, bold: bool = False):
        font = pygame.font.SysFont("arial", size * S, bold=bold)
        image = font.render(text, True, color(fill))
        self.surface.blit(image, self.p([position])[0])

    def glow(self, shape: Callable[["Pen", tuple[int, int, int, int]], None], rgb: str):
        rgba = color(rgb)
        for spread, alpha in ((6, 18), (3, 35), (1, 70)):
            layer = Pen(self.width, self.height)
            shape(layer, (rgba.r, rgba.g, rgba.b, alpha))
            self.surface.blit(layer.surface, (0, 0))

    def final(self) -> pygame.Surface:
        return pygame.transform.smoothscale(self.surface, (self.width, self.height))


def save(name: str, pen: Pen) -> pygame.Surface:
    image = pen.final()
    pygame.image.save(image, OUT_ASSETS / f"{name}.png")
    pygame.image.save(image, OUT_PUBLIC / f"{name}.png")
    return image


def logo() -> Pen:
    p = Pen(480, 90)
    # Door icon carries the split-dimensional premise without adding extra text.
    p.rect(C["door_frame"], (8, 14, 50, 64), radius=3, outline=C["ink"])
    p.rect(C["reality_dark"], (16, 22, 34, 50), radius=1, outline=C["ink"])
    p.poly(C["uniform_chaos"], ((33, 23), (49, 23), (49, 71), (33, 71)))
    p.circle(C["eye"], (43, 48), 2)
    p.line(C["chaos_top"], (57, 17), (63, 11), 2)
    p.line(C["chaos_top"], (59, 25), (68, 24), 2)
    # Render cool and chaos halves separately and clip at the optical center.
    font = pygame.font.SysFont("arialblack", 52 * S, bold=True)
    cool = font.render("SHIFT WORK", True, color(C["reality_top"]))
    chaos = font.render("SHIFT WORK", True, color(C["chaos_top"]))
    target = pygame.Rect(76 * S, 14 * S, 388 * S, 64 * S)
    scaled = pygame.transform.smoothscale(cool, (target.w, target.h))
    scaled_chaos = pygame.transform.smoothscale(chaos, (target.w, target.h))
    half = target.w // 2
    p.surface.blit(scaled, target.topleft, pygame.Rect(0, 0, half, target.h))
    p.surface.blit(scaled_chaos, (target.x + half, target.y), pygame.Rect(half, 0, target.w - half, target.h))
    p.line(C["white"], (270, 23), (270, 69), 1)
    return p


def title_background() -> Pen:
    p = Pen(800, 500)
    # Cross-dimensional background blend.
    left_a, left_b = color(C["reality_dark"]), color(C["reality_light"])
    right_a, right_b = color(C["chaos_dark"]), color(C["chaos_light"])
    for y in range(500 * S):
        t = y / (500 * S - 1)
        lc = left_a.lerp(left_b, t)
        rc = right_a.lerp(right_b, t)
        for x in range(800 * S):
            split = max(0.0, min(1.0, (x / S - 340) / 140))
            c = lc.lerp(rc, split)
            p.surface.set_at((x, y), c)
    # Office left: readable architecture, deliberately quiet lower third.
    p.rect(C["partition"], (40, 104, 255, 154), outline=C["ink"])
    p.rect("#727784", (52, 116, 105, 130), outline=C["ink"])
    p.rect("#727784", (169, 116, 114, 130), outline=C["ink"])
    p.line(C["reality_top"], (0, 290), (370, 290), 3)
    p.poly(C["reality_floor"], ((0, 290), (370, 290), (420, 500), (0, 500)))
    p.poly(C["reality_top"], ((0, 290), (370, 290), (380, 307), (0, 307)))
    p.rect("#202A3D", (88, 45, 96, 24), radius=3, outline=C["ink"])
    p.rect(C["window"], (97, 52, 78, 8), radius=2)
    # Chaos right: floating land mass and restrained orbit motifs.
    p.poly(C["chaos_floor"], ((456, 302), (800, 270), (800, 500), (418, 500)), outline=C["ink"])
    p.poly(C["chaos_top"], ((456, 302), (800, 270), (800, 294), (452, 326)), outline=C["ink"])
    for x, y, r in ((530, 122, 18), (690, 80, 29), (742, 198, 12), (590, 232, 8)):
        for add, alpha in ((12, 20), (6, 35)):
            p.circle((155, 95, 188, alpha), (x, y), r + add)
        p.circle(C["chaos_top"], (x, y), r, outline=C["ink"])
        p.circle("#D7A8EE", (x - r * 0.28, y - r * 0.28), max(2, r * 0.18))
    p.poly(C["pillar"], ((620, 175), (654, 170), (659, 270), (622, 272)), outline=C["ink"])
    p.line(C["chaos_top"], (634, 198), (647, 208), 2)
    p.line(C["chaos_top"], (647, 208), (633, 220), 2)
    return p


def filing_cabinet() -> Pen:
    p = Pen(40, 50)
    p.rect(C["cabinet"], (3, 2, 34, 46), radius=2, outline=C["ink"])
    p.rect("#B7BBC3", (6, 5, 28, 12), radius=1, outline=C["ink"], stroke=1)
    p.rect("#AEB3BD", (6, 18, 28, 12), radius=1, outline=C["ink"], stroke=1)
    p.rect("#9A9FAA", (6, 31, 28, 13), radius=1, outline=C["ink"], stroke=1)
    for y in (10, 23, 36):
        p.rect(C["reality_top"], (15, y, 10, 3), radius=1, outline=C["ink"], stroke=1)
    p.rect(C["uniform_reality"], (31, 35, 3, 7), radius=1)
    p.rect(C["ink"], (6, 46, 5, 3), radius=1)
    p.rect(C["ink"], (29, 46, 5, 3), radius=1)
    return p


def stone_pillar() -> Pen:
    p = Pen(40, 100)
    blocks = [(3, 2, 34, 24), (5, 26, 31, 23), (3, 49, 34, 25), (5, 74, 31, 24)]
    shades = ("#917957", C["pillar"], "#8B7352", "#766044")
    for block, shade in zip(blocks, shades):
        p.rect(shade, block, radius=2, outline=C["ink"])
    p.line("#4E412F", (8, 20), (16, 13), 2)
    p.line("#4E412F", (16, 13), (19, 22), 2)
    p.line("#4E412F", (31, 53), (25, 61), 2)
    p.line("#4E412F", (25, 61), (30, 68), 2)
    # Matching blue accent ties this dimensional replacement to the cabinet.
    p.rect(C["uniform_reality"], (31, 83, 3, 8), radius=1)
    for width, alpha in ((8, 25), (5, 55)):
        p.line((155, 95, 188, alpha), (20 - width / 4, 36), (20 + width / 4, 62), round(width))
    p.poly(C["chaos_top"], ((20, 35), (27, 45), (21, 50), (27, 56), (19, 66), (12, 55), (18, 50), (12, 44)), outline=C["ink"], stroke=1)
    return p


def exit_door() -> Pen:
    p = Pen(30, 50)
    for rect, alpha in (((0, 0, 30, 50), 22), ((2, 2, 26, 48), 40)):
        layer = Pen(30, 50)
        layer.rect((218, 182, 46, alpha), rect, radius=3)
        p.surface.blit(layer.surface, (0, 0))
    p.rect(C["door_frame"], (3, 2, 24, 48), radius=2, outline=C["ink"])
    p.rect(C["door"], (7, 6, 16, 40), radius=1, outline=C["ink"])
    p.rect(C["window"], (9, 9, 12, 12), radius=1, outline=C["ink"], stroke=1)
    p.line(C["white"], (11, 11), (15, 11), 1)
    p.circle(C["ink"], (20, 31), 1.5)
    return p


def pest() -> Pen:
    p = Pen(30, 24)
    # Legs and antennae first so the body reads cleanly at 1x.
    for a, b in (((8, 14), (3, 20)), ((13, 16), (11, 22)), ((20, 15), (23, 21)), ((9, 7), (4, 2)), ((14, 6), (13, 1))):
        p.line(C["ink"], a, b, 2)
    p.ellipse(C["pest"], (5, 6, 20, 13), outline=C["ink"])
    p.circle("#9F252A", (8, 12), 4, outline=C["ink"], stroke=1)
    p.line("#F06A5F", (13, 8), (17, 17), 1)
    p.circle(C["eye"], (20, 10), 2, outline=C["eye"], stroke=1)
    p.circle(C["eye"], (24, 11), 2, outline=C["eye"], stroke=1)
    return p


def custodian(uniform: str, mirrored: bool = False) -> Pen:
    p = Pen(28, 40)
    mop_x = 24 if not mirrored else 4
    hand_x = 21 if not mirrored else 7
    # Mop creates a strong directional silhouette.
    p.line("#725A3E", (mop_x, 12), (mop_x, 36), 2)
    p.line(C["skin"], (hand_x, 22), (mop_x, 22), 3)
    p.poly("#AAB3C3", ((mop_x - 4, 34), (mop_x + 4, 34), (mop_x + 6, 40), (mop_x - 6, 40)), outline=C["ink"], stroke=1)
    p.circle(C["skin"], (14, 10), 6, outline=C["ink"])
    p.rect(uniform, (8, 3, 12, 5), radius=2, outline=C["ink"])
    p.rect(uniform, (5, 6, 18, 3), radius=2, outline=C["ink"])
    p.line(C["ink"], (11, 11), (12, 11), 1)
    p.line(C["ink"], (16, 11), (17, 11), 1)
    p.rect(uniform, (7, 16, 14, 16), radius=2, outline=C["ink"])
    p.poly("#294D8A" if uniform == C["uniform_reality"] else "#562890", ((7, 25), (21, 25), (19, 32), (9, 32)))
    p.rect(C["white"], (14, 19, 5, 3), radius=1, outline=C["ink"], stroke=1)
    p.line(C["ink"], (12, 17), (14, 22), 1)
    p.line(C["ink"], (16, 17), (14, 22), 1)
    p.rect(C["ink"], (7, 31, 6, 8), radius=1)
    p.rect(C["ink"], (15, 31, 6, 8), radius=1)
    return p


def floor_spikes() -> Pen:
    p = Pen(44, 16)
    p.rect(C["chaos_floor"], (0, 13, 44, 3), outline=C["ink"], stroke=1)
    p.poly(C["chaos_top"], ((1, 14), (8, 2), (13, 14)), outline=C["ink"])
    p.poly(C["uniform_chaos"], ((10, 14), (19, 5), (24, 14)), outline=C["ink"])
    p.poly(C["chaos_top"], ((20, 14), (29, 1), (35, 14)), outline=C["ink"])
    p.poly(C["uniform_chaos"], ((32, 14), (39, 4), (44, 14)), outline=C["ink"])
    p.line("#D7A8EE", (8, 5), (8, 9), 1)
    p.line("#D7A8EE", (29, 4), (29, 8), 1)
    return p


def pressure_plate(glow: bool = False) -> Pen:
    p = Pen(60, 12 if glow else 4)
    if glow:
        for rect, alpha in (((3, 3, 54, 7), 22), ((8, 4, 44, 5), 50)):
            p.rect((155, 95, 188, alpha), rect, radius=3)
        p.rect(C["chaos_top"], (11, 5, 38, 3), radius=1)
    else:
        p.rect(C["ink"], (0, 0, 60, 4), radius=1)
        p.rect(C["chaos_top"], (3, 0, 54, 2), radius=1)
        for x in (17, 30, 43):
            p.line(C["eye"], (x - 2, 1), (x, 2), 1)
            p.line(C["eye"], (x, 2), (x + 2, 1), 1)
    return p


def gate(opened: bool = False) -> Pen:
    p = Pen(20, 150)
    alpha = 65 if opened else 255
    frame = color(C["chaos_floor"], alpha)
    energy = color(C["chaos_top"], 45 if opened else 255)
    p.rect(frame, (1, 1, 18, 148), radius=2, outline=C["ink"] if not opened else None)
    p.rect((23, 23, 38, alpha), (5, 5, 10, 140))
    for x in (6, 10, 14):
        p.line(energy, (x, 7), (x, 143), 2)
    if not opened:
        for y in range(13, 143, 18):
            p.line(C["eye"], (7, y), (13, y + 7), 1)
            p.line(C["eye"], (13, y + 7), (7, y + 13), 1)
    return p


def heart(full: bool) -> Pen:
    p = Pen(24, 24)
    fill = C["pest"] if full else C["reality_dark"]
    p.circle(fill, (7.5, 8.5), 5, outline=C["ink"])
    p.circle(fill, (16.5, 8.5), 5, outline=C["ink"])
    p.poly(fill, ((3, 10), (21, 10), (12, 22)), outline=C["ink"])
    if full:
        p.line("#F37878", (6, 6), (9, 5), 2)
    else:
        p.line(C["reality_top"], (8, 7), (16, 15), 2)
    return p


def world_dot(chaos: bool) -> Pen:
    p = Pen(24, 24)
    fill = C["chaos_top"] if chaos else C["uniform_reality"]
    p.circle(C["reality_dark"], (12, 12), 10, outline=C["ink"])
    p.circle(fill, (12, 12), 6, outline=C["ink"], stroke=1)
    p.circle(C["white"], (10, 10), 1.5)
    if chaos:
        p.line(C["eye"], (12, 3), (12, 6), 1)
        p.line(C["eye"], (19, 5), (17, 8), 1)
    else:
        p.line(C["reality_top"], (5, 18), (19, 18), 1)
    return p


def build_atlas(images: dict[str, pygame.Surface]) -> None:
    atlas = pygame.Surface((1200, 980), pygame.SRCALPHA)
    atlas.fill(color("#0B1020"))
    title = pygame.font.SysFont("arialblack", 38, bold=True).render("SHIFT WORK / ASSET ATLAS", True, color(C["white"]))
    subtitle = pygame.font.SysFont("consolas", 13).render("PYGAME • 1X SOURCE • RGBA EXPORTS", True, color(C["reality_top"]))
    atlas.blit(title, (40, 30))
    atlas.blit(subtitle, (42, 78))
    slots = [
        ("logo_wordmark", (40, 120, 540, 150)), ("title_background", (600, 120, 560, 350)),
        ("filing_cabinet_reality", (40, 300, 160, 170)), ("stone_pillar_chaos", (220, 300, 160, 170)),
        ("exit_door", (400, 300, 160, 170)), ("pest", (40, 500, 160, 170)),
        ("custodian_reality", (220, 500, 160, 170)), ("custodian_reality_mirrored", (400, 500, 160, 170)),
        ("custodian_chaos", (600, 500, 160, 170)), ("custodian_chaos_mirrored", (780, 500, 160, 170)),
        ("floor_spikes_chaos", (960, 500, 200, 170)), ("pressure_plate", (40, 700, 160, 120)),
        ("pressure_plate_glow", (220, 700, 160, 120)), ("gate_closed", (400, 700, 160, 250)),
        ("gate_open", (580, 700, 160, 250)), ("heart_full", (760, 700, 110, 120)),
        ("heart_empty", (890, 700, 110, 120)), ("world_dot_reality", (1020, 700, 140, 120)),
        ("world_dot_chaos", (1020, 840, 140, 120)),
    ]
    label_font = pygame.font.SysFont("consolas", 12, bold=True)
    size_font = pygame.font.SysFont("consolas", 11)
    for name, (x, y, w, h) in slots:
        pygame.draw.rect(atlas, color("#121A2C"), (x, y, w, h))
        pygame.draw.rect(atlas, color("#30384C"), (x, y, w, h), 1)
        image = images[name]
        available = pygame.Rect(x + 12, y + 12, w - 24, h - 46)
        scale = min(available.w / image.get_width(), available.h / image.get_height(), 3.0)
        preview = pygame.transform.scale(image, (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale))))
        atlas.blit(preview, preview.get_rect(center=available.center))
        atlas.blit(label_font.render(name, True, color(C["white"])), (x + 10, y + h - 29))
        size_text = f"{image.get_width()} x {image.get_height()}"
        atlas.blit(size_font.render(size_text, True, color(C["reality_top"])), (x + 10, y + h - 15))
    pygame.image.save(atlas, OUT_ASSETS / "shift_work_asset_atlas.png")
    pygame.image.save(atlas, OUT_PUBLIC / "shift_work_asset_atlas.png")


def main() -> None:
    pygame.init()
    pygame.font.init()
    OUT_ASSETS.mkdir(parents=True, exist_ok=True)
    OUT_PUBLIC.mkdir(parents=True, exist_ok=True)
    makers: dict[str, Callable[[], Pen]] = {
        "logo_wordmark": logo,
        "title_background": title_background,
        "filing_cabinet_reality": filing_cabinet,
        "stone_pillar_chaos": stone_pillar,
        "exit_door": exit_door,
        "pest": pest,
        "custodian_reality": lambda: custodian(C["uniform_reality"]),
        "custodian_reality_mirrored": lambda: custodian(C["uniform_reality"], True),
        "custodian_chaos": lambda: custodian(C["uniform_chaos"]),
        "custodian_chaos_mirrored": lambda: custodian(C["uniform_chaos"], True),
        "floor_spikes_chaos": floor_spikes,
        "pressure_plate": pressure_plate,
        "pressure_plate_glow": lambda: pressure_plate(True),
        "gate_closed": gate,
        "gate_open": lambda: gate(True),
        "heart_full": lambda: heart(True),
        "heart_empty": lambda: heart(False),
        "world_dot_reality": lambda: world_dot(False),
        "world_dot_chaos": lambda: world_dot(True),
    }
    images = {name: save(name, maker()) for name, maker in makers.items()}
    build_atlas(images)
    print(f"Generated {len(images)} sprites and atlas in {OUT_ASSETS} and {OUT_PUBLIC}")
    pygame.quit()


if __name__ == "__main__":
    main()
