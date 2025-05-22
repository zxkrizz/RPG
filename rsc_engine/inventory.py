# rsc_engine/inventory.py
import pygame
from typing import TYPE_CHECKING, List, Optional, Dict, Any

if TYPE_CHECKING:
    from rsc_engine.game import Game  # Dla dostępu do item_manager


class Item:
    def __init__(self, game: "Game", item_id: str, quantity: int = 1):
        self.game = game  # Referencja do głównego obiektu gry
        self.item_id = item_id

        # Pobierz definicję, aby sprawdzić, czy przedmiot istnieje i jest stackowalny
        definition = self.game.item_manager.get_item_definition(self.item_id)
        if not definition:
            raise ValueError(f"Item with ID '{item_id}' not found in definitions.")

        self._stackable = definition.get("stackable", False)
        self._max_stack = definition.get("max_stack", 1) if self._stackable else 1

        if not self._stackable and quantity > 1:
            print(
                f"[WARNING] Item '{self.item_id}' is not stackable but quantity {quantity} was provided. Setting quantity to 1.")
            self.quantity = 1
        elif quantity > self._max_stack:
            print(
                f"[WARNING] Quantity {quantity} for item '{self.item_id}' exceeds max stack {self._max_stack}. Setting to max stack.")
            self.quantity = self._max_stack
        else:
            self.quantity = quantity

    @property
    def definition(self) -> Optional[Dict[str, Any]]:
        return self.game.item_manager.get_item_definition(self.item_id)

    @property
    def name(self) -> str:
        return self.definition.get("name", "Unknown Item") if self.definition else "Unknown Item"

    @property
    def icon(self) -> Optional[pygame.Surface]:
        # Ikona jest teraz ładowana i cachowana przez ItemManager
        return self.game.item_manager.get_item_icon(self.item_id)

    @property
    def stackable(self) -> bool:
        return self._stackable

    @property
    def max_stack(self) -> int:
        return self._max_stack

    @property
    def description(self) -> str:
        return self.definition.get("description", "") if self.definition else ""

    @property
    def type(self) -> str:
        return self.definition.get("type", "misc") if self.definition else "misc"

    @property
    def allowed_actions(self) -> List[str]:
        return self.definition.get("allowed_actions", ["examine", "drop"]) if self.definition else ["examine", "drop"]

    def get_effects(self) -> Optional[dict]:
        return self.definition.get("effects") if self.definition else None

    def __repr__(self):
        return f"Item(id='{self.item_id}', name='{self.name}', quantity={self.quantity})"


class Inventory:
    def __init__(self, game: "Game", rows: int = 4, cols: int = 5):  # Dodaj 'game'
        self.game = game  # Potrzebne do tworzenia instancji Item
        self.rows = rows
        self.cols = cols
        self.slots: List[List[Optional[Item]]] = [[None for _ in range(cols)] for _ in range(rows)]

    def add_item(self, item_id: str, quantity: int = 1) -> bool:
        if not self.game.item_manager.item_exists(item_id):
            print(f"[ERROR] Inventory: Attempted to add non-existent item ID '{item_id}'")
            return False

        item_def = self.game.item_manager.get_item_definition(item_id)
        is_stackable = item_def.get("stackable", False)
        max_stack_size = item_def.get("max_stack", 1) if is_stackable else 1

        # 1. Spróbuj dodać do istniejącego stosu, jeśli stackowalny
        if is_stackable:
            for r in range(self.rows):
                for c in range(self.cols):
                    slot_item = self.slots[r][c]
                    if slot_item and slot_item.item_id == item_id and slot_item.quantity < slot_item.max_stack:
                        can_add_to_stack = slot_item.max_stack - slot_item.quantity
                        add_amount = min(quantity, can_add_to_stack)
                        slot_item.quantity += add_amount
                        quantity -= add_amount
                        print(
                            f"[INFO] Added {add_amount} of '{item_id}' to existing stack. Remaining to add: {quantity}")
                        if quantity == 0:
                            return True

        # 2. Jeśli pozostała ilość lub przedmiot nie jest stackowalny, znajdź wolny slot
        # (lub nowy slot dla reszty stackowalnego przedmiotu)
        while quantity > 0:  # Pętla na wypadek, gdyby ilość przekraczała max_stack dla nowego slotu
            found_slot_for_new_item = False
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.slots[r][c] is None:
                        add_this_time = min(quantity, max_stack_size)
                        self.slots[r][c] = Item(self.game, item_id, add_this_time)
                        print(f"[INFO] Placed {add_this_time} of '{item_id}' in new slot ({r},{c}).")
                        quantity -= add_this_time
                        found_slot_for_new_item = True
                        if quantity == 0:
                            return True  # Wszystko dodane
            if not found_slot_for_new_item and quantity > 0:  # Brak miejsca na resztę
                print(f"[WARNING] Inventory full. Could not add remaining {quantity} of '{item_id}'.")
                return False  # Nie udało się dodać wszystkiego

        return True  # Powinno być osiągnięte, jeśli quantity == 0 na początku

    def remove_item_from_slot(self, row: int, col: int, quantity: int = 1) -> Optional[Item]:
        """Usuwa określoną ilość przedmiotu ze slotu lub cały przedmiot/stos."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            slot_item = self.slots[row][col]
            if slot_item:
                if not slot_item.stackable or quantity >= slot_item.quantity:
                    removed_item = slot_item  # Zwróć cały obiekt przedmiotu
                    self.slots[row][col] = None
                    print(f"[INFO] Removed item '{removed_item.name}' (all) from slot ({row},{col}).")
                    return removed_item
                else:  # Stackowalny, usuń część
                    slot_item.quantity -= quantity
                    print(
                        f"[INFO] Removed {quantity} of '{slot_item.name}' from slot ({row},{col}). Remaining: {slot_item.quantity}")
                    # Zwróć nowy obiekt Item z usuniętą ilością, jeśli potrzebne do np. upuszczenia
                    return Item(self.game, slot_item.item_id, quantity)
        return None

    def get_item(self, row: int, col: int) -> Optional[Item]:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.slots[row][col]
        return None