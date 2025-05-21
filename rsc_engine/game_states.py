# rsc_engine/game_states.py
import pygame
from rsc_engine.states import BaseState, PlayerData
from rsc_engine import constants as C  # <<< POPRAWIONY IMPORT STAŁYCH

# Importuj klasy gry potrzebne dla GameplayState
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player, FriendlyNPC, HostileNPC  # Usunięto Entity, jeśli nie jest bezpośrednio tworzone
from rsc_engine.ui import UI, ContextMenu
from rsc_engine.inventory import Inventory, Item
from rsc_engine.utils import screen_to_iso, iso_to_screen

# Importuj inne potrzebne rzeczy z typing
from typing import Tuple, Callable, Optional, List, Any


# Stałe, które były wcześniej importowane z game.py, teraz używamy przez C.
# np. C.ASSETS, C.TARGET_CHAR_HEIGHT itp.


class MenuState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.font_large = pygame.font.SysFont("Consolas", 60, bold=True)
        self.font_buttons = pygame.font.SysFont("Consolas", 40)
        self.options = ["New Game", "Load Game (N/A)", "Options (N/A)", "Quit"]
        self.buttons: List[Tuple[pygame.Surface, pygame.Rect, str]] = []
        self.selected_option_index = 0
        self._create_buttons()
        print("[DEBUG] MenuState initialized")

    def _create_buttons(self):
        self.buttons = []
        button_height = 50
        button_width = 300
        total_button_space = len(self.options) * (button_height + 15) - 15
        start_y = (C.SCREEN_HEIGHT - total_button_space) // 2 + 80

        for i, option_text in enumerate(self.options):
            text_surf = self.font_buttons.render(option_text, True, (220, 220, 220))
            button_rect = pygame.Rect(
                (C.SCREEN_WIDTH - button_width) // 2,
                start_y + i * (button_height + 15),
                button_width,
                button_height
            )
            self.buttons.append((text_surf, button_rect, option_text))

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

    def _select_current_option(self):
        selected_action = self.options[self.selected_option_index]
        print(f"[DEBUG] MenuState: Selected '{selected_action}'")
        if selected_action == "New Game":
            self.game.state_manager.set_state("CHARACTER_CREATION")
        elif selected_action == "Load Game (N/A)":
            print("Load Game - Not implemented yet")
        elif selected_action == "Options (N/A)":
            print("Options - Not implemented yet")
        elif selected_action == "Quit":
            self.game.running = False

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill((20, 20, 30))

        caption_text = "RuneScape Classic Clone"
        title_surf = self.font_large.render(caption_text, True, (200, 200, 250))
        title_rect = title_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 4 - 20))
        surface.blit(title_surf, title_rect)

        for i, (text_surf, rect, _) in enumerate(self.buttons):
            color = (80, 80, 120) if i == self.selected_option_index else (50, 50, 80)
            border_color = (150, 150, 200) if i == self.selected_option_index else (100, 100, 130)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, border_color, rect, 3 if i == self.selected_option_index else 2)

            text_rect = text_surf.get_rect(center=rect.center)
            surface.blit(text_surf, text_rect)


