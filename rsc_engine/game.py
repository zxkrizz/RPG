# file: rsc_engine/game.py
from pathlib import Path
import pygame

from rsc_engine import constants as C
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player
from rsc_engine.utils import screen_to_iso, iso_to_screen
from rsc_engine.ui import UI
from rsc_engine.inventory import Inventory, Item

ASSETS = Path(__file__).with_suffix("").parent / "assets"

class Game:
    def __init__(self,
                 width: int = C.SCREEN_WIDTH,
                 height: int = C.SCREEN_HEIGHT,
                 title: str = "RuneScape Classic Clone"):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True

        self._load_content()
        self.camera = Camera(width, height)
        self.camera.set_world_size(self.tilemap.width * C.TILE_WIDTH,
                                   self.tilemap.height * C.TILE_HEIGHT)

        self.entities = pygame.sprite.Group()
        self.player = Player(ix=5, iy=5, image=self.player_img)
        self.entities.add(self.player)

        self.ui = UI(self)

        # inventory
        self.inventory = Inventory(rows=4, cols=5)
        icon_path = ASSETS / "item_icon.png"
        if icon_path.exists():
            ico = pygame.image.load(str(icon_path)).convert_alpha()
        else:
            # wygeneruj tymczasową, złotą ikonkę 32×32
            ico = pygame.Surface((32, 32), pygame.SRCALPHA)
            ico.fill((255, 215, 0, 200))
        self.inventory.add_item(Item("Magic Stone", ico))


    def _load_image(self, name: str) -> pygame.Surface:
        return pygame.image.load(str(ASSETS / name)).convert_alpha()

    def _load_content(self):
        self.tileset_img = self._load_image("tileset.png")
        self.player_img = self._load_image("player.png")
        map_path = ASSETS / "map.csv"
        self.tilemap = TileMap(str(map_path), self.tileset_img)

    def run(self):
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            self._process_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    def _process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                tx, ty = screen_to_iso(mx + self.camera.rect.x,
                                       my + self.camera.rect.y)
                self.player.set_path(tx, ty)

    def _update(self, dt: float):
        self.entities.update(dt, self.tilemap)
        self.camera.update(self.player.rect)

    def _draw(self):
        self.screen.fill((48, 48, 64))
        self.tilemap.draw(self.screen, self.camera)

        # shadows
        for entity in self.entities:
            sx, sy = iso_to_screen(entity.ix, entity.iy)
            sx -= self.camera.rect.x
            sy -= self.camera.rect.y + C.TILE_HEIGHT // 2
            pygame.draw.ellipse(self.screen, (0, 0, 0, 100),
                                (sx - 10, sy - 5, 20, 8))

        # target X
        if self.player.target:
            tx, ty = self.player.target
            sx, sy = iso_to_screen(tx, ty)
            sx -= self.camera.rect.x
            sy -= self.camera.rect.y
            size = C.TILE_WIDTH // 2
            pygame.draw.line(self.screen, (255, 0, 0),
                             (sx - size, sy - size), (sx + size, sy + size), 3)
            pygame.draw.line(self.screen, (255, 0, 0),
                             (sx - size, sy + size), (sx + size, sy - size), 3)

        # entities
        for entity in self.entities:
            self.screen.blit(entity.image, self.camera.apply(entity.rect))

        # HUD and inventory
        self.ui.draw(self.screen)
        pygame.display.flip()
