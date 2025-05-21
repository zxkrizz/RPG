# rsc_engine/game_states.py
import pygame
from rsc_engine.states import BaseState, PlayerData
from rsc_engine import constants as C

# Importuj klasy gry potrzebne dla GameplayState
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player, FriendlyNPC, HostileNPC  # Usunięto Entity, jeśli nie jest bezpośrednio tworzone
from rsc_engine.ui import UI, ContextMenu  # DamageSplat jest używane przez Game.create_damage_splat
from rsc_engine.inventory import Inventory, Item
from rsc_engine.utils import screen_to_iso, iso_to_screen

# Importuj inne potrzebne rzeczy z typing
from typing import Tuple, Callable, Optional, List, Any


class MenuState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.font_large = pygame.font.SysFont("Consolas", 56, bold=True)
        self.font_buttons = pygame.font.SysFont("Consolas", 36)
        self.options = ["New Game", "Load Game", "Options (N/A)", "Quit"]  # Zmieniono "Load Game (N/A)"
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
        print("[DEBUG] MenuState initialized")

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
                        break
            elif event.type == pygame.MOUSEMOTION:
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, (_, rect, _) in enumerate(self.buttons):
                    if rect.collidepoint(scaled_mouse_pos):
                        self.selected_option_index = i
                        break

    def _select_current_option(self):
        selected_action = self.options[self.selected_option_index]
        print(f"[DEBUG] MenuState: Selected '{selected_action}'")
        if selected_action == "New Game":
            self.game.state_manager.set_state("CHARACTER_CREATION")
        elif selected_action == "Load Game":  # Poprawiona akcja
            print("[DEBUG] MenuState: Transitioning to LOAD_GAME state.")
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
        self.input_rect_width = 400
        self.input_rect_height = 50
        self.input_rect = pygame.Rect(
            (C.SCREEN_WIDTH - self.input_rect_width) // 2,
            C.SCREEN_HEIGHT // 2 - self.input_rect_height // 2 - 20,
            self.input_rect_width,
            self.input_rect_height
        )
        self.active_input = True
        self.prompt_text = "Enter your character's name:"

        self.button_width = 300
        self.button_height = 55
        self.start_button_rect = pygame.Rect(
            (C.SCREEN_WIDTH - self.button_width) // 2,
            self.input_rect.bottom + 40,
            self.button_width,
            self.button_height
        )
        self.start_button_text = "Begin Adventure"

        self.text_color = (220, 220, 230)
        self.input_text_color = (240, 240, 250)
        self.input_bg_color_active = (40, 45, 55)
        self.input_bg_color_inactive = (20, 25, 30)
        self.input_border_color = (90, 95, 110)
        self.button_text_color = (230, 250, 230)
        self.button_color = (60, 110, 60)
        self.button_border_color = (100, 160, 100)

        print("[DEBUG] CharacterCreationState initialized")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.player_name = "Hero"
        self.active_input = True

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.active_input:
                    if event.key == pygame.K_RETURN:
                        self._start_game()
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif event.unicode.isprintable() and len(event.unicode) == 1:
                        if len(self.player_name) < 15:
                            self.player_name += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                if self.input_rect.collidepoint(scaled_mouse_pos):
                    self.active_input = True
                elif self.start_button_rect.collidepoint(scaled_mouse_pos):
                    self._start_game()
                else:
                    self.active_input = False

    def _start_game(self):
        final_name = self.player_name.strip()
        if not final_name:
            final_name = "Adventurer"

        player_data = PlayerData(name=final_name, level=1, start_ix=5, start_iy=5)
        print(f"[DEBUG] CharacterCreationState: Starting game with player data: {player_data}")
        self.game.state_manager.set_state("GAMEPLAY", player_data)

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

        if self.active_input and (pygame.time.get_ticks() // 400) % 2 == 0:
            cursor_x = self.input_rect.x + 10 + name_surf.get_width() + 3
            if not self.player_name: cursor_x = self.input_rect.x + 10
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
        print("[DEBUG] GameplayState initialized (attributes will be set in on_enter)")

    def on_enter(self, player_data: Optional[PlayerData] = None):
        super().on_enter(player_data)

        current_player_data = player_data
        if current_player_data is None:
            current_player_data = PlayerData(name="DefaultPlayer")
            print(f"[WARNING] GameplayState entered without player_data, using fallback: {current_player_data}")

        self.game._load_damage_splat_assets_global()

        tileset_img = self.game._load_image("tileset.png")
        map_path = C.ASSETS / "map.csv"
        self.tilemap = TileMap(str(map_path), tileset_img)
        self.game.tilemap = self.tilemap

        self.camera = Camera(C.SCREEN_WIDTH, C.SCREEN_HEIGHT)
        if self.tilemap:
            self.camera.set_world_size(self.tilemap.width * C.TILE_WIDTH, self.tilemap.height * C.TILE_HEIGHT)
        self.game.camera = self.camera

        self.entities = pygame.sprite.Group()
        self.game.entities = self.entities

        player_original_image = self.game._load_image("player.png")
        scaled_player_image = self.game._scale_image_proportionally(player_original_image, C.TARGET_CHAR_HEIGHT)

        self.player = Player(
            self.game,
            name=current_player_data.name,
            ix=current_player_data.start_ix,
            iy=current_player_data.start_iy,
            image=scaled_player_image,
            max_hp=current_player_data.max_hp,  # Użyj danych z PlayerData
            attack_power=15,  # Można to też przenieść do PlayerData
            defense=5,  # Można to też przenieść do PlayerData
            level=current_player_data.level,
            attack_speed=1.0
        )
        self.player.hp = current_player_data.current_hp  # Ustaw aktualne HP

        self.entities.add(self.player);
        self.game.player = self.player

        try:
            fn_img_orig = self.game._load_image("friendly_npc.png"); fn_img = self.game._scale_image_proportionally(
                fn_img_orig, C.TARGET_CHAR_HEIGHT)
        except pygame.error:
            fn_img = pygame.Surface((C.TARGET_CHAR_HEIGHT, C.TARGET_CHAR_HEIGHT), pygame.SRCALPHA); fn_img.fill(
                (0, 255, 0, 150))
        friendly_npc = FriendlyNPC(self.game, "Old Man", 8, 8, fn_img,
                                   dialogue=["Witaj w świecie gry!", "Miłej zabawy."]);
        self.entities.add(friendly_npc)

        try:
            hn_img_orig = self.game._load_image("hostile_npc.png"); hn_img = self.game._scale_image_proportionally(
                hn_img_orig, C.TARGET_CHAR_HEIGHT)
        except pygame.error:
            hn_img = pygame.Surface((C.TARGET_CHAR_HEIGHT, C.TARGET_CHAR_HEIGHT), pygame.SRCALPHA); hn_img.fill(
                (255, 0, 0, 150))
        goblin = HostileNPC(self.game, "Goblin Fighter", 12, 12, hn_img, max_hp=30, attack_speed=1.8);
        self.entities.add(goblin)

        self.ui = UI(self.game);
        self.game.ui = self.ui
        self.context_menu = ContextMenu(self.game);
        self.game.context_menu = self.context_menu
        self.inventory = Inventory(rows=4, cols=5);
        self.game.inventory = self.inventory
        icon_path = C.ASSETS / "item_icon.png";
        ico = pygame.Surface((32, 32), pygame.SRCALPHA);
        ico.fill((255, 215, 0, 200))
        if icon_path.exists(): ico_original = self.game._load_image("item_icon.png"); ico = ico_original
        self.inventory.add_item(Item("Magic Stone", ico))

        self.game.damage_splats = []

    def handle_events(self, events: list[pygame.event.Event]):
        mouse_pos_physical = None;
        scaled_mouse_pos_for_logic = None
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                print("[DEBUG] Escape pressed in GameplayState, switching to PAUSE_MENU")
                # Przekaż informację, skąd przyszliśmy, aby Pauza mogła wrócić
                self.game.state_manager.set_state("PAUSE_MENU", {"previous_state": "GAMEPLAY"})
                return

            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEMOTION:
                mouse_pos_physical = event.pos
                scaled_mouse_pos_for_logic = self.game.get_scaled_mouse_pos(mouse_pos_physical)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if mouse_pos_physical is None or scaled_mouse_pos_for_logic is None: continue
                action_taken_by_ui_or_menu = False
                if event.button == 1:
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
        if not self.player or not self.tilemap or not self.camera or not self.ui or not self.entities or not self.game.context_menu:
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

        for splat in self.game.damage_splats: splat.draw(surface)

        self.ui.draw(surface)

    def on_exit(self):
        super().on_exit()
        return None


class PauseMenuState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.font_title = pygame.font.SysFont("Consolas", 50, bold=True)
        self.font_options = pygame.font.SysFont("Consolas", 30)
        self.options = ["Resume Game", "Save Game (Slot 1)", "Load Game", "Main Menu"]
        self.selected_option_index = 0
        self.buttons: List[Tuple[Optional[pygame.Surface], pygame.Rect, str]] = []
        self.gameplay_snapshot = None

        self.button_width = 350
        self.button_height = 50
        self.button_padding = 15
        self.text_color = (210, 210, 230)
        self.highlight_text_color = (255, 255, 200)
        self.button_color = (60, 60, 90)
        self.button_highlight_color = (90, 90, 130)
        self.border_color = (110, 110, 160)
        self.border_highlight_color = (160, 160, 210)

        self._create_buttons()
        print("[DEBUG] PauseMenuState initialized")

    def _create_buttons(self):
        self.buttons = []
        total_h = len(self.options) * (self.button_height + self.button_padding) - self.button_padding
        start_y = (C.SCREEN_HEIGHT - total_h) // 2
        for i, opt_text in enumerate(self.options):
            rect = pygame.Rect((C.SCREEN_WIDTH - self.button_width) // 2,
                               start_y + i * (self.button_height + self.button_padding),
                               self.button_width, self.button_height)
            self.buttons.append((None, rect, opt_text))

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_option_index = 0
        self.gameplay_snapshot = self.game.logical_screen.copy()  # Zapisz aktualny obraz gry
        dim_surface = pygame.Surface(self.gameplay_snapshot.get_size(), pygame.SRCALPHA)
        dim_surface.fill((0, 0, 0, 180))
        self.gameplay_snapshot.blit(dim_surface, (0, 0))

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
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, (_, rect, _) in enumerate(self.buttons):
                    if rect.collidepoint(scaled_mouse_pos):
                        self.selected_option_index = i;
                        self._select_current_option();
                        break
            elif event.type == pygame.MOUSEMOTION:
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, (_, rect, _) in enumerate(self.buttons):
                    if rect.collidepoint(scaled_mouse_pos): self.selected_option_index = i; break

    def _select_current_option(self):
        action = self.options[self.selected_option_index]
        print(f"[DEBUG] PauseMenu: selected '{action}'")
        if action == "Resume Game":
            self.game.state_manager.set_state("GAMEPLAY")
        elif action == "Save Game (Slot 1)":
            self.game.save_game(1)
        elif action == "Load Game":
            # Zapamiętaj, że przyszliśmy z pauzy, aby LoadGame mogło wrócić do pauzy
            self.game.state_manager.previous_active_state_key_for_load_game = "PAUSE_MENU"
            self.game.state_manager.set_state("LOAD_GAME")
        elif action == "Main Menu":
            self.game.state_manager.set_state("MENU")

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        if self.gameplay_snapshot:
            surface.blit(self.gameplay_snapshot, (0, 0))
        else:
            surface.fill((10, 10, 20))

        title_surf = self.font_title.render("Game Paused", True, (230, 230, 250))
        title_rect = title_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 4))
        surface.blit(title_surf, title_rect)

        for i, (_, rect, opt_text) in enumerate(self.buttons):
            is_sel = (i == self.selected_option_index)
            btn_col = self.button_highlight_color if is_sel else self.button_color
            brd_col = self.border_highlight_color if is_sel else self.border_color
            txt_col = self.highlight_text_color if is_sel else self.text_color
            brd_thk = 3 if is_sel else 2  # Grubsza ramka dla podświetlonego
            pygame.draw.rect(surface, btn_col, rect, border_radius=6)
            pygame.draw.rect(surface, brd_col, rect, brd_thk, border_radius=6)
            txt_surf = self.font_options.render(opt_text, True, txt_col)
            txt_rect = txt_surf.get_rect(center=rect.center)
            surface.blit(txt_surf, txt_rect)


