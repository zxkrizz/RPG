# file: rsc_engine/game.py
from pathlib import Path
import pygame
import json
import os

from rsc_engine import constants as C
# Importuj stany i PlayerData
from rsc_engine.states import GameStateManager, BaseState, PlayerData
# Importuj konkretne implementacje stanów
# Zakładamy, że te stany są teraz zdefiniowane w rsc_engine/game_states.py
from rsc_engine.game_states import MenuState, CharacterCreationState, GameplayState, PauseMenuState, LoadGameState

# Importy potrzebne dla różnych części, głównie dla metod pomocniczych w Game
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player, FriendlyNPC, HostileNPC, Entity
from rsc_engine.utils import screen_to_iso, iso_to_screen
from rsc_engine.ui import UI, ContextMenu, DamageSplat
from rsc_engine.inventory import Inventory, Item
from typing import Tuple, Callable, Optional, List, Dict, Any

# Stałe ASSETS, TARGET_CHAR_HEIGHT itp. są teraz w constants.py (C.ASSETS, C.TARGET_CHAR_HEIGHT)
SAVE_DIR = Path(".") / "saves"  # Tworzy katalog 'saves' w głównym folderze projektu (RPG)


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

        # Atrybuty, które będą zarządzane przez GameplayState lub inne stany.
        # Game może przechowywać referencje, jeśli są potrzebne globalnie.
        self.player: Optional[Player] = None
        self.entities: Optional[pygame.sprite.Group] = pygame.sprite.Group()  # Inicjalizuj jako pustą grupę
        self.tilemap: Optional[TileMap] = None  # Będzie ustawiane przez GameplayState
        self.camera: Optional[Camera] = None  # Będzie ustawiane przez GameplayState
        self.ui: Optional[UI] = None  # Będzie ustawiane przez GameplayState
        self.context_menu: Optional[ContextMenu] = None  # Będzie ustawiane przez GameplayState
        self.inventory: Optional[Inventory] = None  # Będzie ustawiane przez GameplayState
        self.damage_splats: List[DamageSplat] = []

        self.damage_icon_image = None  # Ładowane w _load_damage_splat_assets_global
        self.damage_font = None  # Ładowane w _load_damage_splat_assets_global
        self._load_damage_splat_assets_global()  # Załaduj od razu, stany mogą tego potrzebować

        self.shared_game_data = {
            "player_data": None,
            "current_save_slot": None
        }

        SAVE_DIR.mkdir(parents=True, exist_ok=True)

        # Inicjalizuj GameStateManager bez initial_state_key
        self.state_manager = GameStateManager(None, self)
        self._register_states()  # Najpierw zarejestruj wszystkie stany

        # Teraz ustaw stan początkowy
        initial_state_key = "GAMEPLAY" if C.DEV_SKIP_MENU_AND_CREATOR else "MENU"
        initial_data = None
        if initial_state_key == "GAMEPLAY" and C.DEV_SKIP_MENU_AND_CREATOR:
            dev_save_path = SAVE_DIR / "dev_save.json"
            if dev_save_path.exists():
                try:
                    with open(dev_save_path, 'r') as f:
                        data_dict = json.load(f)
                    if "player_data" in data_dict:
                        initial_data = PlayerData.from_dict(data_dict["player_data"])
                        print(f"[INFO] Loaded dev save: {initial_data}")
                    else:
                        print(f"[WARNING] dev_save.json is missing 'player_data' key. Using default dev data.")
                        initial_data = PlayerData(name="DevBypass")
                except Exception as e:
                    print(f"[ERROR] Could not load or parse dev_save.json: {e}. Using default dev data.")
                    initial_data = PlayerData(name="DevBypass")
            else:
                print("[INFO] dev_save.json not found. Using default dev data for DEV_SKIP mode.")
                initial_data = PlayerData(name="DevBypass")

        self.state_manager.set_state(initial_state_key, initial_data)

    def _register_states(self):
        self.state_manager.register_state("MENU", MenuState(self))
        self.state_manager.register_state("CHARACTER_CREATION", CharacterCreationState(self))
        self.state_manager.register_state("GAMEPLAY", GameplayState(self))
        self.state_manager.register_state("PAUSE_MENU", PauseMenuState(self))
        self.state_manager.register_state("LOAD_GAME", LoadGameState(self))
        # self.state_manager.register_state("OPTIONS", OptionsState(self))

    def get_save_file_path(self, slot_number: int) -> Path:
        return SAVE_DIR / f"save_slot_{slot_number}.json"

    def save_game(self, slot_number: int):
        if self.state_manager.active_state_key != "GAMEPLAY" or not self.player:
            print("[ERROR] Cannot save game: Not in GameplayState or Player not initialized.")
            if self.ui and hasattr(self.ui, 'show_dialogue'):
                self.ui.show_dialogue("System", ["Error: Cannot save game state now."])
            return

        current_map_id = "default_map"
        if self.tilemap and hasattr(self.tilemap, 'map_id'):
            current_map_id = self.tilemap.map_id
        elif self.tilemap and hasattr(self.tilemap, 'csv_path'):
            current_map_id = Path(self.tilemap.csv_path).stem

        player_data_to_save = PlayerData(
            name=self.player.name,
            level=self.player.level,
            start_ix=self.player.ix,
            start_iy=self.player.iy,
            max_hp=self.player.max_hp,
            current_hp=self.player.hp,
            xp=getattr(self.player, 'xp', 0),
            map_id=current_map_id
        )

        game_state_to_save = {
            "player_data": player_data_to_save.to_dict(),
            "timestamp": pygame.time.get_ticks(),
            "game_version": "0.1"
        }

        save_path = self.get_save_file_path(slot_number)
        try:
            with open(save_path, 'w') as f:
                json.dump(game_state_to_save, f, indent=4, ensure_ascii=False)
            print(f"[INFO] Game saved to slot {slot_number} ({save_path})")
            if self.ui and hasattr(self.ui, 'show_dialogue'):
                self.ui.show_dialogue("System", [f"Game saved to slot {slot_number}."])
        except Exception as e:
            print(f"[ERROR] Could not save game to slot {slot_number}: {e}")
            if self.ui and hasattr(self.ui, 'show_dialogue'):
                self.ui.show_dialogue("System", [f"Error saving game: {e}"])

    def load_game_data_from_slot(self, slot_number: int) -> Optional[PlayerData]:
        save_path = self.get_save_file_path(slot_number)
        if not save_path.exists():
            print(f"[ERROR] Save slot {slot_number} not found at {save_path}")
            return None

        try:
            with open(save_path, 'r') as f:
                game_state_loaded = json.load(f)
            if "player_data" not in game_state_loaded:
                print(f"[ERROR] Save slot {slot_number} is corrupted or has old format (missing 'player_data').")
                return None

            player_data = PlayerData.from_dict(game_state_loaded["player_data"])
            print(f"[INFO] Loaded game data from slot {slot_number}: {player_data}")
            self.shared_game_data["current_save_slot"] = slot_number
            return player_data
        except Exception as e:
            print(f"[ERROR] Could not load game from slot {slot_number}: {e}")
            return None

    def get_save_slot_info(self) -> List[Dict[str, Any]]:
        save_infos = []
        for i in range(1, 4):
            path = self.get_save_file_path(i)
            info = {"slot": i, "exists": False, "player_name": "Empty", "level": "-", "map_id": "-"}
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    if "player_data" in data:
                        info["exists"] = True
                        pd = data["player_data"]
                        info["player_name"] = pd.get("name", "N/A")
                        info["level"] = pd.get("level", "N/A")
                        info["map_id"] = pd.get("map_id", "N/A")
                except Exception as e:
                    print(f"[WARNING] Could not parse save slot {i} info: {e}")
                    info["player_name"] = "Corrupted"
            save_infos.append(info)
        return save_infos

    def run(self):
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT: self.running = False
                if event.type == pygame.VIDEORESIZE:
                    self.window_screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if not self.running: break

            self.state_manager.handle_events(events)
            self.state_manager.update(dt)

            if self.state_manager.active_state:
                self.state_manager.draw(self.logical_screen)
            else:
                self.logical_screen.fill((0, 0, 0))

            scaled_surface = pygame.transform.scale(self.logical_screen, self.window_screen.get_size())
            self.window_screen.blit(scaled_surface, (0, 0))

            if self.state_manager.active_state_key == "GAMEPLAY" and \
                    self.context_menu and self.context_menu.is_visible:  # Sprawdź też, czy context_menu nie jest None
                self.context_menu.draw(self.window_screen)
            pygame.display.flip()
        pygame.quit()

    def _process_events(self):
        pass

    def _update(self, dt: float):
        pass

    def _draw(self):
        pass

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

    def is_tile_occupied_by_entity(self, ix: int, iy: int, excluding_entity: Optional[Entity] = None) -> bool:
        if not self.entities: return False
        for entity in self.entities:
            if entity == excluding_entity: continue
            if entity.is_alive and entity.ix == ix and entity.iy == iy:
                return True
        return False

    def show_examine_text(self, target_entity: Optional[Entity]):
        if target_entity and self.ui:
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
        self.player.target_entity_for_action = action_target
        self.player.action_after_reaching_target = final_action
        if self.tilemap:
            self.player.set_path(target_coords_iso[0], target_coords_iso[1], self.tilemap)
        else:
            print("[ERROR] player_walk_to_and_act: Tilemap not available for pathfinding.")

    def _load_damage_splat_assets_global(self):
        try:
            damage_icon_path = C.ASSETS / "ui" / "damage_icon.png"
            loaded_icon = pygame.image.load(str(damage_icon_path)).convert_alpha()
            self.damage_icon_image = self._scale_image_proportionally(loaded_icon, C.TARGET_SPLAT_ICON_HEIGHT)
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
        self.damage_splats.append(splat)