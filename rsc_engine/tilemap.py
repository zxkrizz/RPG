"""Very small isometric tilemap implementation that loads a CSV layout."""
import csv
import pygame
from pathlib import Path

from rsc_engine import constants as C
from rsc_engine.utils import iso_to_screen

class TileMap:
    """Loads a simple CSV tilemap where each cell stores a tile id."""
    def __init__(self, csv_path: str, tileset: pygame.Surface):
        self.csv_path = Path(csv_path)
        self.tileset = tileset
        self.layout = self._load_csv(self.csv_path)
        self.width  = len(self.layout[0])
        self.height = len(self.layout)
        # Pre-split tileset into tile surfaces.
        tileset_w, tileset_h = self.tileset.get_size()
        self.tile_surfaces = []
        for y in range(0, tileset_h, C.TILE_HEIGHT):
            for x in range(0, tileset_w, C.TILE_WIDTH):
                tile = self.tileset.subsurface(pygame.Rect(x, y, C.TILE_WIDTH, C.TILE_HEIGHT))
                self.tile_surfaces.append(tile)

    def _load_csv(self, path: Path):
        with open(path, newline="") as fp:
            reader = csv.reader(fp)
            return [[int(cell) for cell in row] for row in reader]

    def draw(self, surface: pygame.Surface, camera):
        """Draw visible portion of the map relative to camera."""
        rows = len(self.layout)
        cols = len(self.layout[0])
        for iy in range(rows):
            for ix in range(cols):
                tile_id = self.layout[iy][ix]
                if tile_id < 0:
                    continue  # skip empty
                screen_x, screen_y = iso_to_screen(ix, iy)
                screen_x -= camera.rect.x
                screen_y -= camera.rect.y
                if (screen_x > -C.TILE_WIDTH and screen_y > -C.TILE_HEIGHT
                    and screen_x < C.SCREEN_WIDTH and screen_y < C.SCREEN_HEIGHT):
                    surface.blit(self.tile_surfaces[tile_id], (screen_x, screen_y))
