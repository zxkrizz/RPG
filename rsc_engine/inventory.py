import pygame

class Item:
    def __init__(self, name: str, icon: pygame.Surface):
        self.name = name
        self.icon = icon

class Inventory:
    def __init__(self, rows: int = 4, cols: int = 5):
        self.rows = rows
        self.cols = cols
        # slots[r][c] = Item | None
        self.slots = [[None for _ in range(cols)] for _ in range(rows)]

    def add_item(self, item: Item) -> bool:
        for r in range(self.rows):
            for c in range(self.cols):
                if self.slots[r][c] is None:
                    self.slots[r][c] = item
                    return True
        return False

    def remove_item(self, row: int, col: int) -> None:
        self.slots[row][col] = None