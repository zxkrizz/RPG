# rsc_engine/game_states.py
import pygame
import json
from rsc_engine.states import BaseState, PlayerData
from rsc_engine import constants as C

# Importuj klasy gry potrzebne dla GameplayState
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player, FriendlyNPC, HostileNPC
from rsc_engine.ui import UI, ContextMenu
from rsc_engine.inventory import Inventory, Item
from rsc_engine.utils import screen_to_iso, iso_to_screen
from pathlib import Path

from typing import Tuple, Callable, Optional, List, Any, Dict


class MenuState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.font_large = pygame.font.SysFont("Consolas", 56, bold=True)
        self.font_buttons = pygame.font.SysFont("Consolas", 36)
        self.options = ["New Game", "Load Game", "Options (N/A)", "Quit"]
        self.buttons: List[Tuple[Optional[pygame.Surface], pygame.Rect, str]] = []
        self.selected_option_index = 0

        self.button_height = 55
        self.button_width = 350
        self.button_padding = 20

        self.text_color = (220, 220, 230)
        self.highlight_text_color = (255, 255, 180)
        self.button_color = (40, 40, 70)
        self.button_highlight_color = (70, 70, 110)
        self.border_color = (80, 80, 120)
        self.border_highlight_color = (150, 150, 200)

        self._create_buttons()
        # print("[DEBUG] MenuState initialized") # Usunięto dla czystości logów produkcyjnych

    def _create_buttons(self):
        self.buttons = []
        total_button_space = len(self.options) * (self.button_height + self.button_padding) - self.button_padding
        start_y = (C.SCREEN_HEIGHT - total_button_space) // 2 + 70

        for i, option_text in enumerate(self.options):
            button_rect = pygame.Rect(
                (C.SCREEN_WIDTH - self.button_width) // 2,
                start_y + i * (self.button_height + self.button_padding),
                self.button_width,
                self.button_height
            )
            self.buttons.append((None, button_rect, option_text))

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_option_index = (self.selected_option_index - 1 + len(self.options)) % len(
                        self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected_option_index = (self.selected_option_index + 1) % len(self.options)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._select_current_option()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, (_, rect, _) in enumerate(self.buttons):
                    if rect.collidepoint(scaled_mouse_pos):
                        self.selected_option_index = i
                        self._select_current_option()
                        return
            elif event.type == pygame.MOUSEMOTION:
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, (_, rect, _) in enumerate(self.buttons):
                    if rect.collidepoint(scaled_mouse_pos):
                        if self.selected_option_index != i:
                            self.selected_option_index = i
                        break

    def _select_current_option(self):
        selected_action = self.options[self.selected_option_index]
        print(f"[DEBUG] MenuState: Selected '{selected_action}'")
        if selected_action == "New Game":
            self.game.state_manager.set_state("CHARACTER_CREATION")
        elif selected_action == "Load Game":
            if hasattr(self.game.state_manager, 'previous_active_state_key_for_load_game'):
                self.game.state_manager.previous_active_state_key_for_load_game = "MENU"
            self.game.state_manager.set_state("LOAD_GAME")
        elif selected_action == "Options (N/A)":
            print("Options - Not implemented yet")
        elif selected_action == "Quit":
            self.game.running = False

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill((25, 20, 35))

        caption_text = "RSC Clone Adventure"
        title_surf = self.font_large.render(caption_text, True, (230, 220, 255))
        title_rect = title_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 4 - 30))
        surface.blit(title_surf, title_rect)

        for i, (_, rect, option_text) in enumerate(self.buttons):
            is_selected = (i == self.selected_option_index)

            current_button_color = self.button_highlight_color if is_selected else self.button_color
            current_border_color = self.border_highlight_color if is_selected else self.border_color
            current_text_color = self.highlight_text_color if is_selected else self.text_color
            border_thickness = 4 if is_selected else 2

            pygame.draw.rect(surface, current_button_color, rect, border_radius=8)
            pygame.draw.rect(surface, current_border_color, rect, border_thickness, border_radius=8)

            text_surf = self.font_buttons.render(option_text, True, current_text_color)
            text_rect = text_surf.get_rect(center=rect.center)
            surface.blit(text_surf, text_rect)


