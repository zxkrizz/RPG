from __future__ import annotations
import pygame
from rsc_engine.utils import iso_to_screen

def bresenham(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int,int]]:
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    path: list[tuple[int,int]] = []
    while True:
        if (x, y) != (x0, y0):
            path.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return path

class Entity(pygame.sprite.Sprite):
    def __init__(self, ix: int, iy: int, image: pygame.Surface):
        super().__init__()
        self.ix = ix
        self.iy = iy
        self.image = image
        self.rect = self.image.get_rect()
        self.update_rect()

    def update_rect(self):
        sx, sy = iso_to_screen(self.ix, self.iy)
        self.rect.center = (sx, sy)

    def update(self, dt: float, tilemap: "TileMap"):
        pass

class Player(Entity):
    def __init__(self, ix: int, iy: int, image: pygame.Surface):
        super().__init__(ix, iy, image)
        self.move_cooldown = 0.0
        self.path: list[tuple[int,int]] = []
        self.target: tuple[int,int] | None = None
        # podstawowe statystyki
        self.max_hp = 100
        self.hp     = 100

    def set_path(self, tx: int, ty: int):
        # generujemy ścieżkę i zapisujemy cel do rysowania X
        self.path = bresenham(self.ix, self.iy, tx, ty)
        self.target = (tx, ty)

    def update(self, dt: float, tilemap: "TileMap"):
        self.move_cooldown = max(0.0, self.move_cooldown - dt)
        if self.path and self.move_cooldown == 0.0:
            nx, ny = self.path.pop(0)
            nx = max(0, min(nx, tilemap.width - 1))
            ny = max(0, min(ny, tilemap.height - 1))
            self.ix, self.iy = nx, ny
            self.update_rect()
            self.move_cooldown = 0.15

            # jeżeli dotarliśmy, wyczyść target
            if not self.path:
                self.target = None