# rsc_engine/item_manager.py
import pygame
import json
from pathlib import Path
from typing import Dict, Optional, Any

# Załóżmy, że stałe C są dostępne (lub przekaż ścieżkę do assets inaczej)
from rsc_engine import constants as C


class ItemManager:
    def __init__(self):
        self.item_definitions: Dict[str, Dict[str, Any]] = {}
        self.item_icons: Dict[str, pygame.Surface] = {}
        # Ścieżka do katalogu z ikonami przedmiotów
        self.icons_base_path = C.ASSETS / "items"  # Zakładamy, że ikony są w rsc_engine/assets/items/
        self._load_item_definitions()

    def _load_item_definitions(self):
        # Ścieżka do pliku JSON z definicjami przedmiotów
        definitions_path = C.ASSETS / "data" / "items.json"  # Użyj C.ASSETS z constants.py
        try:
            with open(definitions_path, 'r') as f:
                self.item_definitions = json.load(f)
            print(f"[INFO] ItemManager: Loaded {len(self.item_definitions)} item definitions from {definitions_path}")
        except FileNotFoundError:
            print(f"[ERROR] ItemManager: Item definitions file not found at {definitions_path}")
        except json.JSONDecodeError:
            print(f"[ERROR] ItemManager: Error decoding JSON from {definitions_path}")

    def get_item_definition(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self.item_definitions.get(item_id)

    def get_item_icon(self, item_id: str) -> Optional[pygame.Surface]:
        if item_id in self.item_icons:
            return self.item_icons[item_id]

        definition = self.get_item_definition(item_id)
        if definition and "icon_file" in definition:
            icon_filename = definition["icon_file"]
            icon_path = self.icons_base_path / icon_filename
            try:
                icon_surface = pygame.image.load(str(icon_path)).convert_alpha()
                # Można dodać skalowanie ikon, jeśli potrzebne
                # icon_surface = pygame.transform.smoothscale(icon_surface, (DESIRED_ICON_WIDTH, DESIRED_ICON_HEIGHT))
                self.item_icons[item_id] = icon_surface
                return icon_surface
            except pygame.error as e:
                print(f"[ERROR] ItemManager: Could not load icon '{icon_filename}' for item '{item_id}': {e}")

        # Zwróć placeholder, jeśli ikona nie została znaleziona lub nie ma definicji
        placeholder_size = (32, 32)  # Domyślny rozmiar
        if "DESIRED_ICON_WIDTH" in globals(): placeholder_size = (DESIRED_ICON_WIDTH, DESIRED_ICON_HEIGHT)
        placeholder = pygame.Surface(placeholder_size, pygame.SRCALPHA)
        placeholder.fill((128, 128, 128, 100))  # Szary placeholder
        pygame.draw.rect(placeholder, (200, 200, 200), placeholder.get_rect(), 1)
        self.item_icons[item_id] = placeholder  # Cache placeholder, aby nie tworzyć go za każdym razem
        return placeholder

    def item_exists(self, item_id: str) -> bool:
        return item_id in self.item_definitions