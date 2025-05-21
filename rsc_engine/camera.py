"""2D camera that follows the player or any focus target."""
import pygame
from rsc_engine import constants as C

class Camera:
    def __init__(self, width: int = C.SCREEN_WIDTH, height: int = C.SCREEN_HEIGHT):
        self.rect = pygame.Rect(0, 0, width, height)
        self.world_width = self.world_height = 0  # filled by map after load

    def set_world_size(self, w: int, h: int):
        self.world_width, self.world_height = w, h

    def apply(self, target_rect: pygame.Rect) -> pygame.Rect:
        """Return a new rect shifted into screen-space by camera offset."""
        return target_rect.move(-self.rect.x, -self.rect.y)

    def update(self, target_rect: pygame.Rect):
        # Zawsze centrowanie na obiekcie, bez ograniczeń do granic świata
        self.rect.center = target_rect.center
