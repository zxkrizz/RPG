# rsc_engine/states.py
import pygame
from abc import ABC, abstractmethod
from rsc_engine import constants as C # Dla dostępu do C.SCREEN_WIDTH/HEIGHT w stanach UI

# Aby uniknąć importów cyklicznych dla type hinting
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Callable
if TYPE_CHECKING:
    from rsc_engine.game import Game, PlayerData # Przenieś PlayerData tutaj, jeśli chcesz
    # Importuj inne klasy gry, jeśli stany będą je bezpośrednio tworzyć/używać
    from rsc_engine.camera import Camera
    from rsc_engine.tilemap import TileMap
    from rsc_engine.entity import Player, FriendlyNPC, HostileNPC
    from rsc_engine.ui import UI, ContextMenu
    from rsc_engine.inventory import Inventory, Item


class BaseState(ABC):
    def __init__(self, game: "Game"):
        self.game = game

    @abstractmethod
    def handle_events(self, events: list[pygame.event.Event]):
        pass

    @abstractmethod
    def update(self, dt: float):
        pass

    @abstractmethod
    def draw(self, surface: pygame.Surface): # Stany rysują na przekazanej powierzchni (logical_screen)
        pass

    def on_enter(self, previous_state_data=None):
        """Wywoływane przy wejściu w ten stan."""
        print(f"[DEBUG] Entering state: {self.__class__.__name__} with data: {previous_state_data}") # DEBUG
        pass

    def on_exit(self):
        """Wywoływane przy wyjściu z tego stanu. Może zwrócić dane dla następnego stanu."""
        print(f"[DEBUG] Exiting state: {self.__class__.__name__}") # DEBUG
        return None


class GameStateManager:
    def __init__(self, initial_state_key: str, game: "Game"):
        self.game = game
        self.states: dict[str, BaseState] = {}
        self.active_state: BaseState | None = None
        self.active_state_key: str = "" # Inicjalizuj puste
        self.initial_state_to_set_after_registration = initial_state_key # Zapamiętaj klucz

    def register_state(self, key: str, state: BaseState):
        self.states[key] = state
        print(f"[DEBUG] GameStateManager: Registered state '{key}'")
        # Jeśli to jest stan, który miał być ustawiony na początku, ustaw go teraz
        if key == self.initial_state_to_set_after_registration and self.active_state is None:
             print(f"[DEBUG] GameStateManager: Auto-setting initial state to '{key}' after registration.")
             # Musimy zdecydować, jakie dane przekazać. Game.__init__ ma logikę dla DEV_SKIP.
             # To jest trochę skomplikowane. Prostsze będzie, jeśli set_state w Game.__init__
             # zostanie wywołane PO _register_states.

    def set_state(self, key: str, data_for_next_state=None):
        if self.active_state:
            # Dane z on_exit mogą być użyte, jeśli data_for_next_state jest None
            # ale zazwyczaj przekazujemy jawnie dane do następnego stanu.
            self.active_state.on_exit() 

        if key in self.states:
            print(f"[DEBUG] GameStateManager: Attempting to set state to '{key}'")
            self.active_state_key = key
            self.active_state = self.states[key]
            self.active_state.on_enter(data_for_next_state)
        else:
            print(f"[ERROR] GameStateManager: State '{key}' not found upon trying to set!")

    def handle_events(self, events: list[pygame.event.Event]):
        if self.active_state:
            self.active_state.handle_events(events)

    def update(self, dt: float):
        if self.active_state:
            self.active_state.update(dt)

    def draw(self, surface: pygame.Surface):
        if self.active_state:
            self.active_state.draw(surface)
        else: # Jeśli żaden stan nie jest aktywny, narysuj czarny ekran lub wiadomość
            surface.fill((0,0,0)) 
            font = pygame.font.SysFont("Consolas", 20)
            text = font.render("No active state!", True, (255,0,0))
            rect = text.get_rect(center=(surface.get_width()//2, surface.get_height()//2))
            surface.blit(text, rect)

# Przeniesienie PlayerData tutaj dla lepszej organizacji
class PlayerData:
    def __init__(self, name="Hero_Dev", level=1, start_ix=5, start_iy=5):
        self.name = name
        self.level = level
        self.start_ix = start_ix
        self.start_iy = start_iy
        # W przyszłości: self.inventory_data, self.stats, etc.
    def __repr__(self): # Dla lepszego debugowania
        return f"PlayerData(name='{self.name}', level={self.level}, pos=({self.start_ix},{self.start_iy}))"