class LoadGameState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.font_title = pygame.font.SysFont("Consolas", 40, bold=True)
        self.font_slots = pygame.font.SysFont("Consolas", 26)
        self.save_slots_info: List[Dict[str, Any]] = []
        self.slot_rects: List[pygame.Rect] = []
        self.selected_slot_index = 0

        self.slot_height = 55;
        self.slot_padding = 12
        self.slot_width = C.SCREEN_WIDTH - 150
        self.back_button_rect = pygame.Rect(C.SCREEN_WIDTH // 2 - 75, C.SCREEN_HEIGHT - 80, 150, 45)

        self.text_color = (200, 200, 220);
        self.highlight_text_color = (255, 255, 200)
        self.slot_bg_color = (40, 40, 70);
        self.slot_hl_color = (70, 70, 110)
        self.slot_border_color = (80, 80, 120)
        self.empty_slot_text_color = (120, 120, 140)
        print("[DEBUG] LoadGameState initialized")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.save_slots_info = self.game.get_save_slot_info()
        self.slot_rects = []

        num_slots_to_show = len(self.save_slots_info)
        total_slots_height = num_slots_to_show * (self.slot_height + self.slot_padding) - self.slot_padding
        start_y = (C.SCREEN_HEIGHT // 2) - (total_slots_height // 2) + 30

        for i, info in enumerate(self.save_slots_info):
            rect = pygame.Rect((C.SCREEN_WIDTH - self.slot_width) // 2,
                               start_y + i * (self.slot_height + self.slot_padding),
                               self.slot_width, self.slot_height)
            self.slot_rects.append(rect)
        self.selected_slot_index = 0

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._go_back()
                elif event.key == pygame.K_UP:
                    if self.slot_rects: self.selected_slot_index = (self.selected_slot_index - 1 + len(
                        self.slot_rects)) % len(self.slot_rects)
                elif event.key == pygame.K_DOWN:
                    if self.slot_rects: self.selected_slot_index = (self.selected_slot_index + 1) % len(self.slot_rects)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._load_selected_slot()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                if self.back_button_rect.collidepoint(scaled_mouse_pos):
                    self._go_back();
                    return
                for i, rect in enumerate(self.slot_rects):
                    if rect.collidepoint(scaled_mouse_pos):
                        self.selected_slot_index = i
                        self._load_selected_slot()
                        return
            elif event.type == pygame.MOUSEMOTION:
                scaled_mouse_pos = self.game.get_scaled_mouse_pos(event.pos)
                for i, rect in enumerate(self.slot_rects):
                    if rect.collidepoint(scaled_mouse_pos): self.selected_slot_index = i; break

    def _go_back(self):
        # Powrót do poprzedniego stanu, który wywołał LoadGameState (Menu Główne lub Menu Pauzy)
        previous_state = "MENU"  # Domyślnie
        if hasattr(self.game.state_manager, 'previous_active_state_key_for_load_game') and \
                self.game.state_manager.previous_active_state_key_for_load_game:
            previous_state = self.game.state_manager.previous_active_state_key_for_load_game
        print(f"[DEBUG] LoadGameState: Going back to {previous_state}")
        self.game.state_manager.set_state(previous_state)

    def _load_selected_slot(self):
        if 0 <= self.selected_slot_index < len(self.save_slots_info):
            slot_info = self.save_slots_info[self.selected_slot_index]
            if slot_info["exists"]:
                print(f"[DEBUG] LoadGameState: Attempting to load slot {slot_info['slot']}")
                player_data = self.game.load_game_data_from_slot(slot_info["slot"])
                if player_data:
                    self.game.state_manager.set_state("GAMEPLAY", player_data)
            else:
                print(f"[DEBUG] LoadGameState: Slot {slot_info['slot']} is empty, cannot load.")

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill((35, 30, 45))
        title_surf = self.font_title.render("Load Saved Game", True, self.text_color)
        title_rect = title_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 5))
        surface.blit(title_surf, title_rect)

        for i, rect in enumerate(self.slot_rects):
            info = self.save_slots_info[i]
            is_sel = (i == self.selected_slot_index)

            bg_col = self.slot_hl_color if is_sel and info["exists"] else self.slot_bg_color
            current_text_color = self.highlight_text_color if is_sel and info["exists"] else self.text_color
            if not info["exists"]: current_text_color = self.empty_slot_text_color

            pygame.draw.rect(surface, bg_col, rect, border_radius=5)
            pygame.draw.rect(surface, self.slot_border_color, rect, 2, border_radius=5)

            slot_text = f"Slot {info['slot']}: {info['player_name']} (Lvl: {info['level']}) - Map: {info['map_id']}"
            if not info["exists"]: slot_text = f"Slot {info['slot']}: ----- EMPTY -----"

            text_surf = self.font_slots.render(slot_text, True, current_text_color)
            text_rect = text_surf.get_rect(midleft=(rect.left + 25, rect.centery))
            surface.blit(text_surf, text_rect)

        # Przycisk Powrotu
        back_button_color = (80, 30, 30)
        back_border_color = (120, 70, 70)
        scaled_mouse_pos = self.game.get_scaled_mouse_pos(pygame.mouse.get_pos())
        if self.back_button_rect.collidepoint(scaled_mouse_pos):
            back_button_color = (110, 40, 40)
            back_border_color = (150, 90, 90)

        pygame.draw.rect(surface, back_button_color, self.back_button_rect, border_radius=5)
        pygame.draw.rect(surface, back_border_color, self.back_button_rect, 2, border_radius=5)
        back_text = self.font_slots.render("Back", True, self.text_color)
        surface.blit(back_text, back_text.get_rect(center=self.back_button_rect.center))

    def on_exit(self):
        super().on_exit()
        # Wyczyść zapamiętany poprzedni stan, jeśli istniał
        if hasattr(self.game.state_manager, 'previous_active_state_key_for_load_game'):
            self.game.state_manager.previous_active_state_key_for_load_game = None