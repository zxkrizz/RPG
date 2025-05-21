from __future__ import annotations
import pygame
from rsc_engine.utils import iso_to_screen
from typing import TYPE_CHECKING, Optional  # Dla type hinting bez importów cyklicznych

if TYPE_CHECKING:
    from rsc_engine.tilemap import TileMap  # Import dla type hinting
    from rsc_engine.game import Game  # Import dla type hinting (jeśli potrzebne w przyszłości)


def bresenham(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    path: list[tuple[int, int]] = []
    while True:
        if (x, y) != (x0, y0):  # Nie dodajemy punktu startowego do ścieżki
            path.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return path


class Entity(pygame.sprite.Sprite):
    def __init__(self,
                 name: str,
                 ix: int,
                 iy: int,
                 image: pygame.Surface,
                 level: int = 1,
                 max_hp: int = 10,
                 attack_power: int = 1,
                 defense: int = 0):
        super().__init__()
        self.name = name
        self.ix = ix  # Pozycja izometryczna X (kafelek)
        self.iy = iy  # Pozycja izometryczna Y (kafelek)
        self.image = image
        self.rect = self.image.get_rect()

        # Statystyki
        self.level = level
        self.max_hp = max_hp
        self.hp = max_hp
        self.attack_power = attack_power
        self.defense = defense

        # Stan
        self.current_action: str = "idle"  # np. "idle", "walking", "attacking", "dead"
        self.is_alive: bool = True
        self.target_entity: Optional[Entity] = None  # Cel dla ataku lub interakcji

        self.update_rect()

    def update_rect(self):
        """Aktualizuje pozycję prostokąta (rect) na ekranie na podstawie współrzędnych izometrycznych."""
        sx, sy = iso_to_screen(self.ix, self.iy)
        self.rect.center = (sx, sy)

    def take_damage(self, amount: int):
        """Redukuje HP o określoną wartość, uwzględniając obronę."""
        actual_damage = max(0, amount - self.defense)  # Obrażenia nie mogą być ujemne
        self.hp -= actual_damage
        print(f"{self.name} takes {actual_damage} damage. HP: {self.hp}/{self.max_hp}")
        if self.hp <= 0:
            self.hp = 0
            self.die()

    def die(self):
        """Obsługuje śmierć encji."""
        if self.is_alive:
            print(f"{self.name} has died.")
            self.is_alive = False
            self.current_action = "dead"
            # Tutaj można dodać logikę upuszczania przedmiotów, znikania itp.
            # Na razie encja po prostu przestanie się aktualizować i może być usunięta z grupy
            # Można też zmienić jej obraz na np. zwłoki

    def attack(self, target: "Entity"):
        """Atakuje inną encję."""
        if not self.is_alive or not target.is_alive:
            return

        print(f"{self.name} attacks {target.name}!")
        # Prosty system walki - można rozbudować
        target.take_damage(self.attack_power)
        # Tutaj można dodać cooldown ataku

    def interact(self, interactor: "Entity"):
        """
        Podstawowa metoda interakcji. Powinna być nadpisana przez klasy pochodne.
        `interactor` to encja, która inicjuje interakcję (np. gracz).
        """
        print(f"{interactor.name} interacts with {self.name}. Nothing special happens.")

    def update(self, dt: float, tilemap: "TileMap", all_entities: pygame.sprite.Group):
        """
        Główna metoda aktualizacji logiki encji.
        `all_entities` to grupa wszystkich encji, aby NPC mogły np. widzieć gracza.
        """
        if not self.is_alive:
            # Martwe encje nie robią nic (chyba że mają animację śmierci)
            return

        # Podstawowa logika ruchu (jeśli jest) będzie w Player/NPC
        pass


class Player(Entity):
    def __init__(self,
                 name: str,
                 ix: int,
                 iy: int,
                 image: pygame.Surface,
                 level: int = 1,
                 max_hp: int = 100,  # Gracz ma więcej HP
                 attack_power: int = 10,
                 defense: int = 2):
        super().__init__(name, ix, iy, image, level, max_hp, attack_power, defense)
        self.move_cooldown_max = 0.15  # Czas odnowienia ruchu w sekundach
        self.move_cooldown = 0.0
        self.path: list[tuple[int, int]] = []
        self.target_tile_coords: tuple[int, int] | None = None  # Cel na mapie do rysowania 'X'

    def set_path(self, tx: int, ty: int, tilemap: "TileMap"):  # Dodajemy tilemap do walidacji celu
        """Generuje ścieżkę do celu (tx, ty) i zapisuje cel do rysowania X."""
        # Podstawowa walidacja, czy cel jest w granicach mapy
        if 0 <= tx < tilemap.width and 0 <= ty < tilemap.height:
            # Sprawdź, czy kafelek docelowy nie jest blokowany (jeśli masz system kolizji mapy)
            # if not tilemap.is_blocked(tx, ty):
            self.path = bresenham(self.ix, self.iy, tx, ty)
            self.target_tile_coords = (tx, ty)
            if self.path:
                self.current_action = "walking"
            else:  # Jeśli ścieżka jest pusta (np. kliknięto na ten sam kafelek)
                self.current_action = "idle"
                self.target_tile_coords = None  # Usuń X, jeśli nie ma ruchu
        else:
            print(f"Cel ({tx},{ty}) jest poza granicami mapy.")
            self.path = []
            self.target_tile_coords = None
            self.current_action = "idle"

    def update(self, dt: float, tilemap: "TileMap", all_entities: pygame.sprite.Group):
        super().update(dt, tilemap, all_entities)  # Wywołaj update z klasy bazowej
        if not self.is_alive:
            return

        self.move_cooldown = max(0.0, self.move_cooldown - dt)

        if self.path and self.move_cooldown == 0.0:
            self.current_action = "walking"
            nx, ny = self.path.pop(0)

            # Prosta walidacja granic mapy i ewentualnej kolizji kafelka
            # (rozbudować o sprawdzanie `tilemap.is_blocked(nx,ny)`)
            can_move = True
            if not (0 <= nx < tilemap.width and 0 <= ny < tilemap.height):
                can_move = False
            # Dodaj tu sprawdzanie kolizji z mapą, np.:
            # if tilemap.is_solid(nx, ny):
            #     can_move = False
            #     self.path = [] # Zatrzymaj ruch, jeśli trafiono na przeszkodę
            #     self.target_tile_coords = None
            #     self.current_action = "idle"

            if can_move:
                self.ix, self.iy = nx, ny
                self.update_rect()
                self.move_cooldown = self.move_cooldown_max

            if not self.path:  # Jeśli dotarliśmy do końca ścieżki
                self.target_tile_coords = None
                self.current_action = "idle"
        elif not self.path and self.current_action == "walking":  # Jeśli skończyła się ścieżka
            self.current_action = "idle"


class NPC(Entity):
    def __init__(self,
                 name: str,
                 ix: int,
                 iy: int,
                 image: pygame.Surface,
                 level: int = 1,
                 max_hp: int = 20,
                 attack_power: int = 5,
                 defense: int = 1,
                 movement_pattern: str = "stationary",  # "stationary", "patrol", "wander"
                 dialogue: Optional[list[str]] = None):
        super().__init__(name, ix, iy, image, level, max_hp, attack_power, defense)
        self.movement_pattern = movement_pattern
        self.dialogue = dialogue if dialogue else []
        self.patrol_points: list[tuple[int, int]] = []
        self.current_patrol_point_idx: int = 0
        self.path: list[tuple[int, int]] = []  # Ścieżka dla NPC
        self.move_cooldown_max = 0.3  # NPC mogą być wolniejsi
        self.move_cooldown = 0.0

    def update_ai(self, dt: float, tilemap: "TileMap", player: Player, all_entities: pygame.sprite.Group):
        """Logika AI specyficzna dla NPC."""
        pass  # Zostanie zaimplementowana w FriendlyNPC i HostileNPC

    def update(self, dt: float, tilemap: "TileMap", all_entities: pygame.sprite.Group):
        super().update(dt, tilemap, all_entities)  # Wywołaj update z klasy bazowej
        if not self.is_alive:
            return

        # Znajdź gracza w all_entities (potrzebne dla HostileNPC)
        # W tym prostym przykładzie zakładamy, że Player jest przekazywany bezpośrednio
        # lub jest jedynym obiektem typu Player w all_entities.
        # Lepszym rozwiązaniem byłoby przekazanie referencji do gracza do metody update_ai.
        player_ref = None
        for entity in all_entities:
            if isinstance(entity, Player):
                player_ref = entity
                break

        if player_ref:
            self.update_ai(dt, tilemap, player_ref, all_entities)

        # Podstawowa logika ruchu dla NPC (jeśli mają ścieżkę)
        self.move_cooldown = max(0.0, self.move_cooldown - dt)
        if self.path and self.move_cooldown == 0.0:
            self.current_action = "walking"
            nx, ny = self.path.pop(0)
            # Prosta walidacja granic mapy i ewentualnej kolizji kafelka
            if 0 <= nx < tilemap.width and 0 <= ny < tilemap.height:  # and not tilemap.is_solid(nx, ny)
                self.ix, self.iy = nx, ny
                self.update_rect()
                self.move_cooldown = self.move_cooldown_max
            else:  # Trafiono na przeszkodę lub koniec mapy
                self.path = []
                self.current_action = "idle"

            if not self.path:
                self.current_action = "idle"
        elif not self.path and self.current_action == "walking":
            self.current_action = "idle"


class FriendlyNPC(NPC):
    def __init__(self,
                 name: str,
                 ix: int,
                 iy: int,
                 image: pygame.Surface,
                 level: int = 1,
                 max_hp: int = 30,
                 dialogue: Optional[list[str]] = None):
        super().__init__(name, ix, iy, image, level, max_hp, attack_power=0, defense=0, movement_pattern="stationary",
                         dialogue=dialogue)
        # FriendlyNPC domyślnie nie atakują

    def interact(self, interactor: "Entity"):
        if isinstance(interactor, Player):  # Tylko gracz może rozmawiać
            if self.dialogue:
                # Prosta logika dialogu - wyświetl pierwszą linię lub losową
                # W przyszłości można tu zaimplementować system dialogowy
                print(f"[{self.name}]: {self.dialogue[0]}")
                # Można by to przekazać do UI, aby wyświetlić w dymku
            else:
                print(f"[{self.name}]: Witaj, {interactor.name}!")
        else:
            super().interact(interactor)

    def update_ai(self, dt: float, tilemap: "TileMap", player: Player, all_entities: pygame.sprite.Group):
        # Przyjazny NPC może np. spacerować, jeśli ma ustawiony 'wander' lub 'patrol'
        # Na razie pozostaje stacjonarny lub wykonuje prosty ruch po ścieżce
        if self.movement_pattern == "wander" and not self.path and self.current_action == "idle":
            # Prosta logika błądzenia: co jakiś czas wybierz losowy pobliski cel
            # if random.random() < 0.01: # Szansa na rozpoczęcie błądzenia
            #     tx = self.ix + random.randint(-3, 3)
            #     ty = self.iy + random.randint(-3, 3)
            #     if 0 <= tx < tilemap.width and 0 <= ty < tilemap.height:
            #         self.path = bresenham(self.ix, self.iy, tx, ty)
            pass  # Logika błądzenia do zaimplementowania
        elif self.movement_pattern == "patrol" and not self.path and self.patrol_points and self.current_action == "idle":
            # Logika patrolowania
            # target_patrol_point = self.patrol_points[self.current_patrol_point_idx]
            # self.path = bresenham(self.ix, self.iy, target_patrol_point[0], target_patrol_point[1])
            # self.current_patrol_point_idx = (self.current_patrol_point_idx + 1) % len(self.patrol_points)
            pass  # Logika patrolowania do zaimplementowania


class HostileNPC(NPC):
    def __init__(self,
                 name: str,
                 ix: int,
                 iy: int,
                 image: pygame.Surface,
                 level: int = 1,
                 max_hp: int = 50,
                 attack_power: int = 8,
                 defense: int = 3,
                 aggro_radius: int = 5,  # Zasięg w kafelkach, w którym NPC staje się agresywny
                 attack_cooldown_max: float = 2.0):  # Cooldown między atakami
        super().__init__(name, ix, iy, image, level, max_hp, attack_power, defense, movement_pattern="stationary")
        self.aggro_radius = aggro_radius
        self.is_hostile = True  # Oznaczamy, że ten NPC jest wrogi
        self.attack_cooldown_max = attack_cooldown_max
        self.attack_cooldown = 0.0
        self.is_chasing = False

    def interact(self, interactor: "Entity"):
        if isinstance(interactor, Player) and self.is_alive:
            # Gracz klikający na wrogiego NPC może go zaatakować
            print(f"{interactor.name} considers attacking {self.name}.")
            # Dalsza logika ataku może być zarządzana przez system menu kontekstowego
            # lub bezpośrednio, np. interactor.attack(self)
        else:
            super().interact(interactor)

    def update_ai(self, dt: float, tilemap: "TileMap", player: Player, all_entities: pygame.sprite.Group):
        if not player.is_alive:  # Jeśli gracz nie żyje, wróg przestaje go ścigać
            self.is_chasing = False
            self.target_entity = None
            self.path = []
            self.current_action = "idle"
            return

        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)

        # Oblicz odległość do gracza (w przybliżeniu, Manhattan distance na siatce izometrycznej)
        distance_to_player = abs(self.ix - player.ix) + abs(self.iy - player.iy)

        if self.target_entity and not self.target_entity.is_alive:  # Jeśli cel umarł
            self.target_entity = None
            self.is_chasing = False
            self.path = []
            self.current_action = "idle"

        if self.target_entity == player:  # Jeśli aktualnym celem jest gracz
            if distance_to_player <= 1 and self.attack_cooldown == 0.0:  # W zasięgu ataku (sąsiedni kafelek)
                self.path = []  # Zatrzymaj ruch podczas ataku
                self.current_action = "attacking"
                self.attack(player)
                self.attack_cooldown = self.attack_cooldown_max
            elif distance_to_player > self.aggro_radius * 1.5:  # Gracz uciekł za daleko
                self.target_entity = None
                self.is_chasing = False
                self.path = []
                self.current_action = "idle"
            elif distance_to_player > 1:  # Gracz jest w zasięgu aggro, ale nie w zasięgu ataku - ścigaj
                self.is_chasing = True
                # Aktualizuj ścieżkę co jakiś czas, nie w każdej klatce
                if not self.path or (self.path and (player.ix, player.iy) != self.path[-1]):
                    self.path = bresenham(self.ix, self.iy, player.ix, player.iy)
                    if self.path:
                        self.current_action = "walking"

        elif distance_to_player <= self.aggro_radius and not self.is_chasing:  # Gracz wszedł w zasięg aggro
            print(f"{self.name} spots {player.name}!")
            self.target_entity = player
            self.is_chasing = True
            self.path = bresenham(self.ix, self.iy, player.ix, player.iy)
            if self.path:
                self.current_action = "walking"

        # Prosta logika powrotu na startową pozycję, jeśli nie ściga (do rozbudowy)
        # if not self.is_chasing and self.movement_pattern == "stationary" and (self.ix != self.start_ix or self.iy != self.start_iy):
        #     # Wróć na pozycję startową
        #     pass