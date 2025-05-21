# file: rsc_engine/game.py
from pathlib import Path
import pygame

from rsc_engine import constants as C
from rsc_engine.camera import Camera
from rsc_engine.tilemap import TileMap
from rsc_engine.entity import Player, FriendlyNPC, HostileNPC, Entity
from rsc_engine.utils import screen_to_iso, iso_to_screen
from rsc_engine.ui import UI, ContextMenu, DamageSplat
from rsc_engine.inventory import Inventory, Item
from typing import Tuple, Callable, Optional, List

ASSETS = Path(__file__).resolve().parent / "assets"
TARGET_CHAR_HEIGHT = int(C.TILE_HEIGHT * 2.2)
TARGET_SPLAT_ICON_WIDTH = 28
TARGET_SPLAT_ICON_HEIGHT = 28


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

        self.damage_splats: List[DamageSplat] = []
        self.damage_icon_image = None
        self.damage_font = None
        self._load_damage_splat_assets()

        self._load_initial_assets()

        self.camera = Camera(C.SCREEN_WIDTH, C.SCREEN_HEIGHT)
        if self.tilemap:
            self.camera.set_world_size(self.tilemap.width * C.TILE_WIDTH,
                                       self.tilemap.height * C.TILE_HEIGHT)

        self.entities = pygame.sprite.Group()

        player_original_img = self._load_image("player.png")
        scaled_player_img = self._scale_image_proportionally(player_original_img, TARGET_CHAR_HEIGHT)

        self.player = Player(
            self,
            name="Hero",
            ix=5, iy=5,
            image=scaled_player_img,
            max_hp=100,
            attack_power=15,
            defense=5,
            attack_speed=1.0
        )
        self.entities.add(self.player)

        try:
            friendly_npc_original_img = self._load_image("friendly_npc.png")
            scaled_friendly_npc_img = self._scale_image_proportionally(friendly_npc_original_img, TARGET_CHAR_HEIGHT)
        except pygame.error:
            temp_surface = pygame.Surface((C.TILE_WIDTH, TARGET_CHAR_HEIGHT), pygame.SRCALPHA)
            temp_surface.fill((0, 255, 0, 180))
            scaled_friendly_npc_img = temp_surface

        friendly_npc = FriendlyNPC(
            self,
            name="Old Man",
            ix=8, iy=8,
            image=scaled_friendly_npc_img,
            dialogue=["Witaj, podróżniku!", "Uważaj na potwory w okolicy."]
        )
        self.entities.add(friendly_npc)

        try:
            hostile_npc_original_img = self._load_image("hostile_npc.png")
            scaled_hostile_npc_img = self._scale_image_proportionally(hostile_npc_original_img, TARGET_CHAR_HEIGHT,
                                                                      use_smoothscale_if_upscaling=True)
        except pygame.error:
            temp_surface = pygame.Surface((int(C.TILE_WIDTH * 0.8), TARGET_CHAR_HEIGHT), pygame.SRCALPHA)
            temp_surface.fill((255, 0, 0, 180))
            scaled_hostile_npc_img = temp_surface

        goblin = HostileNPC(
            self,
            name="Goblin Scout",
            ix=12, iy=12,
            image=scaled_hostile_npc_img,
            level=2,
            max_hp=30,
            attack_power=6,
            defense=1,
            aggro_radius=4,
            attack_speed=2.2
        )
        self.entities.add(goblin)

        self.ui = UI(self)
        self.context_menu = ContextMenu(self)

        self.inventory = Inventory(rows=4, cols=5)
        icon_path = ASSETS / "item_icon.png"
        if icon_path.exists():
            ico_original = pygame.image.load(str(icon_path)).convert_alpha()
            ico = ico_original
        else:
            ico = pygame.Surface((32, 32), pygame.SRCALPHA)
            ico.fill((255, 215, 0, 200))
        self.inventory.add_item(Item("Magic Stone", ico))

    def _load_damage_splat_assets(self):
        try:
            damage_icon_path = ASSETS / "ui" / "damage_icon.png"
            loaded_icon = pygame.image.load(str(damage_icon_path)).convert_alpha()
            self.damage_icon_image = pygame.transform.smoothscale(loaded_icon,
                                                                  (TARGET_SPLAT_ICON_WIDTH, TARGET_SPLAT_ICON_HEIGHT))
            # print(f"[DEBUG] Loaded and scaled damage icon to: ({TARGET_SPLAT_ICON_WIDTH}x{TARGET_SPLAT_ICON_HEIGHT})")
        except pygame.error as e:
            print(f"Could not load damage_icon.png from {damage_icon_path}: {e}. Damage splats may not have icons.")
            self.damage_icon_image = pygame.Surface((TARGET_SPLAT_ICON_WIDTH, TARGET_SPLAT_ICON_HEIGHT),
                                                    pygame.SRCALPHA)
            self.damage_icon_image.fill((200, 0, 0, 150))

        try:
            self.damage_font = pygame.font.SysFont("Arial Black", 14, bold=True)
        except Exception as e:
            print(f"Could not load damage font: {e}. Using default system font for damage.")
            self.damage_font = pygame.font.SysFont(pygame.font.get_default_font(), 14, bold=True)

    def create_damage_splat(self, value: int, target_entity: Entity):
        if not self.damage_font:
            print("[ERROR] Damage font not loaded, cannot create damage splat.")
            return

        logical_entity_rect_on_cam = self.camera.apply(target_entity.rect)
        center_x = logical_entity_rect_on_cam.centerx
        top_y = logical_entity_rect_on_cam.top

        splat = DamageSplat(value, center_x, top_y, self.damage_icon_image, self.damage_font, self.camera)
        self.damage_splats.append(splat)

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

    def _load_image(self, name: str) -> pygame.Surface:
        return pygame.image.load(str(ASSETS / name)).convert_alpha()

    def _load_initial_assets(self):
        self.tileset_img = self._load_image("tileset.png")
        map_path = ASSETS / "map.csv"
        self.tilemap = TileMap(str(map_path), self.tileset_img)

    def is_tile_occupied_by_entity(self, ix: int, iy: int, excluding_entity: Optional[Entity] = None) -> bool:
        for entity in self.entities:
            if entity == excluding_entity:
                continue
            if entity.is_alive and entity.ix == ix and entity.iy == iy:
                return True
        return False

    def show_examine_text(self, target_entity: Optional[Entity]):
        if target_entity:
            message = f"It's a {target_entity.name} (Level: {target_entity.level}, HP: {target_entity.hp}/{target_entity.max_hp})."
            if hasattr(self.ui, 'show_dialogue'):
                self.ui.show_dialogue("System", [message])
            else:
                print(f"[DEBUG] Game.show_examine_text: '{message}' (UI.show_dialogue not found)")

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
        self.player.set_path(target_coords_iso[0], target_coords_iso[1], self.tilemap)

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

            if event.type == pygame.VIDEORESIZE:
                new_width, new_height = event.size
                self.window_screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
                # print(f"Window resized to: {new_width}x{new_height}")

            # Przetwarzaj zdarzenia myszy tylko jeśli są to odpowiednie typy
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos_physical = event.pos  # Fizyczna pozycja kliknięcia

                window_w, window_h = self.window_screen.get_size()
                logical_w, logical_h = self.logical_screen.get_size()
                scaled_mouse_pos = mouse_pos_physical  # Domyślnie, jeśli nie ma skalowania

                if window_w > 0 and window_h > 0:
                    mouse_scale_x = logical_w / window_w
                    mouse_scale_y = logical_h / window_h
                    scaled_mouse_pos = (int(mouse_pos_physical[0] * mouse_scale_x),
                                        int(mouse_pos_physical[1] * mouse_scale_y))

                mouse_pos_for_ui_elements_on_logical_screen = scaled_mouse_pos
                # ContextMenu.show() i handle_click() używają fizycznych koordynatów
                # ponieważ ContextMenu jest rysowane bezpośrednio na window_screen

                action_taken_by_ui_or_menu = False

                # 1. Kliknięcie ikon UI (na logical_screen)
                if event.button == 1:
                    if hasattr(self.ui, 'backpack_icon_rect') and self.ui.backpack_icon_rect.collidepoint(
                            mouse_pos_for_ui_elements_on_logical_screen):
                        if hasattr(self.ui, 'toggle_inventory'): self.ui.toggle_inventory()
                        action_taken_by_ui_or_menu = True

                    elif hasattr(self.ui, 'char_info_icon_rect') and self.ui.char_info_icon_rect.collidepoint(
                            mouse_pos_for_ui_elements_on_logical_screen):
                        if hasattr(self.ui, 'toggle_character_info'): self.ui.toggle_character_info()
                        action_taken_by_ui_or_menu = True

                # 2. Obsługa ContextMenu (na window_screen)
                if not action_taken_by_ui_or_menu and self.context_menu.is_visible:
                    if self.context_menu.handle_click(mouse_pos_physical):  # Użyj fizycznych koordynatów
                        action_taken_by_ui_or_menu = True

                        # 3. Obsługa aktywnego dialogu (na logical_screen)
                if not action_taken_by_ui_or_menu and event.button == 1 and hasattr(self.ui,
                                                                                    'dialogue_active') and self.ui.dialogue_active:
                    self.ui.next_dialogue_line()  # Kliknięcie gdziekolwiek, gdy dialog aktywny
                    action_taken_by_ui_or_menu = True

                if action_taken_by_ui_or_menu:
                    continue  # Przejdź do następnego zdarzenia

                # --- Standardowa obsługa kliknięć na mapie/encjach ---
                if event.button == 1:
                    if not self.player or not self.player.is_alive: continue

                    # Użyj przeskalowanej pozycji myszy do obliczeń w świecie gry
                    world_mx = mouse_pos_for_ui_elements_on_logical_screen[0] + self.camera.rect.x
                    world_my = mouse_pos_for_ui_elements_on_logical_screen[1] + self.camera.rect.y
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
                            self.initiate_dialogue_with_npc(clicked_entity_lmb)
                        else:
                            self.show_examine_text(clicked_entity_lmb)
                    else:
                        self.player.set_path(tx_iso, ty_iso, self.tilemap, is_manual_walk_command=True)

                elif event.button == 3:  # Prawy przycisk - otwarcie ContextMenu
                    if not self.player or not self.player.is_alive: continue

                    # Obliczenia świata dla logiki menu używają przeskalowanej pozycji
                    world_mx_menu = mouse_pos_for_ui_elements_on_logical_screen[0] + self.camera.rect.x
                    world_my_menu = mouse_pos_for_ui_elements_on_logical_screen[1] + self.camera.rect.y
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
                        self.context_menu.show(mouse_pos_physical, options)  # Pokaż menu na FIZYCZNEJ pozycji myszy
                    else:
                        self.context_menu.hide()

    def _update(self, dt: float):
        if not self.player: return
        for entity in self.entities:
            entity.update(dt, self.tilemap, self.entities)

        active_splats = []
        for splat in self.damage_splats:
            if splat.update(dt):
                active_splats.append(splat)
        self.damage_splats = active_splats

        if self.player and not self.player.is_alive and self.running:
            print("GAME OVER - Player is dead")
        if self.player:
            self.camera.update(self.player.rect)

    def _draw(self):
        # 1. Rysuj wszystko na `self.logical_screen`
        self.logical_screen.fill((48, 48, 64))

        if self.tilemap:
            self.tilemap.draw(self.logical_screen, self.camera)

        for entity in self.entities:
            if entity.is_alive:
                sx, sy = iso_to_screen(entity.ix, entity.iy)
                sx -= self.camera.rect.x
                sy -= self.camera.rect.y + C.TILE_HEIGHT // 2
                shadow_rect = pygame.Rect(sx - C.TILE_WIDTH // 4, sy - C.TILE_HEIGHT // 4, C.TILE_WIDTH // 2,
                                          C.TILE_HEIGHT // 2)
                pygame.draw.ellipse(self.logical_screen, (0, 0, 0, 100), shadow_rect)

        if self.player and self.player.is_alive and self.player.target_tile_coords:
            tx, ty = self.player.target_tile_coords
            screen_x_center, screen_y_center = iso_to_screen(tx, ty)
            screen_x_center -= self.camera.rect.x
            screen_y_center -= self.camera.rect.y
            points = [
                (screen_x_center, screen_y_center - C.TILE_HEIGHT // 2),
                (screen_x_center + C.TILE_WIDTH // 2, screen_y_center),
                (screen_x_center, screen_y_center + C.TILE_HEIGHT // 2),
                (screen_x_center - C.TILE_WIDTH // 2, screen_y_center)
            ]
            highlight_color = (255, 0, 0, 100)

            tile_surf_size = (C.TILE_WIDTH, C.TILE_HEIGHT)
            poly_surface = pygame.Surface(tile_surf_size, pygame.SRCALPHA)
            local_points = [
                (tile_surf_size[0] // 2, 0),
                (tile_surf_size[0], tile_surf_size[1] // 2),
                (tile_surf_size[0] // 2, tile_surf_size[1]),
                (0, tile_surf_size[1] // 2)
            ]
            pygame.draw.polygon(poly_surface, highlight_color, local_points)
            blit_pos_x = screen_x_center - C.TILE_WIDTH // 2
            blit_pos_y = screen_y_center - C.TILE_HEIGHT // 2
            self.logical_screen.blit(poly_surface, (blit_pos_x, blit_pos_y))

        for entity in self.entities:
            if isinstance(entity, HostileNPC) and entity.is_alive and entity.show_hp_bar:
                if entity.max_hp > 0:
                    bar_width = C.TILE_WIDTH * 0.6
                    bar_height = 6
                    logical_entity_rect_on_cam = self.camera.apply(entity.rect)
                    bar_x = logical_entity_rect_on_cam.centerx - bar_width // 2
                    bar_y = logical_entity_rect_on_cam.top - bar_height - 4
                    pygame.draw.rect(self.logical_screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
                    hp_percentage = entity.hp / entity.max_hp
                    fill_w = int(bar_width * hp_percentage)
                    pygame.draw.rect(self.logical_screen, (200, 0, 0), (bar_x, bar_y, fill_w, bar_height))
                    pygame.draw.rect(self.logical_screen, (180, 180, 180), (bar_x, bar_y, bar_width, bar_height), 1)

        sorted_entities = sorted(list(self.entities), key=lambda e: (e.rect.centery, e.rect.centerx))
        for entity in sorted_entities:
            if entity.is_alive:
                self.logical_screen.blit(entity.image, self.camera.apply(entity.rect))
            elif hasattr(entity, 'corpse_image') and entity.corpse_image:
                self.logical_screen.blit(entity.corpse_image, self.camera.apply(entity.rect))

        for splat in self.damage_splats:
            splat.draw(self.logical_screen)

        if self.ui:
            self.ui.draw(self.logical_screen)

            # 2. Skaluj `self.logical_screen` do rozmiaru `self.window_screen`
        # Użyj pygame.transform.scale dla pixel artu, aby zachować ostrość
        # Jeśli proporcje ekranu logicznego i okna są różne, to spowoduje rozciągnięcie.
        # Można dodać logikę do zachowania proporcji (letterboxing/pillarboxing).
        scaled_surface = pygame.transform.scale(self.logical_screen, self.window_screen.get_size())

        # 3. Wyświetl przeskalowaną powierzchnię na fizycznym ekranie
        self.window_screen.blit(scaled_surface, (0, 0))

        # Rysowanie menu kontekstowego na `window_screen`
        if self.context_menu and self.context_menu.is_visible:
            self.context_menu.draw(self.window_screen)

        pygame.display.flip()