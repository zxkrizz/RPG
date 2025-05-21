# file: rsc_engine/game.py
from pathlib import Path
import pygame

from rsc_engine import constants as C
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player, FriendlyNPC, HostileNPC
from rsc_engine.utils import screen_to_iso, iso_to_screen
from rsc_engine.ui import UI
from rsc_engine.inventory import Inventory, Item

ASSETS = Path(__file__).resolve().parent / "assets"

# <<< NOWY KOD: Zdefiniujmy docelowe wymiary postaci >>>
# Możesz dostosować te wartości, aby uzyskać pożądany wygląd
TARGET_CHAR_HEIGHT = int(C.TILE_HEIGHT * 2.2)  # Np. postać nieco wyższa niż 2 kafelki


# Szerokość będzie obliczana proporcjonalnie, aby nie zniekształcić grafiki

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

        # Przeniesienie _load_content() wyżej, aby self.player_img było dostępne
        self._load_initial_assets()  # Zmieniona nazwa dla jasności

        self.camera = Camera(width, height)
        if self.tilemap:
            self.camera.set_world_size(self.tilemap.width * C.TILE_WIDTH,
                                       self.tilemap.height * C.TILE_HEIGHT)

        self.entities = pygame.sprite.Group()

        # <<< MODYFIKACJA: Skalowanie obrazka gracza >>>
        player_original_img = self._load_image("player.png")
        scaled_player_img = self._scale_image_proportionally(player_original_img, TARGET_CHAR_HEIGHT)

        self.player = Player(
            name="Hero",
            ix=5,
            iy=5,
            image=scaled_player_img,  # Użyj przeskalowanego obrazka
            max_hp=150,
            attack_power=12,
            defense=5
        )
        self.entities.add(self.player)

        # <<< MODYFIKACJA: Skalowanie obrazków NPC >>>
        try:
            friendly_npc_original_img = self._load_image("friendly_npc.png")
            scaled_friendly_npc_img = self._scale_image_proportionally(friendly_npc_original_img, TARGET_CHAR_HEIGHT)
        except pygame.error:
            # Tymczasowy obrazek, jeśli plik nie istnieje - jego też warto przeskalować
            temp_surface = pygame.Surface((C.TILE_WIDTH, TARGET_CHAR_HEIGHT),
                                          pygame.SRCALPHA)  # Użyj docelowych wymiarów
            temp_surface.fill((0, 255, 0, 180))
            scaled_friendly_npc_img = temp_surface

        friendly_npc = FriendlyNPC(
            name="Old Man",
            ix=8, iy=8,
            image=scaled_friendly_npc_img,  # Użyj przeskalowanego obrazka
            dialogue=["Witaj, podróżniku!", "Uważaj na potwory w okolicy."]
        )
        self.entities.add(friendly_npc)

        try:
            hostile_npc_original_img = self._load_image("hostile_npc.png")
            # Obrazek hostile_npc.png jest bardzo mały (36x58), więc skalowanie go w górę
            # do TARGET_CHAR_HEIGHT może go bardzo zniekształcić.
            # Lepiej przygotować go w większej rozdzielczości lub ustawić dla niego inny TARGET_CHAR_HEIGHT.
            # Na razie użyjemy tego samego, ale bądź świadom efektu.
            # Jeśli oryginalny obraz jest mniejszy niż TARGET_CHAR_HEIGHT, smoothscale może być lepsze.
            scaled_hostile_npc_img = self._scale_image_proportionally(hostile_npc_original_img, TARGET_CHAR_HEIGHT,
                                                                      use_smoothscale_if_upscaling=True)
        except pygame.error:
            temp_surface = pygame.Surface((int(C.TILE_WIDTH * 0.8), TARGET_CHAR_HEIGHT),
                                          pygame.SRCALPHA)  # Mniejsza szerokość dla "szczuplejszego" wroga
            temp_surface.fill((255, 0, 0, 180))
            scaled_hostile_npc_img = temp_surface

        goblin = HostileNPC(
            name="Goblin Scout",
            ix=12, iy=12,
            image=scaled_hostile_npc_img,  # Użyj przeskalowanego obrazka
            level=2,
            max_hp=40,
            attack_power=6,
            defense=1,
            aggro_radius=4
        )
        self.entities.add(goblin)

        self.ui = UI(self)
        self.inventory = Inventory(rows=4, cols=5)
        icon_path = ASSETS / "item_icon.png"
        if icon_path.exists():
            ico_original = pygame.image.load(str(icon_path)).convert_alpha()
            # Możesz też przeskalować ikony przedmiotów, jeśli potrzebujesz
            # ico = pygame.transform.smoothscale(ico_original, (SLOT_SIZE - PADDING, SLOT_SIZE - PADDING))
            ico = ico_original  # Na razie bez skalowania ikon
        else:
            ico = pygame.Surface((32, 32), pygame.SRCALPHA)
            ico.fill((255, 215, 0, 200))
        self.inventory.add_item(Item("Magic Stone", ico))

    # <<< NOWA METODA POMOCNICZA do skalowania proporcjonalnego >>>
    def _scale_image_proportionally(self, image: pygame.Surface, target_height: int,
                                    use_smoothscale_if_upscaling: bool = False) -> pygame.Surface:
        original_width, original_height = image.get_size()
        if original_height == 0:  # Zabezpieczenie przed dzieleniem przez zero
            return image
        aspect_ratio = original_width / original_height
        target_width = int(target_height * aspect_ratio)

        if target_width == 0 or target_height == 0:  # Zabezpieczenie przed zerowymi wymiarami
            return image

        # Dla pixel artu, przy powiększaniu (upscaling), `scale` może dać ostrzejszy efekt.
        # Przy zmniejszaniu (downscaling), `smoothscale` jest zazwyczaj lepsze.
        if original_height < target_height and not use_smoothscale_if_upscaling:  # Powiększanie i chcemy ostrych pikseli
            return pygame.transform.scale(image, (target_width, target_height))
        else:  # Zmniejszanie lub powiększanie z smoothscale
            return pygame.transform.smoothscale(image, (target_width, target_height))

    def _load_image(self, name: str) -> pygame.Surface:
        """Wczytuje obrazek. Skalowanie odbywa się po tej funkcji."""
        return pygame.image.load(str(ASSETS / name)).convert_alpha()

    # Zmieniona nazwa metody dla jasności
    def _load_initial_assets(self):
        """Wczytuje zasoby, które nie są dynamicznie skalowane per-encja (np. tileset)."""
        self.tileset_img = self._load_image("tileset.png")
        # self.player_img już nie jest potrzebne jako pole klasy, bo wczytujemy bezpośrednio
        # i skalujemy przy tworzeniu gracza. Podobnie dla NPC.
        map_path = ASSETS / "map.csv"
        self.tilemap = TileMap(str(map_path), self.tileset_img)

    def run(self):
        # ... (reszta metody run bez zmian) ...
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            self._process_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    def _process_events(self):
        # ... (bez zmian) ...
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.player or not self.player.is_alive:
                    continue

                mx, my = event.pos
                world_mx = mx + self.camera.rect.x
                world_my = my + self.camera.rect.y

                tx, ty = screen_to_iso(world_mx, world_my)

                clicked_entity = None
                for entity in self.entities:
                    if entity.rect.collidepoint(world_mx, world_my) and entity != self.player:
                        clicked_entity = entity
                        break

                if clicked_entity and clicked_entity.is_alive:
                    # print(f"Clicked on {clicked_entity.name}") # Usunięto lub można zostawić do debugowania
                    distance_to_clicked = abs(self.player.ix - clicked_entity.ix) + abs(
                        self.player.iy - clicked_entity.iy)

                    if isinstance(clicked_entity, HostileNPC):
                        self.player.target_entity = clicked_entity
                        if distance_to_clicked <= 1:
                            self.player.path = []
                            self.player.target_tile_coords = None
                            self.player.attack(clicked_entity)
                        else:
                            self.player.set_path(clicked_entity.ix, clicked_entity.iy, self.tilemap)
                            # print(f"Player is now targeting {clicked_entity.name} to attack.") # Usunięto lub można zostawić
                    elif isinstance(clicked_entity, FriendlyNPC):
                        self.player.target_entity = clicked_entity
                        if distance_to_clicked <= 1:
                            self.player.path = []
                            self.player.target_tile_coords = None
                            clicked_entity.interact(self.player)
                        else:
                            self.player.set_path(clicked_entity.ix, clicked_entity.iy, self.tilemap)
                            # print(f"Player is approaching {clicked_entity.name} to interact.") # Usunięto lub można zostawić
                else:
                    self.player.target_entity = None
                    self.player.set_path(tx, ty, self.tilemap)

    def _update(self, dt: float):
        # ... (bez zmian) ...
        if not self.player:
            return

        for entity in self.entities:
            entity.update(dt, self.tilemap, self.entities)

        if self.player and not self.player.is_alive and self.running:
            print("GAME OVER - Player is dead")
            pass

        if self.player:
            self.camera.update(self.player.rect)

    def _draw(self):
        # ... (bez zmian) ...
        self.screen.fill((48, 48, 64))
        if self.tilemap:
            self.tilemap.draw(self.screen, self.camera)

        for entity in self.entities:
            if entity.is_alive:
                sx, sy = iso_to_screen(entity.ix, entity.iy)
                sx -= self.camera.rect.x
                sy -= self.camera.rect.y + C.TILE_HEIGHT // 2
                # Mały cień pod stopami, jego rozmiar jest stały
                shadow_rect = pygame.Rect(sx - C.TILE_WIDTH // 4, sy - C.TILE_HEIGHT // 4, C.TILE_WIDTH // 2,
                                          C.TILE_HEIGHT // 2)
                pygame.draw.ellipse(self.screen, (0, 0, 0, 100), shadow_rect)

        if self.player and self.player.is_alive and self.player.target_tile_coords:
            tx, ty = self.player.target_tile_coords
            sx, sy = iso_to_screen(tx, ty)
            sx -= self.camera.rect.x
            sy -= self.camera.rect.y
            size = C.TILE_WIDTH // 2
            pygame.draw.line(self.screen, (255, 0, 0),
                             (sx - size, sy - size), (sx + size, sy + size), 3)
            pygame.draw.line(self.screen, (255, 0, 0),
                             (sx - size, sy + size), (sx + size, sy - size), 3)

        sorted_entities = sorted(list(self.entities), key=lambda e: (e.rect.centery, e.rect.centerx))
        for entity in sorted_entities:
            if entity.is_alive:
                self.screen.blit(entity.image, self.camera.apply(entity.rect))
            elif hasattr(entity, 'corpse_image') and entity.corpse_image:
                self.screen.blit(entity.corpse_image, self.camera.apply(entity.rect))

        if self.ui:
            self.ui.draw(self.screen)

        pygame.display.flip()