class CharacterCreationState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.font_title = pygame.font.SysFont("Consolas", 40, bold=True)
        self.font_prompt = pygame.font.SysFont("Consolas", 30)
        self.font_input = pygame.font.SysFont("Consolas", 28)
        self.font_button = pygame.font.SysFont("Consolas", 30)

        self.player_name = ""
        self.input_rect = pygame.Rect(C.SCREEN_WIDTH // 2 - 200, C.SCREEN_HEIGHT // 2 - 25, 400, 50)
        self.active_input = True
        self.prompt_text = "Enter your character's name:"
        self.start_button_rect = pygame.Rect(C.SCREEN_WIDTH // 2 - 125, C.SCREEN_HEIGHT // 2 + 60, 250, 60)
        self.start_button_text = "Begin Adventure"
        print("[DEBUG] CharacterCreationState initialized")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.player_name = "Hero"
        self.active_input = True
        # print("[DEBUG] CharacterCreationState entered") # Już logowane przez BaseState.on_enter

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.active_input:
                    if event.key == pygame.K_RETURN:
                        self._start_game()
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif event.unicode.isalnum() or event.unicode == ' ':
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
            final_name = "Hero"

        player_data = PlayerData(name=final_name, level=1, start_ix=5, start_iy=5)
        # self.game.shared_game_data["player_data"] = player_data # Opcjonalne, jeśli Game tego potrzebuje globalnie
        print(f"[DEBUG] CharacterCreationState: Starting game with player data: {player_data}")
        self.game.state_manager.set_state("GAMEPLAY", player_data)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill((30, 35, 40))

        title_surf = self.font_title.render("Create Your Character", True, (210, 210, 230))
        title_rect = title_surf.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 4))
        surface.blit(title_surf, title_rect)

        prompt_surf = self.font_prompt.render(self.prompt_text, True, (180, 180, 200))
        prompt_rect = prompt_surf.get_rect(center=(C.SCREEN_WIDTH // 2, self.input_rect.top - 35))
        surface.blit(prompt_surf, prompt_rect)

        pygame.draw.rect(surface, (20, 25, 30) if not self.active_input else (40, 45, 55), self.input_rect,
                         border_radius=5)
        pygame.draw.rect(surface, (90, 95, 110), self.input_rect, 2, border_radius=5)
        name_surf = self.font_input.render(self.player_name, True, (200, 200, 220))
        surface.blit(name_surf, (self.input_rect.x + 10,
                                 self.input_rect.y + (self.input_rect.height - name_surf.get_height()) // 2))

        if self.active_input and (pygame.time.get_ticks() // 500) % 2 == 0:
            cursor_x = self.input_rect.x + 10 + name_surf.get_width() + 2
            cursor_y_start = self.input_rect.y + 8
            cursor_y_end = self.input_rect.y + self.input_rect.height - 8
            pygame.draw.line(surface, (200, 200, 220), (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 2)

        pygame.draw.rect(surface, (60, 110, 60), self.start_button_rect, border_radius=8)
        pygame.draw.rect(surface, (100, 160, 100), self.start_button_rect, 3, border_radius=8)
        start_text_surf = self.font_button.render(self.start_button_text, True, (210, 240, 210))
        start_text_rect = start_text_surf.get_rect(center=self.start_button_rect.center)
        surface.blit(start_text_surf, start_text_rect)


class GameplayState(BaseState):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.player: Optional[Player] = None
        self.entities: Optional[pygame.sprite.Group] = None  # Grupa dla wszystkich encji, w tym gracza
        self.tilemap: Optional[TileMap] = None
        self.camera: Optional[Camera] = None
        self.ui: Optional[UI] = None
        self.context_menu: Optional[ContextMenu] = None
        self.inventory: Optional[Inventory] = None
        # self.damage_splats jest zarządzane przez self.game.damage_splats

        print("[DEBUG] GameplayState initialized (attributes will be set in on_enter)")

    def on_enter(self, player_data: Optional[PlayerData] = None):
        super().on_enter(player_data)

        current_player_data = player_data
        if current_player_data is None:
            current_player_data = PlayerData(name="DefaultPlayer")
            print(f"[WARNING] GameplayState entered without player_data, using fallback: {current_player_data}")

        # Inicjalizacja/Reset obiektów gry
        self.game._load_damage_splat_assets_global()  # Upewnij się, że zasoby splatów są załadowane w Game

        tileset_img = self.game._load_image("tileset.png")
        map_path = C.ASSETS / "map.csv"  # Użyj C.ASSETS
        self.tilemap = TileMap(str(map_path), tileset_img)
        self.game.tilemap = self.tilemap

        self.camera = Camera(C.SCREEN_WIDTH, C.SCREEN_HEIGHT)
        self.camera.set_world_size(self.tilemap.width * C.TILE_WIDTH, self.tilemap.height * C.TILE_HEIGHT)
        self.game.camera = self.camera

        self.entities = pygame.sprite.Group()
        self.game.entities = self.entities

        # Ładowanie arkusza gracza
        player_original_image = self.game._load_image("player.png")  # Użyj poprawnej nazwy pliku

        # Skalujemy ten pojedynczy obrazek
        scaled_player_image = self.game._scale_image_proportionally(
            player_original_image,
            C.TARGET_CHAR_HEIGHT
        )
        self.player = Player(
            self.game,
            name=current_player_data.name,
            ix=current_player_data.start_ix,
            iy=current_player_data.start_iy,
            image=scaled_player_image,  # <<< ZMIANA: przekazujemy pojedynczy obrazek
            max_hp=100, attack_power=15, defense=5, level=current_player_data.level, attack_speed=1.0
        )
        self.entities.add(self.player)
        self.game.player = self.player

        try:
            fn_img_orig = self.game._load_image("friendly_npc.png")
            fn_img = self.game._scale_image_proportionally(fn_img_orig, C.TARGET_CHAR_HEIGHT)
        except pygame.error:
            fn_img = pygame.Surface((32, 32)); fn_img.fill((0, 255, 0))
        friendly_npc = FriendlyNPC(self.game, "Old Man", 8, 8, fn_img,
                                   dialogue=["Witaj w świecie gry!", "Miłej zabawy."])
        self.entities.add(friendly_npc)

        try:
            hn_img_orig = self.game._load_image("hostile_npc.png")
            hn_img = self.game._scale_image_proportionally(hn_img_orig, C.TARGET_CHAR_HEIGHT)
        except pygame.error:
            hn_img = pygame.Surface((32, 32)); hn_img.fill((255, 0, 0))
        goblin = HostileNPC(self.game, "Goblin Fighter", 12, 12, hn_img, max_hp=30, attack_speed=1.8)
        self.entities.add(goblin)

        self.ui = UI(self.game)
        self.game.ui = self.ui

        self.context_menu = ContextMenu(self.game)
        self.game.context_menu = self.context_menu

        self.inventory = Inventory(rows=4, cols=5)
        self.game.inventory = self.inventory
        icon_path = C.ASSETS / "item_icon.png"  # Użyj C.ASSETS
        if icon_path.exists():
            ico_original = self.game._load_image("item_icon.png")  # Użyj game._load_image
            ico = ico_original
        else:
            ico = pygame.Surface((32, 32), pygame.SRCALPHA)
            ico.fill((255, 215, 0, 200))
        self.inventory.add_item(Item("Magic Stone", ico))

        self.game.damage_splats = []  # Wyczyść listę splatów przy wejściu w stan

    def handle_events(self, events: list[pygame.event.Event]):
        mouse_pos_physical = None
        scaled_mouse_pos_for_logic = None

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEMOTION:
                mouse_pos_physical = event.pos
                scaled_mouse_pos_for_logic = self.game.get_scaled_mouse_pos(mouse_pos_physical)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if mouse_pos_physical is None: continue

                action_taken_by_ui_or_menu = False

                if event.button == 1:
                    if self.ui.backpack_icon_rect.collidepoint(scaled_mouse_pos_for_logic):
                        self.ui.toggle_inventory();
                        action_taken_by_ui_or_menu = True
                    elif self.ui.char_info_icon_rect.collidepoint(scaled_mouse_pos_for_logic):
                        self.ui.toggle_character_info();
                        action_taken_by_ui_or_menu = True

                if not action_taken_by_ui_or_menu and self.context_menu.is_visible:
                    if self.context_menu.handle_click(mouse_pos_physical):
                        action_taken_by_ui_or_menu = True

                if not action_taken_by_ui_or_menu and event.button == 1 and self.ui.dialogue_active:
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

                    options = []
                    clicked_entity_for_menu = None
                    for entity_sprite in self.entities:
                        if entity_sprite.rect.collidepoint(world_mx_menu, world_my_menu):
                            clicked_entity_for_menu = entity_sprite;
                            break

                    if clicked_entity_for_menu:
                        options = clicked_entity_for_menu.get_context_menu_options(self.player)
                    else:
                        options.append({
                            "text": "Walk here",
                            "action": lambda ignored_arg: self.player.set_path(tx_iso_menu, ty_iso_menu, self.tilemap,
                                                                               is_manual_walk_command=True),
                            "target": None
                        })
                    if options:
                        self.context_menu.show(mouse_pos_physical, options)
                    else:
                        self.context_menu.hide()

    def update(self, dt: float):
        if not self.player: return  # Jeśli stan nie został w pełni zainicjowany
        self.entities.update(dt, self.tilemap, self.entities)

        active_splats = []
        for splat in self.game.damage_splats:  # Użyj listy z obiektu Game
            if splat.update(dt):
                active_splats.append(splat)
        self.game.damage_splats = active_splats

        if self.player and not self.player.is_alive and self.game.running:
            print("GAME OVER - Player is dead")
            # Można tu dodać logikę przejścia do stanu "Game Over"
            # self.game.state_manager.set_state("GAME_OVER")
        if self.player:
            self.camera.update(self.player.rect)

    def draw(self, surface: pygame.Surface):
        if not self.player or not self.tilemap or not self.camera or not self.ui:  # Upewnij się, że wszystko jest
            surface.fill((10, 0, 0))  # Ciemnoczerwony błąd, jeśli stan niezaładowany
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

        sorted_entities = sorted(list(self.entities), key=lambda e: (e.rect.centery, e.rect.centerx))
        for entity in sorted_entities:
            if entity.is_alive:
                surface.blit(entity.image, self.camera.apply(entity.rect))
            elif hasattr(entity, 'corpse_image') and entity.corpse_image:
                surface.blit(entity.corpse_image, self.camera.apply(entity.rect))

        for splat in self.game.damage_splats: splat.draw(surface)

        self.ui.draw(surface)
        # ContextMenu jest rysowane przez Game.run() na window_screen

    def on_exit(self):
        super().on_exit()
        # Opcjonalnie: zwolnij zasoby specyficzne dla tego stanu
        # self.game.player = None # Game będzie trzymać referencję do PlayerData, nie do instancji
        # self.game.entities = None
        # self.game.tilemap = None
        # etc.
        return None  # Lub dane do przekazania do następnego stanu