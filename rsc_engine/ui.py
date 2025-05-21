# file: rsc_engine/ui.py
import pygame
from rsc_engine import constants as C
from typing import List, Any  # Dodano Any dla get_context_menu_options
from pathlib import Path

# VVV POPRAWIONA DEFINICJA ASSETS_DIR VVV
ASSETS_DIR = Path(__file__).resolve().parent / "assets"  # Ścieżka do katalogu assets wewnątrz rsc_engine


class UI:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont("Consolas", 14)
        self.debug_font = pygame.font.SysFont("Consolas", 12)

        # --- Atrybuty dla dialogu ---
        self.dialogue_active = False
        self.dialogue_text_surface = None
        self.dialogue_speaker = ""
        self.dialogue_lines: List[str] = []
        self.current_dialogue_line_index = 0
        self.dialogue_pos = (50, C.SCREEN_HEIGHT - 120)
        self.dialogue_height = 100
        self.dialogue_bg_color = (20, 20, 50, 220)
        self.dialogue_border_color = (100, 100, 150)
        self.dialogue_text_color = (230, 230, 230)
        self.dialogue_padding = 15
        self.dialogue_max_width = C.SCREEN_WIDTH - 100
        self.dialogue_line_spacing = 5
        self.dialogue_font = pygame.font.SysFont("Consolas", 16)

        # --- Atrybuty dla ekwipunku ---
        self.inventory_visible = False
        self.backpack_icon_size = 28
        health_bar_x, health_bar_y, health_bar_w, health_bar_h = 10, 10, 200, 20
        self.backpack_icon_pos = (health_bar_x + health_bar_w + 10,
                                  health_bar_y + (health_bar_h // 2) - (self.backpack_icon_size // 2))
        self.backpack_icon_rect = pygame.Rect(self.backpack_icon_pos[0], self.backpack_icon_pos[1],
                                              self.backpack_icon_size, self.backpack_icon_size)

        self.backpack_icon_image = None
        backpack_image_path = ASSETS_DIR / "ui" / "backpack.png"
        try:
            loaded_icon = pygame.image.load(str(backpack_image_path)).convert_alpha()
            self.backpack_icon_image = pygame.transform.smoothscale(loaded_icon,
                                                                    (self.backpack_icon_size, self.backpack_icon_size))
        except pygame.error as e:
            print(f"Could not load backpack icon: {backpack_image_path}, error: {e}. Using placeholder.")
            self.backpack_icon_image = pygame.Surface((self.backpack_icon_size, self.backpack_icon_size),
                                                      pygame.SRCALPHA)
            self.backpack_icon_image.fill((100, 100, 100))
            pygame.draw.rect(self.backpack_icon_image, (150, 150, 150), self.backpack_icon_image.get_rect(), 2)

        # --- Atrybuty dla panelu informacji o postaci ---
        self.character_info_visible = False
        self.char_info_icon_size = 28
        self.char_info_icon_pos = (self.backpack_icon_rect.right + 10, self.backpack_icon_rect.top)
        self.char_info_icon_rect = pygame.Rect(self.char_info_icon_pos[0], self.char_info_icon_pos[1],
                                               self.char_info_icon_size, self.char_info_icon_size)

        self.char_info_icon_image = None
        char_info_image_path = ASSETS_DIR / "ui" / "char_info_icon.png"
        try:
            loaded_char_icon = pygame.image.load(str(char_info_image_path)).convert_alpha()
            self.char_info_icon_image = pygame.transform.smoothscale(loaded_char_icon, (self.char_info_icon_size,
                                                                                        self.char_info_icon_size))
        except pygame.error as e:
            print(f"Could not load char_info_icon.png: {char_info_image_path}, error: {e}. Using placeholder.")
            self.char_info_icon_image = pygame.Surface((self.char_info_icon_size, self.char_info_icon_size),
                                                       pygame.SRCALPHA)
            self.char_info_icon_image.fill((100, 100, 180))
            pygame.draw.rect(self.char_info_icon_image, (150, 150, 200), self.char_info_icon_image.get_rect(), 2)
            info_font = pygame.font.SysFont("Arial", 20, bold=True)
            info_surf = info_font.render("i", True, (230, 230, 250))
            info_rect = info_surf.get_rect(center=self.char_info_icon_image.get_rect().center)
            self.char_info_icon_image.blit(info_surf, info_rect)

        self.char_info_panel_width = 200
        self.char_info_panel_height = 80
        self.char_info_panel_pos = (10, self.backpack_icon_rect.bottom + 10)
        self.char_info_panel_bg_color = (50, 60, 50, 200)
        self.char_info_panel_border_color = (130, 140, 130)
        self.char_info_text_color = (220, 240, 220)
        self.char_info_font = pygame.font.SysFont("Consolas", 16)

    def toggle_inventory(self):
        self.inventory_visible = not self.inventory_visible
        if self.inventory_visible:
            self.character_info_visible = False
        print(f"[DEBUG] UI: Inventory visibility toggled to {self.inventory_visible}")

    def toggle_character_info(self):
        self.character_info_visible = not self.character_info_visible
        if self.character_info_visible:
            self.inventory_visible = False
        print(f"[DEBUG] UI: Character info visibility toggled to {self.character_info_visible}")

    def show_dialogue(self, speaker_name: str, lines: List[str]):
        print(f"[DEBUG] UI.show_dialogue called. Speaker: '{speaker_name}', Lines: {lines}")
        if not lines:
            print("[DEBUG] UI.show_dialogue: No lines, dialogue not activated.")
            self.dialogue_active = False
            self.dialogue_text_surface = None
            return

        self.dialogue_active = True
        self.dialogue_speaker = speaker_name
        self.dialogue_lines = lines
        self.current_dialogue_line_index = 0
        self._render_current_dialogue_line()

    def _render_current_dialogue_line(self):
        print("[DEBUG] UI._render_current_dialogue_line called.")
        if not self.dialogue_active or self.current_dialogue_line_index >= len(self.dialogue_lines):
            print("[DEBUG] UI._render_current_dialogue_line: Conditions not met or end of dialogue.")
            self.dialogue_active = False
            self.dialogue_text_surface = None
            return

        current_line_text = self.dialogue_lines[self.current_dialogue_line_index]
        full_text = f"{self.dialogue_speaker}: {current_line_text}"

        self.dialogue_text_surface = self.dialogue_font.render(full_text, True, self.dialogue_text_color)
        # print(f"[DEBUG] UI: Rendered dialogue surface for: '{full_text}'. Surface: {self.dialogue_text_surface}")

    def next_dialogue_line(self):
        print("[DEBUG] UI.next_dialogue_line called.")
        if not self.dialogue_active:
            # print("[DEBUG] UI.next_dialogue_line: Dialogue not active.")
            return

        self.current_dialogue_line_index += 1
        if self.current_dialogue_line_index < len(self.dialogue_lines):
            # print(f"[DEBUG] UI.next_dialogue_line: Moving to line {self.current_dialogue_line_index}.")
            self._render_current_dialogue_line()
        else:
            # print("[DEBUG] UI.next_dialogue_line: Dialogue ended.")
            self.dialogue_active = False
            self.dialogue_text_surface = None
            if hasattr(self.game.player, 'is_in_dialogue'):
                self.game.player.is_in_dialogue = False

    def hide_dialogue(self):
        self.dialogue_active = False
        self.dialogue_text_surface = None
        if hasattr(self.game.player, 'is_in_dialogue'):
            self.game.player.is_in_dialogue = False

    def draw(self, surface):
        if self.game.player:
            p = self.game.player
            x_hp, y_hp = 10, 10
            w_hp, h_hp = 200, 20

            pygame.draw.rect(surface, (50, 50, 50), (x_hp, y_hp, w_hp, h_hp))
            if p.max_hp > 0:
                fill_w = int((p.hp / p.max_hp) * w_hp)
                pygame.draw.rect(surface, (200, 0, 0), (x_hp, y_hp, fill_w, h_hp))
            pygame.draw.rect(surface, (255, 255, 255), (x_hp, y_hp, w_hp, h_hp), 2)
            txt = self.font.render(f"HP: {p.hp}/{p.max_hp}", True, (255, 255, 255))
            surface.blit(txt, (x_hp + 5, y_hp + 2))
        else:
            x_hp, y_hp = 10, 10;
            w_hp, h_hp = 200, 20
            pygame.draw.rect(surface, (50, 50, 50), (x_hp, y_hp, w_hp, h_hp))
            pygame.draw.rect(surface, (255, 255, 255), (x_hp, y_hp, w_hp, h_hp), 2)
            txt = self.font.render(f"HP: --/--", True, (255, 255, 255))
            surface.blit(txt, (x_hp + 5, y_hp + 2))

        if self.backpack_icon_image:
            surface.blit(self.backpack_icon_image, self.backpack_icon_rect.topleft)
            pygame.draw.rect(surface, (180, 180, 180), self.backpack_icon_rect, 1)

        if self.char_info_icon_image:
            surface.blit(self.char_info_icon_image, self.char_info_icon_rect.topleft)
            pygame.draw.rect(surface, (180, 180, 180), self.char_info_icon_rect, 1)

        if self.character_info_visible and self.game.player:
            p = self.game.player
            panel_x, panel_y = self.char_info_panel_pos

            info_panel_surf = pygame.Surface((self.char_info_panel_width, self.char_info_panel_height), pygame.SRCALPHA)
            info_panel_surf.fill(self.char_info_panel_bg_color)
            pygame.draw.rect(info_panel_surf, self.char_info_panel_border_color, info_panel_surf.get_rect(), 2)

            line1_text = f"Name: {p.name}"
            line2_text = f"Level: {p.level}"

            text_surf1 = self.char_info_font.render(line1_text, True, self.char_info_text_color)
            text_surf2 = self.char_info_font.render(line2_text, True, self.char_info_text_color)

            info_panel_surf.blit(text_surf1, (self.dialogue_padding, self.dialogue_padding))
            info_panel_surf.blit(text_surf2,
                                 (self.dialogue_padding, self.dialogue_padding + text_surf1.get_height() + 5))

            surface.blit(info_panel_surf, (panel_x, panel_y))

        if self.inventory_visible and self.game.inventory:
            inv = self.game.inventory
            slot_sz = 40
            padding = 6
            start_x_inv, start_y_inv = self.char_info_panel_pos[0], self.char_info_panel_pos[1]
            if self.character_info_visible:
                start_y_inv = self.char_info_panel_pos[1] + self.char_info_panel_height + 10
            else:
                start_y_inv = self.backpack_icon_rect.bottom + 10

            num_slots_wide = inv.cols
            num_slots_high = inv.rows
            inv_panel_width = num_slots_wide * (slot_sz + padding) + padding
            inv_panel_height = num_slots_high * (slot_sz + padding) + padding
            inv_panel_rect = pygame.Rect(start_x_inv - padding, start_y_inv - padding, inv_panel_width,
                                         inv_panel_height)

            inv_panel_surf = pygame.Surface((inv_panel_rect.width, inv_panel_rect.height), pygame.SRCALPHA)
            inv_panel_surf.fill((50, 50, 50, 200))
            pygame.draw.rect(inv_panel_surf, (150, 150, 150), inv_panel_surf.get_rect(), 2)
            surface.blit(inv_panel_surf, inv_panel_rect.topleft)

            for r in range(inv.rows):
                for c in range(inv.cols):
                    x = start_x_inv + c * (slot_sz + padding)
                    y = start_y_inv + r * (slot_sz + padding)
                    pygame.draw.rect(surface, (60, 60, 60), (x, y, slot_sz, slot_sz))
                    pygame.draw.rect(surface, (200, 200, 200), (x, y, slot_sz, slot_sz), 2)
                    item = inv.slots[r][c]
                    if item and item.icon:
                        try:
                            icon = pygame.transform.smoothscale(item.icon, (slot_sz - 8, slot_sz - 8))
                            surface.blit(icon, (x + 4, y + 4))
                        except pygame.error as e:
                            print(f"Error scaling item icon: {e}")

        if self.dialogue_active and self.dialogue_text_surface:
            bg_rect_width = min(self.dialogue_max_width,
                                self.dialogue_text_surface.get_width() + self.dialogue_padding * 2)
            bg_rect_height = self.dialogue_height
            dialogue_bg_surf = pygame.Surface((bg_rect_width, bg_rect_height), pygame.SRCALPHA)
            dialogue_bg_surf.fill(self.dialogue_bg_color)
            pygame.draw.rect(dialogue_bg_surf, self.dialogue_border_color, dialogue_bg_surf.get_rect(), 2)
            surface.blit(dialogue_bg_surf, self.dialogue_pos)
            text_x = self.dialogue_pos[0] + self.dialogue_padding
            text_y = self.dialogue_pos[1] + (bg_rect_height - self.dialogue_text_surface.get_height()) // 2
            surface.blit(self.dialogue_text_surface, (text_x, text_y))
            continue_font = self.debug_font
            continue_text = continue_font.render("Click to continue...", True, self.dialogue_text_color)
            surface.blit(continue_text,
                         (self.dialogue_pos[0] + bg_rect_width - continue_text.get_width() - self.dialogue_padding,
                          self.dialogue_pos[
                              1] + bg_rect_height - continue_text.get_height() - self.dialogue_padding // 2))


class ContextMenu:
    def __init__(self, game, font_size=14, padding=5, item_height=22):
        self.game = game
        self.font = pygame.font.SysFont("Consolas", font_size)
        self.is_visible = False
        self.position = (0, 0)
        self.options = []
        self.item_rects = []

        self.padding = padding
        self.item_height = item_height
        self.background_color = (40, 40, 40, 230)
        self.text_color = (220, 220, 220)
        self.highlight_color = (80, 80, 80, 230)
        self.border_color = (100, 100, 100)
        self.menu_surface = None

    def _calculate_dimensions(self):
        if not self.options:
            return 0, 0
        max_text_width = 0
        for option in self.options:
            text_surface = self.font.render(option["text"], True, self.text_color)
            if text_surface.get_width() > max_text_width:
                max_text_width = text_surface.get_width()
        menu_width = max_text_width + self.padding * 2
        menu_height = len(self.options) * self.item_height + self.padding * 2
        return menu_width, menu_height

    def show(self, position: tuple[int, int], options: list[dict]):
        self.position = position  # Pozycja menu jest na fizycznym ekranie
        self.options = options
        self.is_visible = True
        self.item_rects = []

        menu_width, menu_height = self._calculate_dimensions()
        if menu_width == 0 or menu_height == 0:
            self.is_visible = False
            return

        # VVV  POPRAWKA TUTAJ VVV
        # Użyj self.game.window_screen zamiast self.game.screen
        screen_w, screen_h = self.game.window_screen.get_size()
        # ^^^ POPRAWKA TUTAJ ^^^

        adj_x, adj_y = list(self.position)

        if adj_x + menu_width > screen_w:
            adj_x = screen_w - menu_width
        if adj_y + menu_height > screen_h:
            adj_y = screen_h - menu_height
        self.position = (max(0, adj_x), max(0, adj_y))

        self.menu_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        self.menu_surface.fill(self.background_color)
        pygame.draw.rect(self.menu_surface, self.border_color, self.menu_surface.get_rect(), 1)

        current_y = self.padding
        for i, option_data in enumerate(self.options):
            # item_rects powinny być w koordynatach ekranu, na którym menu jest rysowane (window_screen)
            global_item_rect = pygame.Rect(
                self.position[0],
                self.position[1] + current_y - self.padding // 2,  # Dodajemy pozycję menu na ekranie
                menu_width,
                self.item_height
            )
            # Jeśli ContextMenu.draw rysuje self.menu_surface na self.position (na window_screen),
            # to item_rects dla handle_click powinny być globalne (na window_screen)
            self.item_rects.append({"rect": global_item_rect, "data": option_data})

            text_surface = self.font.render(option_data["text"], True, self.text_color)
            text_y_pos = current_y + (
                        self.item_height - text_surface.get_height()) // 2 - self.padding // 2  # Lokalnie dla menu_surface
            text_rect = text_surface.get_rect(topleft=(self.padding, text_y_pos))
            self.menu_surface.blit(text_surface, text_rect)

            current_y += self.item_height

    def hide(self):
        self.is_visible = False
        self.options = []
        self.item_rects = []
        self.menu_surface = None

    def draw(self, surface: pygame.Surface):  # surface to window_screen
        if not self.is_visible or not self.menu_surface:
            return

        mouse_pos = pygame.mouse.get_pos()  # Fizyczne koordynaty myszy
        final_menu_to_blit = self.menu_surface.copy()  # Rysuj na kopii menu_surface

        for i, item_info in enumerate(self.item_rects):
            # item_info["rect"] jest już w globalnych koordynatach (window_screen)
            if item_info["rect"].collidepoint(mouse_pos):
                # Prostokąt podświetlenia jest lokalny dla menu_surface
                highlight_rect_local = pygame.Rect(
                    0,
                    self.padding + i * self.item_height - self.padding // 2,
                    self.menu_surface.get_width(),
                    self.item_height
                )
                pygame.draw.rect(final_menu_to_blit, self.highlight_color, highlight_rect_local)

                option_data = self.options[i]
                text_surface = self.font.render(option_data["text"], True, self.text_color)
                text_y_pos = self.padding + i * self.item_height + (
                            self.item_height - text_surface.get_height()) // 2 - self.padding // 2
                text_rect = text_surface.get_rect(topleft=(self.padding, text_y_pos))
                final_menu_to_blit.blit(text_surface, text_rect)

        surface.blit(final_menu_to_blit, self.position)  # Rysuj menu_surface na self.position na window_screen

    def handle_click(self, mouse_pos: tuple[int, int]) -> bool:  # mouse_pos to fizyczne koordynaty myszy
        if not self.is_visible:
            return False

        for item_info in self.item_rects:  # item_rects są w fizycznych koordynatach
            if item_info["rect"].collidepoint(mouse_pos):
                action_data = item_info["data"]
                action_func = action_data.get("action")
                target = action_data.get("target")

                if action_func:
                    action_func(
                        target if target is not None else self.game.player)  # Zmieniono self.game na self.game.player jako domyślny target, jeśli sensowne
                    self.hide()
                    return True

        self.hide()
        return False


# Dodanie klasy DamageSplat na końcu pliku
class DamageSplat:
    def __init__(self, value: int, center_x: int, entity_top_y: int, icon_image: pygame.Surface, font: pygame.font.Font,
                 game_camera):
        self.game_camera = game_camera
        self.initial_entity_top_y = entity_top_y
        self.initial_center_x = center_x

        self.value = value
        self.icon = icon_image
        self.font = font

        self.text_color = (255, 255, 255)
        if self.value == 0:
            self.text_color = (180, 180, 200)

        self.text_surface = self.font.render(str(self.value), True, self.text_color)

        self.lifetime = 1.2  # sekundy
        self.alpha = 255
        self.vertical_speed = 30  # pikseli na sekundę w górę
        self.fade_speed = 255 / (self.lifetime if self.lifetime > 0 else 0.1)  # Unikaj dzielenia przez zero

        self.current_y_offset = 0

        self.icon_width = self.icon.get_width() if self.icon else 0
        self.icon_height = self.icon.get_height() if self.icon else 0
        self.text_width = self.text_surface.get_width()
        self.text_height = self.text_surface.get_height()

        self.base_x = self.initial_center_x - self.icon_width // 2
        self.base_y = self.initial_entity_top_y - self.icon_height
        self.current_icon_surface = None  # Dla kopii ikony z alfą

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        if self.lifetime <= 0:
            return False

        self.current_y_offset += self.vertical_speed * dt
        new_alpha_val = max(0, self.alpha - self.fade_speed * dt)

        if self.icon:
            # Twórz nową powierzchnię dla ikony z alfą tylko gdy alfa się zmienia znacząco lub jest to pierwsze ustawienie
            if int(self.alpha) != int(new_alpha_val) or self.current_icon_surface is None:
                self.current_icon_surface = self.icon.copy()  # Pracuj na kopii
                self.current_icon_surface.set_alpha(int(new_alpha_val))

        self.alpha = new_alpha_val  # Aktualizuj alfę jako float dla precyzji, ale używaj int dla set_alpha

        if self.alpha < 50 and self.text_surface:  # Ukryj tekst, gdy prawie niewidoczny
            self.text_surface = None

        return True

    def draw(self, surface: pygame.Surface):  # Surface, na której rysujemy (powinien to być logical_screen)
        # Pozycja splata jest obliczana względem initial_center_x i initial_entity_top_y,
        # które były koordynatami na logical_screen po zastosowaniu kamery.
        # Więc rysujemy bezpośrednio na logical_screen w tych koordynatach.

        draw_x = self.base_x
        draw_y = self.base_y - int(self.current_y_offset)

        icon_to_draw = self.current_icon_surface if self.current_icon_surface else self.icon

        if icon_to_draw:
            surface.blit(icon_to_draw, (draw_x, draw_y))

        if self.text_surface:
            text_x = draw_x + (self.icon_width - self.text_width) // 2
            text_y = draw_y + (self.icon_height - self.text_height) // 2
            surface.blit(self.text_surface, (text_x, text_y))