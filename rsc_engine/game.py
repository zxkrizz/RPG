# file: rsc_engine/game.py
from pathlib import Path  # To zostaje, jeśli C.ASSETS jest używane lokalnie do budowania ścieżek
import pygame

from rsc_engine import constants as C  # Importujemy constants jako C
# Importuj stany i PlayerData
from rsc_engine.states import GameStateManager, BaseState, PlayerData
# Importuj konkretne implementacje stanów
from rsc_engine.game_states import MenuState, CharacterCreationState, GameplayState

# Importy potrzebne dla GameplayState (lub przekazywane do niego)
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player, FriendlyNPC, HostileNPC, Entity
from rsc_engine.utils import screen_to_iso, iso_to_screen
from rsc_engine.ui import UI, ContextMenu, DamageSplat
from rsc_engine.inventory import Inventory, Item
from typing import Tuple, Callable, Optional, List


# Stałe ASSETS, TARGET_CHAR_HEIGHT itp. zostały przeniesione do constants.py
# Będziemy się do nich odwoływać przez C.NAZWA_STALEJ

class Game:
    def __init__(self,
                 window_width: int = 1600,
                 window_height: int = 900,
                 title: str = "RuneScape Classic Clone"):
        pygame.init()
        self.window_screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
        pygame.display.set_caption(title)
        self.logical_screen = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.player: Optional[Player] = None
        self.entities: Optional[pygame.sprite.Group] = None
        self.tilemap: Optional[TileMap] = None
        self.camera: Optional[Camera] = None
        self.ui: Optional[UI] = None
        self.context_menu: Optional[ContextMenu] = None
        self.inventory: Optional[Inventory] = None
        self.damage_splats: List[DamageSplat] = []

        self.damage_icon_image = None
        self.damage_font = None

        self.shared_game_data = {
            "player_data": None
        }

        initial_state_key = "GAMEPLAY" if C.DEV_SKIP_MENU_AND_CREATOR else "MENU"
        self.state_manager = GameStateManager(initial_state_key, self)
        self._register_states()

        if C.DEV_SKIP_MENU_AND_CREATOR:
            self.state_manager.set_state("GAMEPLAY", PlayerData(name="DevBypass"))
        else:
            self.state_manager.set_state("MENU")

    def _register_states(self):
        self.state_manager.register_state("MENU", MenuState(self))
        self.state_manager.register_state("CHARACTER_CREATION", CharacterCreationState(self))
        self.state_manager.register_state("GAMEPLAY", GameplayState(self))

    def run(self):
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.VIDEORESIZE:
                    new_width, new_height = event.size
                    self.window_screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)

            if not self.running: break

            self.state_manager.handle_events(events)
            self.state_manager.update(dt)

            self.state_manager.draw(self.logical_screen)

            scaled_surface = pygame.transform.scale(self.logical_screen, self.window_screen.get_size())
            self.window_screen.blit(scaled_surface, (0, 0))

            if self.state_manager.active_state_key == "GAMEPLAY" and \
                    hasattr(self,
                            'context_menu') and self.context_menu and self.context_menu.is_visible:  # Dodano hasattr
                self.context_menu.draw(self.window_screen)

            pygame.display.flip()
        pygame.quit()

    def get_scaled_mouse_pos(self, physical_mouse_pos: Tuple[int, int]) -> Tuple[int, int]:
        window_w, window_h = self.window_screen.get_size()
        logical_w, logical_h = self.logical_screen.get_size()
        if window_w > 0 and window_h > 0:
            mouse_scale_x = logical_w / window_w
            mouse_scale_y = logical_h / window_h
            return (int(physical_mouse_pos[0] * mouse_scale_x),
                    int(physical_mouse_pos[1] * mouse_scale_y))
        return physical_mouse_pos

    def _load_image(self, name: str) -> pygame.Surface:
        # Użyj C.ASSETS do budowania ścieżki
        return pygame.image.load(str(C.ASSETS / name)).convert_alpha()

    def _scale_image_proportionally(self, image: pygame.Surface, target_height: int,
                                    use_smoothscale_if_upscaling: bool = False) -> pygame.Surface:
        original_width, original_height = image.get_size()
        if original_height == 0: return image
        aspect_ratio = original_width / original_height
        target_width = int(target_height * aspect_ratio)
        if target_width == 0 or target_height == 0: return image
        if original_height < target_height and not use_smoothscale_if_upscaling:
            return pygame.transform.scale(image, (target_width, target_height))
        return pygame.transform.smoothscale(image, (target_width, target_height))

    # Metody specyficzne dla rozgrywki, które są teraz wywoływane przez GameplayState na obiekcie 'game'
    def is_tile_occupied_by_entity(self, ix: int, iy: int, excluding_entity: Optional[Entity] = None) -> bool:
        if not self.entities: return False  # entities jest teraz atrybutem GameplayState, ale game ma referencję
        for entity in self.entities:
            if entity == excluding_entity: continue
            if entity.is_alive and entity.ix == ix and entity.iy == iy:
                return True
        return False

    def show_examine_text(self, target_entity: Optional[Entity]):
        if target_entity and self.ui:  # ui jest atrybutem GameplayState, ale game ma referencję
            message = f"It's a {target_entity.name} (Lvl: {target_entity.level}, HP: {target_entity.hp}/{target_entity.max_hp})."
            if hasattr(self.ui, 'show_dialogue'):
                self.ui.show_dialogue("System", [message])
            else:
                print(f"[INFO] Game.show_examine_text: '{message}'")

    def initiate_dialogue_with_npc(self, npc: Optional[FriendlyNPC]):
        if npc and isinstance(npc, FriendlyNPC) and npc.is_alive and self.player and self.player.is_alive:
            dx = abs(self.player.ix - npc.ix)
            dy = abs(self.player.iy - npc.iy)
            interaction_distance = max(dx, dy)
            if interaction_distance <= 1:
                npc.interact(self.player)
            else:
                self.player_walk_to_and_act(
                    (npc.ix, npc.iy),
                    lambda ignored_target: self.initiate_dialogue_with_npc(npc),
                    npc
                )
        elif npc and not npc.is_alive:
            self.show_examine_text(npc)

    def player_walk_to_and_act(self, target_coords_iso: Tuple[int, int], final_action: Callable,
                               action_target: Optional[Entity] = None):
        if not self.player or not self.player.is_alive: return
        # player jest teraz atrybutem GameplayState, game ma do niego referencję
        self.player.target_entity_for_action = action_target
        self.player.action_after_reaching_target = final_action
        self.player.set_path(target_coords_iso[0], target_coords_iso[1], self.tilemap)

    def _load_damage_splat_assets_global(self):
        try:
            # Użyj C.ASSETS i C.TARGET_SPLAT_ICON_WIDTH/HEIGHT
            damage_icon_path = C.ASSETS / "ui" / "damage_icon.png"
            loaded_icon = pygame.image.load(str(damage_icon_path)).convert_alpha()  # Bezpośrednie ładowanie
            self.damage_icon_image = pygame.transform.smoothscale(loaded_icon, (C.TARGET_SPLAT_ICON_WIDTH,
                                                                                C.TARGET_SPLAT_ICON_HEIGHT))
        except pygame.error as e:
            print(f"Could not load damage_icon.png from {damage_icon_path}: {e}. Using placeholder.")
            self.damage_icon_image = pygame.Surface((C.TARGET_SPLAT_ICON_WIDTH, C.TARGET_SPLAT_ICON_HEIGHT),
                                                    pygame.SRCALPHA)
            self.damage_icon_image.fill((200, 0, 0, 150))
        try:
            self.damage_font = pygame.font.SysFont("Arial Black", 14, bold=True)
        except Exception as e:
            print(f"Could not load damage font: {e}. Using default system font.")
            self.damage_font = pygame.font.SysFont(pygame.font.get_default_font(), 14, bold=True)

    def create_damage_splat(self, value: int, target_entity: Entity):
        if not self.damage_font or not self.damage_icon_image:
            self._load_damage_splat_assets_global()
            if not self.damage_font:
                print("[ERROR] Damage font still not loaded after attempt, cannot create damage splat.")
                return

        if not self.camera or not target_entity.rect: return

        logical_entity_rect_on_cam = self.camera.apply(target_entity.rect)
        center_x = logical_entity_rect_on_cam.centerx
        top_y = logical_entity_rect_on_cam.top

        splat = DamageSplat(value, center_x, top_y, self.damage_icon_image, self.damage_font, self.camera)
        self.damage_splats.append(splat)  # damage_splats jest teraz w Game, zarządzane przez GameplayState.update