class CharacterCreationState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.font_title = pygame.font.SysFont("Consolas", 40, bold=True)
        self.font_prompt = pygame.font.SysFont("Consolas", 28)
        self.font_input = pygame.font.SysFont("Consolas", 32)
        self.font_button = pygame.font.SysFont("Consolas", 30)

        self.player_name = ""
        self.input_rect_width = 400;
        self.input_rect_height = 50
        self.input_rect = pygame.Rect((C.SCREEN_WIDTH - self.input_rect_width) // 2,
                                      C.SCREEN_HEIGHT // 2 - self.input_rect_height // 2 - 20, self.input_rect_width,
                                      self.input_rect_height)
        self.active_input = True;
        self.prompt_text = "Enter your character's name:"
        self.button_width = 300;
        self.button_height = 55
        self.start_button_rect = pygame.Rect((C.SCREEN_WIDTH - self.button_width) // 2, self.input_rect.bottom + 40,
                                             self.button_width, self.button_height)
        self.start_button_text = "Begin Adventure"
        self.text_color = (220, 220, 230);
        self.input_text_color = (240, 240, 250);
        self.input_bg_color_active = (40, 45, 55);
        self.input_bg_color_inactive = (20, 25, 30);
        self.input_border_color = (90, 95, 110);
        self.button_text_color = (230, 250, 230);
        self.button_color = (60, 110, 60);
        self.button_border_color = (100, 160, 100)
        # print("[DEBUG] CharacterCreationState initialized")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data);
        self.player_name = "Hero";
        self.active_input = True

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.active_input:
                    if event.key == pygame.K_RETURN:
                        self._start_game()
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif event.unicode.isprintable() and len(event.unicode) == 1 and len(self.player_name) < 15:
                        self.player_name += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sm_pos = self.game.get_scaled_mouse_pos(event.pos)
                if self.input_rect.collidepoint(sm_pos):
                    self.active_input = True
                elif self.start_button_rect.collidepoint(sm_pos):
                    self._start_game()
                else:
                    self.active_input = False

    def _start_game(self):
        fn = self.player_name.strip();
        fn = fn if fn else "Adventurer"
        pd = PlayerData(name=fn);
        print(f"[DEBUG] CharacterCreationState: Starting game with player data: {pd}")
        self.game.state_manager.set_state("GAMEPLAY", pd)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill((25, 30, 35))

        title_surf = self.font_title.render("Create Your Hero", True, self.text_color)
        title_rect = title_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 4 - 20))
        surface.blit(title_surf, title_rect)

        prompt_surf = self.font_prompt.render(self.prompt_text, True, self.text_color)
        prompt_rect = prompt_surf.get_rect(center=(C.SCREEN_WIDTH // 2, self.input_rect.top - 40))
        surface.blit(prompt_surf, prompt_rect)

        current_input_bg = self.input_bg_color_active if self.active_input else self.input_bg_color_inactive
        pygame.draw.rect(surface, current_input_bg, self.input_rect, border_radius=5)
        pygame.draw.rect(surface, self.input_border_color, self.input_rect, 2, border_radius=5)

        name_surf = self.font_input.render(self.player_name, True, self.input_text_color)
        name_surf_rect = name_surf.get_rect(left=self.input_rect.left + 10, centery=self.input_rect.centery)
        surface.blit(name_surf, name_surf_rect)

        # Kursor tekstowy
        if self.active_input and (pygame.time.get_ticks() // 400) % 2 == 0:
            cursor_x = self.input_rect.x + 10 + name_surf.get_width() + 3
            # VVV POPRAWIONA LOGIKA VVV
            if not self.player_name:
                cursor_x = self.input_rect.x + 10
                # ^^^ POPRAWIONA LOGIKA ^^^
            cursor_y_start = self.input_rect.y + self.input_rect.height * 0.2
            cursor_y_end = self.input_rect.y + self.input_rect.height * 0.8
            pygame.draw.line(surface, self.input_text_color, (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 2)

        pygame.draw.rect(surface, self.button_color, self.start_button_rect, border_radius=8)
        pygame.draw.rect(surface, self.button_border_color, self.start_button_rect, 3, border_radius=8)
        start_text_surf = self.font_button.render(self.start_button_text, True, self.button_text_color)
        start_text_rect = start_text_surf.get_rect(center=self.start_button_rect.center)
        surface.blit(start_text_surf, start_text_rect)


class GameplayState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.player: Optional[Player] = None
        self.entities: Optional[pygame.sprite.Group] = None
        self.tilemap: Optional[TileMap] = None
        self.camera: Optional[Camera] = None
        self.ui: Optional[UI] = None
        self.context_menu: Optional[ContextMenu] = None
        self.inventory: Optional[Inventory] = None
        # print("[DEBUG] GameplayState initialized (attributes will be set in on_enter)")

    def on_enter(self, loaded_game_or_player_data: Optional[Any] = None):
        super().on_enter(loaded_game_or_player_data)
        current_player_data: Optional[PlayerData] = None
        loaded_npc_states: Optional[List[Dict[str, Any]]] = None
        current_map_id = "default_map"

        if isinstance(loaded_game_or_player_data, PlayerData):
            current_player_data = loaded_game_or_player_data
            print(f"[INFO] GameplayState entered from Character Creator with: {current_player_data}")
        elif isinstance(loaded_game_or_player_data, dict) and "player_data" in loaded_game_or_player_data:
            current_player_data = PlayerData.from_dict(loaded_game_or_player_data["player_data"])
            loaded_npc_states = loaded_game_or_player_data.get("npc_states", [])
            current_map_id = loaded_game_or_player_data.get("current_map_id", current_map_id)
            print(
                f"[INFO] GameplayState entered from Load Game with: {current_player_data} and {len(loaded_npc_states or [])} NPC states.")
        else:
            current_player_data = PlayerData(name="DefaultPlayer_GS")
            print(f"[WARNING] GameplayState entered without specific data, using fallback: {current_player_data}")

        self.game._load_damage_splat_assets_global()

        tileset_img = self.game._load_image("tileset.png")
        map_csv_filename = current_map_id + ".csv" if not current_map_id.endswith(".csv") else current_map_id
        map_path = C.ASSETS / map_csv_filename

        if not map_path.exists():
            print(f"[ERROR] Map file not found: {map_path}. Using default map.csv")
            map_path = C.ASSETS / "map.csv"
            if not map_path.exists():
                print(f"[FATAL ERROR] Default map.csv also not found. Cannot initialize GameplayState.")
                self.game.running = False;
                return

        self.tilemap = TileMap(str(map_path), tileset_img)
        setattr(self.tilemap, 'id', Path(map_path).stem)  # Zapisz ID mapy (nazwę pliku bez rozszerzenia)
        self.game.tilemap = self.tilemap

        self.camera = Camera(C.SCREEN_WIDTH, C.SCREEN_HEIGHT)
        if self.tilemap: self.camera.set_world_size(self.tilemap.width * C.TILE_WIDTH,
                                                    self.tilemap.height * C.TILE_HEIGHT)
        self.game.camera = self.camera

        self.entities = pygame.sprite.Group();
        self.game.entities = self.entities

        player_original_image = self.game._load_image("player.png")
        scaled_player_image = self.game._scale_image_proportionally(player_original_image, C.TARGET_CHAR_HEIGHT)

        self.player = Player(self.game, name=current_player_data.name, ix=current_player_data.start_ix,
                             iy=current_player_data.start_iy, image=scaled_player_image,
                             entity_id=f"player_{current_player_data.name.lower().replace(' ', '_')}",
                             max_hp=current_player_data.max_hp, attack_power=15, defense=5,
                             level=current_player_data.level, attack_speed=1.0)
        self.player.hp = current_player_data.current_hp
        if hasattr(self.player, 'xp') and hasattr(current_player_data, 'xp'): self.player.xp = current_player_data.xp
        self.entities.add(self.player);
        self.game.player = self.player

        def_fn_ix, def_fn_iy = 8, 8;
        def_gn_ix, def_gn_iy = 12, 12
        default_npc_definitions = {
            f"friendly_oldman_{def_fn_ix}_{def_fn_iy}": {"type": FriendlyNPC, "name": "Old Man", "ix": def_fn_ix,
                                                         "iy": def_fn_iy, "image_file": "friendly_npc.png",
                                                         "dialogue": ["Witaj w GameplayState!", "To jest test."],
                                                         "max_hp": 30, "attack_speed": 9999},
            f"hostile_goblin_{def_gn_ix}_{def_gn_iy}": {"type": HostileNPC, "name": "Goblin Scout", "ix": def_gn_ix,
                                                        "iy": def_gn_iy, "image_file": "hostile_npc.png", "max_hp": 30,
                                                        "attack_speed": 1.8, "level": 1, "attack_power": 5,
                                                        "defense": 1, "aggro_radius": 5}
        }

        processed_npc_ids = set()
        if loaded_npc_states:
            for npc_data in loaded_npc_states:
                entity_id = npc_data.get("entity_id");
                if not entity_id: continue;
                processed_npc_ids.add(entity_id);
                npc_class_name = npc_data.get("type");
                npc_class = None;
                image_file_for_npc = default_npc_definitions.get(entity_id, {}).get("image_file",
                                                                                    "hostile_npc.png")  # Pobierz z definicji
                if npc_class_name == "FriendlyNPC":
                    npc_class = FriendlyNPC
                elif npc_class_name == "HostileNPC":
                    npc_class = HostileNPC

                if npc_class and npc_data.get("is_alive", True):
                    print(f"[INFO] Loading NPC from save: {entity_id}")
                    try:
                        img_orig = self.game._load_image(
                            image_file_for_npc); img = self.game._scale_image_proportionally(img_orig,
                                                                                             C.TARGET_CHAR_HEIGHT)
                    except:
                        img = pygame.Surface((C.TARGET_CHAR_HEIGHT, C.TARGET_CHAR_HEIGHT), pygame.SRCALPHA); img.fill(
                            (100, 100, 100, 150))

                    base_def = default_npc_definitions.get(entity_id, {})
                    npc_args = {
                        "game": self.game, "name": npc_data.get("name", base_def.get("name")),
                        "ix": npc_data.get("ix"), "iy": npc_data.get("iy"), "image": img,
                        "entity_id": entity_id, "level": npc_data.get("level", base_def.get("level", 1)),
                        "max_hp": npc_data.get("max_hp", base_def.get("max_hp")),
                        "attack_speed": npc_data.get("attack_speed", base_def.get("attack_speed", 2.0))
                    }
                    if npc_class == FriendlyNPC:
                        npc_args["dialogue"] = npc_data.get("dialogue", base_def.get("dialogue"))
                    elif npc_class == HostileNPC:
                        npc_args["attack_power"] = npc_data.get("attack_power", base_def.get("attack_power", 5))
                        npc_args["defense"] = npc_data.get("defense", base_def.get("defense", 1))
                        npc_args["aggro_radius"] = npc_data.get("aggro_radius", base_def.get("aggro_radius", 5))

                    npc_instance = npc_class(**npc_args);
                    npc_instance.hp = npc_data.get("hp");
                    npc_instance.is_alive = npc_data.get("is_alive", True)
                    if isinstance(npc_instance, HostileNPC):
                        npc_instance.show_hp_bar = npc_data.get("show_hp_bar", False);
                        npc_instance.is_chasing = npc_data.get("is_chasing", False)
                        npc_instance.start_ix, npc_instance.start_iy = npc_data.get("ix"), npc_data.get(
                            "iy")  # Użyj pozycji z zapisu jako startowej

                    if npc_instance.is_alive: self.entities.add(npc_instance)
                elif not npc_data.get("is_alive", True):
                    print(f"[INFO] NPC {entity_id} was dead in save, not creating.")

        for entity_id, def_data in default_npc_definitions.items():
            if entity_id not in processed_npc_ids:
                print(f"[INFO] Creating default NPC: {entity_id}")
                npc_class = def_data["type"]
                try:
                    img_orig = self.game._load_image(
                        def_data["image_file"]); img = self.game._scale_image_proportionally(img_orig,
                                                                                             C.TARGET_CHAR_HEIGHT)
                except:
                    img = pygame.Surface((C.TARGET_CHAR_HEIGHT, C.TARGET_CHAR_HEIGHT), pygame.SRCALPHA); img.fill(
                        (100, 100, 100, 150))

                npc_args = {"game": self.game, "name": def_data["name"], "ix": def_data["ix"], "iy": def_data["iy"],
                            "image": img, "entity_id": entity_id, "level": def_data.get("level", 1),
                            "max_hp": def_data["max_hp"], "attack_speed": def_data.get("attack_speed", 2.0)}
                if npc_class == FriendlyNPC:
                    npc_args["dialogue"] = def_data.get("dialogue")
                elif npc_class == HostileNPC:
                    npc_args["attack_power"] = def_data.get("attack_power", 5); npc_args["defense"] = def_data.get(
                        "defense", 1); npc_args["aggro_radius"] = def_data.get("aggro_radius", 5)
                npc_instance = npc_class(**npc_args)
                if isinstance(npc_instance, HostileNPC): npc_instance.start_ix, npc_instance.start_iy = def_data["ix"], \
                def_data["iy"]
                self.entities.add(npc_instance)

        self.ui = UI(self.game);
        self.game.ui = self.ui
        self.context_menu = ContextMenu(self.game);
        self.game.context_menu = self.context_menu
        self.inventory = Inventory(self.game, rows=4, cols=5)  # Przekazujemy self.game do Inventory
        self.game.inventory = self.inventory

        # Usuwamy bezpośrednie tworzenie Item tutaj:
        # icon_path = C.ASSETS/"item_icon.png";
        # ico=pygame.Surface((32,32),pygame.SRCALPHA);
        # ico.fill((255,215,0,200))
        # if icon_path.exists():
        #     try:
        #         ico_original=self.game._load_image("item_icon.png");
        #         ico=ico_original
        #     except Exception as e:
        #         print(f"Could not load item_icon.png in GameplayState on_enter: {e}")

        # self.inventory.add_item(Item("Magic Stone", ico)); # <<< STARA, BŁĘDNA LINIA

        # VVV POPRAWIONY SPOSÓB DODAWANIA PRZEDMIOTU VVV
        # Użyj item_id zdefiniowanego w items.json
        # Upewnij się, że ItemManager jest już zainicjalizowany w self.game
        if hasattr(self.game, 'item_manager') and self.game.item_manager:
            item_id_to_add = "MISC001"  # Przykładowe ID dla "Gold Coin" lub inne, które masz
            if self.game.item_manager.item_exists(item_id_to_add):
                self.inventory.add_item(item_id_to_add, 1)  # Dodaj 1 sztukę
                print(f"[INFO] Added '{item_id_to_add}' to inventory.")
            else:
                print(f"[WARNING] Item ID '{item_id_to_add}' not found in item definitions. Cannot add to inventory.")
        else:
            print("[ERROR] ItemManager not initialized in game object. Cannot add items to inventory.")
        # ^^^ KONIEC POPRAWKI ^^^

        self.game.damage_splats = []

def handle_events(self, events: list[pygame.event.Event]):
        mouse_pos_physical = None;
        scaled_mouse_pos_for_logic = None
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                print("[DEBUG] Escape pressed in GameplayState, switching to PAUSE_MENU")
                if hasattr(self.game.state_manager, 'previous_active_state_key_for_load_game'):
                    self.game.state_manager.previous_active_state_key_for_load_game = "GAMEPLAY"
                self.game.state_manager.set_state("PAUSE_MENU")
                return

            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEMOTION:
                mouse_pos_physical = event.pos
                scaled_mouse_pos_for_logic = self.game.get_scaled_mouse_pos(mouse_pos_physical)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if mouse_pos_physical is None or scaled_mouse_pos_for_logic is None: continue
                action_taken_by_ui_or_menu = False
                if event.button == 1:  # Lewy przycisk myszy
                    if self.ui and hasattr(self.ui, 'backpack_icon_rect') and self.ui.backpack_icon_rect.collidepoint(
                            scaled_mouse_pos_for_logic):
                        if hasattr(self.ui,
                                   'toggle_inventory'): self.ui.toggle_inventory(); action_taken_by_ui_or_menu = True
                    elif self.ui and hasattr(self.ui,
                                             'char_info_icon_rect') and self.ui.char_info_icon_rect.collidepoint(
                            scaled_mouse_pos_for_logic):
                        if hasattr(self.ui,
                                   'toggle_character_info'): self.ui.toggle_character_info(); action_taken_by_ui_or_menu = True
                    elif self.ui and hasattr(self.ui,
                                             'game_menu_icon_rect') and self.ui.game_menu_icon_rect.collidepoint(
                            scaled_mouse_pos_for_logic):
                        if hasattr(self.ui,
                                   'toggle_game_menu'): self.ui.toggle_game_menu(); action_taken_by_ui_or_menu = True

                if not action_taken_by_ui_or_menu and self.ui and hasattr(self.ui,
                                                                          'in_game_menu') and self.ui.in_game_menu.is_visible:
                    if self.ui.in_game_menu.handle_click(scaled_mouse_pos_for_logic): action_taken_by_ui_or_menu = True

                if not action_taken_by_ui_or_menu and self.context_menu and self.context_menu.is_visible:
                    if self.context_menu.handle_click(mouse_pos_physical): action_taken_by_ui_or_menu = True

                if not action_taken_by_ui_or_menu and event.button == 1 and self.ui and hasattr(self.ui,
                                                                                                'dialogue_active') and self.ui.dialogue_active:
                    self.ui.next_dialogue_line();
                    action_taken_by_ui_or_menu = True

                if action_taken_by_ui_or_menu: continue

                if event.button == 1:
                    if not self.player or not self.player.is_alive: continue
                    world_mx = scaled_mouse_pos_for_logic[0] + self.camera.rect.x
                    world_my = scaled_mouse_pos_for_logic[1] + self.camera.rect.y
                    tx_iso, ty_iso = screen_to_iso(world_mx, world_my)
                    clicked_entity_lmb = None
                    for entity_sprite in self.entities:
                        if entity_sprite.rect.collidepoint(world_mx, world_my) and entity_sprite != self.player:
                            clicked_entity_lmb = entity_sprite;
                            break
                    if clicked_entity_lmb and clicked_entity_lmb.is_alive:
                        if isinstance(clicked_entity_lmb, HostileNPC):
                            self.player.initiate_attack_on_target(clicked_entity_lmb)
                        elif isinstance(clicked_entity_lmb, FriendlyNPC):
                            self.game.initiate_dialogue_with_npc(clicked_entity_lmb)
                        else:
                            self.game.show_examine_text(clicked_entity_lmb)
                    else:
                        self.player.set_path(tx_iso, ty_iso, self.tilemap, is_manual_walk_command=True)

                elif event.button == 3:
                    if not self.player or not self.player.is_alive: continue
                    world_mx_menu = scaled_mouse_pos_for_logic[0] + self.camera.rect.x
                    world_my_menu = scaled_mouse_pos_for_logic[1] + self.camera.rect.y
                    tx_iso_menu, ty_iso_menu = screen_to_iso(world_mx_menu, world_my_menu)
                    options = [];
                    clicked_entity_for_menu = None
                    for entity_sprite in self.entities:
                        if entity_sprite.rect.collidepoint(world_mx_menu,
                                                           world_my_menu): clicked_entity_for_menu = entity_sprite; break
                    if clicked_entity_for_menu:
                        options = clicked_entity_for_menu.get_context_menu_options(self.player)
                    else:
                        options.append({"text": "Walk here",
                                        "action": lambda ig: self.player.set_path(tx_iso_menu, ty_iso_menu,
                                                                                  self.tilemap,
                                                                                  is_manual_walk_command=True),
                                        "target": None})
                    if options:
                        self.context_menu.show(mouse_pos_physical, options)
                    else:
                        self.context_menu.hide()

    def update(self, dt: float):
        if not self.player or not self.entities or not self.tilemap or not self.camera: return
        self.entities.update(dt, self.tilemap, self.entities)
        active_splats = [];
        for splat in self.game.damage_splats:
            if splat.update(dt): active_splats.append(splat)
        self.game.damage_splats = active_splats
        if self.player and not self.player.is_alive and self.game.running: print("GAME OVER - Player is dead")
        if self.player: self.camera.update(self.player.rect)

    def draw(self, surface: pygame.Surface):
        if not self.player or not self.tilemap or not self.camera or not self.ui or not self.entities or \
                not hasattr(self.game, 'context_menu') or self.game.context_menu is None:
            surface.fill((10, 0, 0))
            return

        surface.fill((48, 48, 64))
        self.tilemap.draw(surface, self.camera)

        for entity in self.entities:
            if entity.is_alive:
                sx, sy = iso_to_screen(entity.ix, entity.iy)
                sx -= self.camera.rect.x;
                sy -= self.camera.rect.y + C.TILE_HEIGHT // 2
                shadow_rect = pygame.Rect(sx - C.TILE_WIDTH // 4, sy - C.TILE_HEIGHT // 4, C.TILE_WIDTH // 2,
                                          C.TILE_HEIGHT // 2)
                pygame.draw.ellipse(surface, (0, 0, 0, 100), shadow_rect)

                # Rysowanie podświetlonego kafelka celu gracza
        if self.player.is_alive and self.player.target_tile_coords:
            tx, ty = self.player.target_tile_coords
            screen_x_center, screen_y_center = iso_to_screen(tx, ty)
            screen_x_center -= self.camera.rect.x;
            screen_y_center -= self.camera.rect.y
            points = [(screen_x_center, screen_y_center - C.TILE_HEIGHT // 2),
                      (screen_x_center + C.TILE_WIDTH // 2, screen_y_center),
                      (screen_x_center, screen_y_center + C.TILE_HEIGHT // 2),
                      (screen_x_center - C.TILE_WIDTH // 2, screen_y_center)]
            highlight_color = (255, 0, 0, 100)
            tile_surf_size = (C.TILE_WIDTH, C.TILE_HEIGHT);
            poly_surface = pygame.Surface(tile_surf_size, pygame.SRCALPHA)
            local_points = [(tile_surf_size[0] // 2, 0), (tile_surf_size[0], tile_surf_size[1] // 2),
                            (tile_surf_size[0] // 2, tile_surf_size[1]), (0, tile_surf_size[1] // 2)]
            pygame.draw.polygon(poly_surface, highlight_color, local_points)
            surface.blit(poly_surface, (screen_x_center - C.TILE_WIDTH // 2, screen_y_center - C.TILE_HEIGHT // 2))

        for entity in self.entities:
            if isinstance(entity, HostileNPC) and entity.is_alive and entity.show_hp_bar:
                if entity.max_hp > 0:
                    bar_w = C.TILE_WIDTH * 0.6;
                    bar_h = 6
                    log_rect = self.camera.apply(entity.rect)
                    bar_x = log_rect.centerx - bar_w // 2;
                    bar_y = log_rect.top - bar_h - 4
                    pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
                    fill_w = int(bar_w * (entity.hp / entity.max_hp))
                    pygame.draw.rect(surface, (200, 0, 0), (bar_x, bar_y, fill_w, bar_h))
                    pygame.draw.rect(surface, (180, 180, 180), (bar_x, bar_y, bar_w, bar_h), 1)

        sorted_entities = sorted(list(self.entities), key=lambda x: (x.rect.centery, x.rect.centerx))
        for entity in sorted_entities:
            if entity.is_alive:
                surface.blit(entity.image, self.camera.apply(entity.rect))
            elif hasattr(entity, 'corpse_image') and entity.corpse_image:
                surface.blit(entity.corpse_image, self.camera.apply(entity.rect))

        if hasattr(self.game, 'damage_splats') and isinstance(self.game.damage_splats, list):
            for splat in self.game.damage_splats:
                splat.draw(surface)

            self.ui.draw(surface)

    def on_exit(self):
        super().on_exit()
        if self.game.player and self.game.player.is_alive:
            current_map_id = "default_map"
            if self.tilemap and hasattr(self.tilemap, 'id'):
                current_map_id = self.tilemap.id
            elif self.tilemap and hasattr(self.tilemap, 'csv_path'):
                current_map_id = Path(self.tilemap.csv_path).stem

            self.game.shared_game_data["player_data_on_pause"] = PlayerData(
                name=self.game.player.name, level=self.game.player.level,
                start_ix=self.game.player.ix, start_iy=self.game.player.iy,
                max_hp=self.game.player.max_hp, current_hp=self.game.player.hp,
                xp=getattr(self.game.player, 'xp', 0), map_id=current_map_id
            )
        return None


class PauseMenuState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game);
        self.font_title = pygame.font.SysFont("Consolas", 50, bold=True);
        self.font_options = pygame.font.SysFont("Consolas", 30);
        self.options = ["Resume Game", "Save Game (Slot 1)", "Save Game (Slot 2)", "Save Game (Slot 3)", "Load Game",
                        "Main Menu"];  # Zaktualizowane opcje
        self.selected_option_index = 0;
        self.buttons: List[Tuple[Optional[pygame.Surface], pygame.Rect, str]] = [];
        self.gameplay_snapshot = None
        self.button_width = 380;
        self.button_height = 45;
        self.button_padding = 10;  # Dostosowane wymiary
        self.text_color = (210, 210, 230);
        self.highlight_text_color = (255, 255, 200);
        self.button_color = (60, 60, 90);
        self.button_highlight_color = (90, 90, 130);
        self.border_color = (110, 110, 160);
        self.border_highlight_color = (160, 160, 210)
        self._create_buttons();
        print("[DEBUG] PauseMenuState initialized")

    def _create_buttons(self):
        self.buttons = [];
        total_h = len(self.options) * (self.button_height + self.button_padding) - self.button_padding;
        start_y = (C.SCREEN_HEIGHT - total_h) // 2
        for i, opt_text in enumerate(self.options): rect = pygame.Rect((C.SCREEN_WIDTH - self.button_width) // 2,
                                                                       start_y + i * (
                                                                                   self.button_height + self.button_padding),
                                                                       self.button_width,
                                                                       self.button_height); self.buttons.append(
            (None, rect, opt_text))

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data);
        self.selected_option_index = 0
        if self.game.logical_screen: self.gameplay_snapshot = self.game.logical_screen.copy(); dim_surface = pygame.Surface(
            self.gameplay_snapshot.get_size(), pygame.SRCALPHA); dim_surface.fill(
            (0, 0, 0, 180)); self.gameplay_snapshot.blit(dim_surface, (0, 0))

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.state_manager.set_state("GAMEPLAY")
                elif event.key == pygame.K_UP:
                    self.selected_option_index = (self.selected_option_index - 1 + len(self.options)) % len(
                        self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected_option_index = (self.selected_option_index + 1) % len(self.options)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._select_current_option()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sm_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, (_, rect, _) in enumerate(self.buttons):
                    if rect.collidepoint(sm_pos): self.selected_option_index = i;self._select_current_option();break
            elif event.type == pygame.MOUSEMOTION:
                sm_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, (_, rect, _) in enumerate(self.buttons):
                    if rect.collidepoint(sm_pos): self.selected_option_index = i;break

    def _select_current_option(self):
        action = self.options[self.selected_option_index];
        print(f"[DEBUG] PauseMenu: selected '{action}'")
        if action == "Resume Game":
            self.game.state_manager.set_state("GAMEPLAY")
        elif action == "Save Game (Slot 1)":
            if self.game.player and self.game.tilemap:
                self.game.save_game(1)
            else:
                print("[ERROR] PauseMenu: Cannot save, player or tilemap not found on game object!")
        elif action == "Save Game (Slot 2)":
            if self.game.player and self.game.tilemap:
                self.game.save_game(2)
            else:
                print("[ERROR] PauseMenu: Cannot save, player or tilemap not found on game object!")
        elif action == "Save Game (Slot 3)":
            if self.game.player and self.game.tilemap:
                self.game.save_game(3)
            else:
                print("[ERROR] PauseMenu: Cannot save, player or tilemap not found on game object!")
        elif action == "Load Game":
            if hasattr(self.game.state_manager,
                       'previous_active_state_key_for_load_game'): self.game.state_manager.previous_active_state_key_for_load_game = "PAUSE_MENU"
            self.game.state_manager.set_state("LOAD_GAME")
        elif action == "Main Menu":
            self.game.state_manager.set_state("MENU")

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        if self.gameplay_snapshot:
            surface.blit(self.gameplay_snapshot, (0, 0))
        else:
            surface.fill((10, 10, 20, 180))
        ts = self.font_title.render("Game Paused", True, (230, 230, 250));
        tr = ts.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 4));
        surface.blit(ts, tr)
        for i, (_, rect, opt_text) in enumerate(self.buttons):
            is_sel = (i == self.selected_option_index);
            bc = self.button_highlight_color if is_sel else self.button_color;
            brc = self.border_highlight_color if is_sel else self.border_color;
            tc = self.highlight_text_color if is_sel else self.text_color;
            bt = 3 if is_sel else 2
            pygame.draw.rect(surface, bc, rect, 0, 6);
            pygame.draw.rect(surface, brc, rect, bt, 6);
            ts = self.font_options.render(opt_text, True, tc);
            tr = ts.get_rect(center=rect.center);
            surface.blit(ts, tr)


class LoadGameState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game);
        self.font_title = pygame.font.SysFont("Consolas", 40, bold=True);
        self.font_slots = pygame.font.SysFont("Consolas", 26);
        self.save_slots_info: List[Dict[str, Any]] = [];
        self.slot_rects: List[pygame.Rect] = [];
        self.selected_slot_index = 0
        self.slot_height = 55;
        self.slot_padding = 12;
        self.slot_width = C.SCREEN_WIDTH - 150;
        self.back_button_rect = pygame.Rect(C.SCREEN_WIDTH // 2 - 75, C.SCREEN_HEIGHT - 80, 150, 45)
        self.text_color = (200, 200, 220);
        self.highlight_text_color = (255, 255, 200);
        self.slot_bg_color = (40, 40, 70);
        self.slot_hl_color = (70, 70, 110);
        self.slot_border_color = (80, 80, 120);
        self.empty_slot_text_color = (120, 120, 140);  # print("[DEBUG] LoadGameState initialized")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data);
        self.save_slots_info = self.game.get_save_slot_info();
        self.slot_rects = []
        num_slots = len(self.save_slots_info);
        total_h = num_slots * (self.slot_height + self.slot_padding) - self.slot_padding;
        start_y = (C.SCREEN_HEIGHT // 2) - (total_h // 2) + 30
        for i, info in enumerate(self.save_slots_info): rect = pygame.Rect((C.SCREEN_WIDTH - self.slot_width) // 2,
                                                                           start_y + i * (
                                                                                       self.slot_height + self.slot_padding),
                                                                           self.slot_width,
                                                                           self.slot_height);self.slot_rects.append(
            rect)
        self.selected_slot_index = 0

    def handle_events(self, events: list[pygame.event.Event]):
        for e_event in events:
            if e_event.type == pygame.KEYDOWN:
                if e_event.key == pygame.K_ESCAPE:
                    self._go_back()
                elif e_event.key == pygame.K_UP and self.slot_rects:
                    self.selected_slot_index = (self.selected_slot_index - 1 + len(self.slot_rects)) % len(
                        self.slot_rects)
                elif e_event.key == pygame.K_DOWN and self.slot_rects:
                    self.selected_slot_index = (self.selected_slot_index + 1) % len(self.slot_rects)
                elif e_event.key == pygame.K_RETURN or e_event.key == pygame.K_SPACE:
                    self._load_selected_slot()
            elif e_event.type == pygame.MOUSEBUTTONDOWN and e_event.button == 1:
                sm_pos = self.game.get_scaled_mouse_pos(e_event.pos)
                if self.back_button_rect.collidepoint(sm_pos): self._go_back();return
                for i, r in enumerate(self.slot_rects):
                    if r.collidepoint(sm_pos): self.selected_slot_index = i;self._load_selected_slot();return
            elif e_event.type == pygame.MOUSEMOTION:
                sm_pos = self.game.get_scaled_mouse_pos(e_event.pos)
                for i, r in enumerate(self.slot_rects):
                    if r.collidepoint(sm_pos): self.selected_slot_index = i;break

    def _go_back(self):
        prev_state = "MENU";
        stored_prev_state = getattr(self.game.state_manager, 'previous_active_state_key_for_load_game', None)
        if stored_prev_state:
            prev_state = stored_prev_state
        print(f"[DEBUG] LoadGameState: Going back to {prev_state}")
        self.game.state_manager.set_state(prev_state)

    def _load_selected_slot(self):
        if 0 <= self.selected_slot_index < len(self.save_slots_info):
            info = self.save_slots_info[self.selected_slot_index]
            if info["exists"]:
                print(f"[DEBUG] LoadGameState: Attempting to load slot {info['slot']}")
                save_path = self.game.get_save_file_path(info["slot"]);
                loaded_data = None
                if save_path.exists():
                    try:
                        with open(save_path, 'r') as f:
                            loaded_data = json.load(f)
                    except Exception as e:
                        print(f"[ERROR] Could not parse slot {info['slot']}: {e}")
                if loaded_data and "player_data" in loaded_data:
                    self.game.shared_game_data["current_save_slot"] = info["slot"]
                    self.game.state_manager.set_state("GAMEPLAY", loaded_data)
                else:
                    print(f"[ERROR] Failed to load slot {info['slot']}")
            else:
                print(f"[DEBUG] Slot {info['slot']} is empty")

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill((35, 30, 45));
        ts = self.font_title.render("Load Saved Game", True, self.text_color);
        tr = ts.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 5));
        surface.blit(ts, tr)
        for i, rect in enumerate(self.slot_rects):
            info = self.save_slots_info[i];
            is_sel = (i == self.selected_slot_index);
            bg_col = self.slot_hl_color if is_sel and info["exists"] else self.slot_bg_color;
            txt_col = self.highlight_text_color if is_sel and info["exists"] else self.text_color
            if not info["exists"]: txt_col = self.empty_slot_text_color
            pygame.draw.rect(surface, bg_col, rect, 0, 5);
            pygame.draw.rect(surface, self.slot_border_color, rect, 2, 5)
            slot_txt = f"Slot {info['slot']}: {info['player_name']} (Lvl: {info['level']}) - Map: {info['map_id']}";
            if not info["exists"]: slot_txt = f"Slot {info['slot']}: ----- EMPTY -----"
            txt_s = self.font_slots.render(slot_txt, True, txt_col);
            txt_r = txt_s.get_rect(midleft=(rect.left + 25, rect.centery));
            surface.blit(txt_s, txt_r)
        bb_col = (80, 30, 30);
        bb_bc = (120, 70, 70);
        sm_pos = self.game.get_scaled_mouse_pos(pygame.mouse.get_pos())
        if self.back_button_rect.collidepoint(sm_pos): bb_col = (110, 40, 40);bb_bc = (150, 90, 90)
        pygame.draw.rect(surface, bb_col, self.back_button_rect, 0, 5);
        pygame.draw.rect(surface, bb_bc, self.back_button_rect, 2, 5);
        bt_txt = self.font_slots.render("Back", True, self.text_color);
        surface.blit(bt_txt, bt_txt.get_rect(center=self.back_button_rect.center))

    def on_exit(self):
        super().on_exit()
        if hasattr(self.game.state_manager, 'previous_active_state_key_for_load_game'):
            self.game.state_manager.previous_active_state_key_for_load_game = None