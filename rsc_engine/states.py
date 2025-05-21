# rsc_engine/states.py
import pygame
from abc import ABC, abstractmethod
from rsc_engine import constants as C

# Aby uniknąć importów cyklicznych dla type hinting
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Callable
if TYPE_CHECKING:
    from rsc_engine.game import Game
    # Importuj inne klasy gry, jeśli stany będą je bezpośrednio tworzyć/używać
    from rsc_engine.camera import Camera
    from rsc_engine.tilemap import TileMap
    from rsc_engine.entity import Player, FriendlyNPC, HostileNPC # Usunięto Entity, jeśli nie jest bezpośrednio tworzone
    from rsc_engine.ui import UI, ContextMenu
    from rsc_engine.inventory import Inventory, Item
    from rsc_engine.utils import screen_to_iso, iso_to_screen


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
        print(f"[DEBUG] Entering state: {self.__class__.__name__} with data: {previous_state_data}")
        pass

    def on_exit(self):
        print(f"[DEBUG] Exiting state: {self.__class__.__name__}")
        return None


class GameStateManager:
    def __init__(self, initial_state_key: Optional[str], game: "Game"): # initial_state_key może być None
        self.game = game
        self.states: dict[str, BaseState] = {}
        self.active_state: BaseState | None = None
        self.active_state_key: str = ""
        self.initial_state_to_set_after_registration = initial_state_key
        # Faktyczne ustawienie stanu początkowego dzieje się w Game.__init__ po _register_states()

    def register_state(self, key: str, state: BaseState):
        self.states[key] = state
        print(f"[DEBUG] GameStateManager: Registered state '{key}'")

    def set_state(self, key: str, data_for_next_state=None):
        if self.active_state:
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
        else:
            surface.fill((0,0,0))
            font = pygame.font.SysFont("Consolas", 20)
            text = font.render("No active state or state not registered!", True, (255,0,0))
            rect = text.get_rect(center=(surface.get_width()//2, surface.get_height()//2))
            surface.blit(text, rect)

class PlayerData:
    def __init__(self, name="Hero_Dev", level=1, start_ix=5, start_iy=5,
                 max_hp=100, current_hp=100, xp=0,
                 map_id="default_map"):
        self.name = name
        self.level = level
        self.start_ix = start_ix
        self.start_iy = start_iy
        self.max_hp = max_hp
        self.current_hp = current_hp
        self.xp = xp
        self.map_id = map_id

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level,
            "start_ix": self.start_ix,
            "start_iy": self.start_iy,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "xp": self.xp,
            "map_id": self.map_id
        }

    @classmethod
    def from_dict(cls, data_dict: dict) -> "PlayerData":
        return cls(
            name=data_dict.get("name", "Loaded Hero"),
            level=data_dict.get("level", 1),
            start_ix=data_dict.get("start_ix", 5),
            start_iy=data_dict.get("start_iy", 5),
            max_hp=data_dict.get("max_hp", 100),
            current_hp=data_dict.get("current_hp", 100),
            xp=data_dict.get("xp", 0),
            map_id=data_dict.get("map_id", "default_map")
        )

    def __repr__(self):
        return f"PlayerData(name='{self.name}', Lvl:{self.level}, Pos:({self.start_ix},{self.start_iy}), HP:{self.current_hp}/{self.max_hp}, Map:'{self.map_id}')"