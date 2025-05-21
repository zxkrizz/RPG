# file: rsc_engine/ui.py
import pygame
from rsc_engine import constants as C

class UI:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont("Consolas", 14)

    def draw(self, surface):
        # 1) Health bar
        p = self.game.player
        x, y = 10, 10
        w, h = 200, 20

        # tło paska
        pygame.draw.rect(surface, (50,50,50), (x, y, w, h))
        # wypełnienie czerwone
        fill_w = int((p.hp / p.max_hp) * w)
        pygame.draw.rect(surface, (200,0,0), (x, y, fill_w, h))
        # obramowanie
        pygame.draw.rect(surface, (255,255,255), (x, y, w, h), 2)
        # tekst
        txt = self.font.render(f"HP: {p.hp}/{p.max_hp}", True, (255,255,255))
        surface.blit(txt, (x + 5, y + 2))

        # 2) TODO: inventory slots, minimap, dialog box itp.
        # –––––––––– INVENTORY GRID ––––––––––
        inv = self.game.inventory
        slot_sz = 40
        padding = 6
        start_x, start_y = 10, 40
        for r in range(inv.rows):
            for c in range(inv.cols):
                x = start_x + c * (slot_sz + padding)
                y = start_y + r * (slot_sz + padding)
                # tło i obramowanie slotu
                pygame.draw.rect(surface, (60,60,60), (x, y, slot_sz, slot_sz))
                pygame.draw.rect(surface, (200,200,200), (x, y, slot_sz, slot_sz), 2)
                item = inv.slots[r][c]
                if item:
                    # centrowanie ikonki
                    icon = pygame.transform.smoothscale(item.icon, (slot_sz-8, slot_sz-8))
                    surface.blit(icon, (x+4, y+4))