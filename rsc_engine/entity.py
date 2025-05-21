from __future__ import annotations
import pygame
from rsc_engine.utils import iso_to_screen  #
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Callable

if TYPE_CHECKING:
    from rsc_engine.tilemap import TileMap  #
    from rsc_engine.game import Game  #


def bresenham(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:  #
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    path: list[tuple[int, int]] = []
    while True:
        if (x, y) != (x0, y0):
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


class Entity(pygame.sprite.Sprite):  #
    def __init__(self,
                 game: "Game",
                 name: str,
                 ix: int,
                 iy: int,
                 image: pygame.Surface,
                 level: int = 1,
                 max_hp: int = 10,
                 attack_power: int = 1,
                 defense: int = 0,
                 attack_speed: float = 1.5):  # Domyślna prędkość ataku
        super().__init__()
        self.game = game
        self.name = name
        self.ix = ix
        self.iy = iy
        self.image = image
        self.rect = self.image.get_rect()  #

        self.level = level
        self.max_hp = max_hp  #
        self.hp = max_hp  #
        self.attack_power = attack_power
        self.defense = defense

        self.current_action: str = "idle"  # np. "idle", "walking", "fighting", "dead"
        self.is_alive: bool = True

        # --- Atrybuty walki ---
        self.in_combat: bool = False
        self.combat_target: Optional[Entity] = None
        self.attack_speed: float = attack_speed
        self.attack_cooldown_timer: float = 0.0
        self.show_hp_bar: bool = False  # Czy pokazywać pasek HP nad tą encją

        self.update_rect()

    def update_rect(self):  #
        sx, sy = iso_to_screen(self.ix, self.iy)  #
        self.rect.center = (sx, sy)

    def take_damage(self, amount: int):
        actual_damage = max(0, amount - self.defense)
        self.hp -= actual_damage

        # Tworzenie DamageSplat
        # Sprawdź, czy self.game istnieje i ma metodę create_damage_splat
        # Pokaż splat nawet jeśli to był śmiertelny cios (stąd warunek na hp+actual_damage)
        if hasattr(self.game, 'create_damage_splat') and (
                self.is_alive or (not self.is_alive and self.hp + actual_damage > 0)):
            self.game.create_damage_splat(actual_damage, self)

        print(f"[COMBAT] {self.name} takes {actual_damage} damage. HP: {self.hp}/{self.max_hp}")

        if isinstance(self, HostileNPC) and self.is_alive:
            self.show_hp_bar = True

        if self.hp <= 0 and self.is_alive:
            self.hp = 0
            self.die()

    def die(self):
        if self.is_alive:
            print(f"[COMBAT] {self.name} has died.")
            self.is_alive = False
            self.current_action = "dead"
            self.show_hp_bar = False

            former_target = self.combat_target
            if self.in_combat:
                self.in_combat = False
                self.combat_target = None

            if former_target and former_target.combat_target == self:
                print(
                    f"[DEBUG] {former_target.name} was targeting the now dead {self.name}. {former_target.name} leaves combat.")
                former_target.leave_combat()

            if hasattr(self.game, 'entities'):  # Upewnij się, że game i entities istnieją
                for entity in self.game.entities:
                    if entity.combat_target == self and entity.is_alive:
                        print(
                            f"[DEBUG] {entity.name} was targeting the now dead {self.name}. {entity.name} leaves combat.")
                        entity.leave_combat()

    def attack(self, target: "Entity"):
        if not self.is_alive or not target.is_alive:
            if self.in_combat: self.leave_combat()
            return

        print(f"[COMBAT] {self.name} (HP: {self.hp}) attacks {target.name} (HP: {target.hp})!")
        target.take_damage(self.attack_power)

    def enter_combat_with(self, target: Entity):
        if not target or not target.is_alive or not self.is_alive:
            if self.in_combat: self.leave_combat()
            return

        if self.in_combat and self.combat_target == target:
            if isinstance(self, HostileNPC): self.show_hp_bar = True
            return

        print(f"[COMBAT] {self.name} enters combat with {target.name}")
        self.in_combat = True
        self.combat_target = target
        self.current_action = "fighting"
        self.path = []
        if hasattr(self, 'target_tile_coords'):
            self.target_tile_coords = None
        if hasattr(self, 'action_after_reaching_target'):
            self.action_after_reaching_target = None
            self.target_entity_for_action = None

        self.attack_cooldown_timer = 0.0

        if isinstance(self, HostileNPC):
            self.show_hp_bar = True

        if not target.in_combat or target.combat_target != self:
            # Cel również wchodzi w walkę
            # Nie wywołuj enter_combat_with dla celu tutaj, jeśli cel to gracz, bo gracz sam zarządza swoim wejściem w walkę
            # przez Player.initiate_attack_on_target LUB gdy jest atakowany przez NPC (co obsłuży _handle_automatic_combat celu)
            if isinstance(target, Player):
                print(
                    f"[DEBUG] {target.name} (Player) is now targeted by {self.name}, should enter combat if attacked.")
                # Gracz wejdzie w walkę, gdy _handle_automatic_combat NPC go zaatakuje,
                # lub jeśli sam zainicjował atak.
                # Dla pewności, można tu ustawić flagi gracza, jeśli NPC go atakuje.
                if not target.in_combat:  # Jeśli gracz nie jest jeszcze w walce
                    target.in_combat = True
                    target.combat_target = self
                    target.current_action = "fighting"
                    print(f"[DEBUG] {target.name} (Player) was not in combat, now fighting {self.name}")
                # Pokaż pasek HP tego NPC, bo gracz go teraz atakuje (lub jest przez niego atakowany)
                if isinstance(self, HostileNPC):
                    self.show_hp_bar = True

            elif isinstance(target, NPC):  # NPC vs NPC
                target.enter_combat_with(self)

    def leave_combat(self):
        if not self.in_combat: return

        print(f"[COMBAT] {self.name} leaves combat with {self.combat_target.name if self.combat_target else 'nobody'}.")

        former_target = self.combat_target
        self.in_combat = False
        self.combat_target = None

        if self.is_alive:
            if not (isinstance(self, HostileNPC) and hasattr(self, 'is_chasing') and self.is_chasing):
                self.current_action = "idle"

        if isinstance(self, HostileNPC) and self.is_alive:  # Pasek HP wrogiego NPC może pozostać widoczny
            pass  # self.show_hp_bar = False # Można dodać timer zanikania paska HP

        if former_target and former_target.is_alive and former_target.combat_target == self:
            former_target.leave_combat()

    def _handle_automatic_combat(self, dt: float):
        if not self.in_combat or not self.combat_target:
            if self.in_combat: self.leave_combat()
            return

        if not self.combat_target.is_alive:
            print(f"[DEBUG] {self.name}'s combat target {self.combat_target.name} is dead. Leaving combat.")  # DEBUG
            self.leave_combat()
            return

        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)

        dx = abs(self.ix - self.combat_target.ix)
        dy = abs(self.iy - self.combat_target.iy)
        distance_to_target = max(dx, dy)

        attack_range = 1

        if distance_to_target <= attack_range:
            if self.path and self.current_action == "walking":
                self.path = []
                print(f"[DEBUG] {self.name} reached melee range of {self.combat_target.name}, stopping path.")

            self.current_action = "fighting"

            if self.attack_cooldown_timer == 0.0:
                self.attack(self.combat_target)
                self.attack_cooldown_timer = self.attack_speed
        else:  # Cel poza zasięgiem ataku
            if self.current_action == "fighting":
                self.current_action = "idle"  # Wróć do idle, AI/logika ruchu zdecyduje co dalej

            if isinstance(self, Player):
                if not self.path:
                    print(
                        f"[DEBUG] Player {self.name}: Combat target {self.combat_target.name} is out of range. Player needs to move or re-engage.")
            elif isinstance(self, HostileNPC):
                # Logika ścigania dla HostileNPC jest w update_ai.
                # update_ai powinno ustawić self.path, jeśli NPC ma ścigać.
                if not self.path and hasattr(self, 'is_chasing') and self.is_chasing:  # Jeśli ściga, a nie ma ścieżki
                    print(
                        f"[DEBUG] HostileNPC {self.name} (in _handle_automatic_combat): Target out of range, AI should set path soon.")
                    pass  # Pozwól update_ai ustawić ścieżkę

    def interact(self, interactor: "Entity"):
        print(f"[DEBUG] Entity '{self.name}' generic interact by '{interactor.name}'")
        print(f"{interactor.name} interacts with {self.name}. Nothing special happens.")

    def get_context_menu_options(self, interactor: "Entity") -> List[Dict[str, Any]]:
        options = []
        if self.is_alive:
            # Opcja Attack jest dodawana w HostileNPC.get_context_menu_options
            options.append({
                "text": f"Examine {self.name}",
                "action": lambda ignored_target: self.game.show_examine_text(self),
                "target": self
            })
        return options

    def update(self, dt: float, tilemap: "TileMap", all_entities: pygame.sprite.Group):
        if not self.is_alive:
            self.show_hp_bar = False
            return

        self._handle_automatic_combat(dt)
        # Logika ruchu i AI specyficzna dla klas pochodnych będzie w ich metodach update/update_ai
        pass


class Player(Entity):
    def __init__(self, game: "Game", name: str, ix: int, iy: int, image: pygame.Surface,
                 level: int = 1, max_hp: int = 100, attack_power: int = 10, defense: int = 2,
                 attack_speed: float = 1.0):
        super().__init__(game, name, ix, iy, image, level, max_hp, attack_power, defense, attack_speed)
        self.move_cooldown_max = 0.15
        self.move_cooldown = 0.0
        self.path: list[tuple[int, int]] = []
        self.target_tile_coords: tuple[int, int] | None = None

        self.target_entity_for_action: Optional[Entity] = None
        self.action_after_reaching_target: Optional[Callable] = None

    def set_path(self, tx: int, ty: int, tilemap: "TileMap", is_manual_walk_command: bool = False):
        print(f"[DEBUG] Player.set_path called for ({tx},{ty}). Manual: {is_manual_walk_command}")

        if is_manual_walk_command and self.in_combat:
            print(
                f"[DEBUG] Player {self.name} received manual walk, leaving combat with {self.combat_target.name if self.combat_target else 'nobody'}.")
            self.leave_combat()

        if 0 <= tx < tilemap.width and 0 <= ty < tilemap.height:
            if is_manual_walk_command:
                print("[DEBUG] Player.set_path: Manual walk command, clearing action_after_reaching_target.")
                self.action_after_reaching_target = None
                self.target_entity_for_action = None
                # self.target_entity = None # To pole nie jest już używane w Entity

            self.path = bresenham(self.ix, self.iy, tx, ty)
            self.target_tile_coords = (tx, ty)
            if self.path:
                self.current_action = "walking"
                # Jeśli zaczynamy iść, a byliśmy w walce (i nie idziemy do celu walki)
                if self.in_combat and self.current_action == "fighting":  # Poprzedni stan mógł być fighting
                    is_moving_to_combat_target = False
                    if self.combat_target and self.path:
                        # Sprawdź czy ostatni punkt ścieżki to cel walki
                        path_target_x, path_target_y = self.path[-1]
                        if path_target_x == self.combat_target.ix and path_target_y == self.combat_target.iy:
                            is_moving_to_combat_target = True

                    if not is_moving_to_combat_target:
                        print(f"[DEBUG] Player {self.name} started walking (not to combat target), leaving combat.")
                        self.leave_combat()
            else:  # Ścieżka pusta
                self.current_action = "idle"
                self.target_tile_coords = None
                # Jeśli była akcja (np. Talk), a ścieżka od razu pusta (np. cel obok)
                if self.action_after_reaching_target:
                    print("[DEBUG] Player.set_path: Path is empty, but action was queued. Attempting immediate action.")
                    action_to_run = self.action_after_reaching_target
                    target_for_action = self.target_entity_for_action
                    self.action_after_reaching_target = None
                    self.target_entity_for_action = None
                    if target_for_action:
                        action_to_run(target_for_action)
                    else:
                        action_to_run()
        else:
            print(f"[DEBUG] Player.set_path: Target ({tx},{ty}) is out of map bounds.")
            self.path = []
            self.target_tile_coords = None
            self.current_action = "idle"
            if self.in_combat:
                print(f"[DEBUG] Player {self.name}: Path target out of bounds, leaving combat.")
                self.leave_combat()
            print("[DEBUG] Player.set_path: Target out of bounds, clearing action_after_reaching_target.")
            self.action_after_reaching_target = None
            self.target_entity_for_action = None

    def initiate_attack_on_target(self, target_npc: HostileNPC):
        print(f"[DEBUG] Player.initiate_attack_on_target: Targeting {target_npc.name if target_npc else 'None'}")
        if not target_npc or not target_npc.is_alive or not self.is_alive:
            if self.in_combat and self.combat_target == target_npc: self.leave_combat()
            return

        # Jeśli już walczymy z tym celem, nie rób nic (chyba że chcemy np. wymusić podejście)
        if self.in_combat and self.combat_target == target_npc:
            print(f"[DEBUG] Player {self.name} already in combat with {target_npc.name}.")
            # Sprawdź dystans, jeśli za daleko, podejdź
            distance_to_target = max(abs(self.ix - target_npc.ix), abs(self.iy - target_npc.iy))
            if distance_to_target > 1 and not self.path:  # Jeśli nie idzie, a jest za daleko
                self.path = bresenham(self.ix, self.iy, target_npc.ix, target_npc.iy)
                if self.path: self.current_action = "walking"; self.target_tile_coords = (target_npc.ix, target_npc.iy)
            return

        print(f"[DEBUG] Player {self.name} is initiating attack sequence on {target_npc.name} via walk_and_act.")
        # Użyj player_walk_to_and_act, aby gracz podszedł, a PO DOJŚCIU wszedł w walkę.
        self.game.player_walk_to_and_act(
            (target_npc.ix, target_npc.iy),
            # Akcja do wykonania po dojściu: wejdź w walkę
            lambda npc_to_engage: self.enter_combat_with(npc_to_engage),
            target_npc
        )

    def start_following(self, target_to_follow: Entity):
        if target_to_follow and target_to_follow.is_alive:
            print(f"[DEBUG] Player.start_following: {target_to_follow.name}.")
            self.game.player_walk_to_and_act(
                (target_to_follow.ix, target_to_follow.iy),
                lambda followed_target: print(
                    f"Arrived at {followed_target.name} (follow stub). Player should now continuously follow."),
                target_to_follow
            )
        else:
            print(
                f"[DEBUG] Player.start_following: Cannot follow {target_to_follow.name if target_to_follow else 'None'}.")

    def update(self, dt: float, tilemap: "TileMap", all_entities: pygame.sprite.Group):
        super().update(dt, tilemap, all_entities)
        if not self.is_alive:
            return

        self.move_cooldown = max(0.0, self.move_cooldown - dt)

        is_fighting_in_melee_range = False
        if self.in_combat and self.combat_target and self.combat_target.is_alive:
            distance_to_combat_target = max(abs(self.ix - self.combat_target.ix), abs(self.iy - self.combat_target.iy))
            if distance_to_combat_target <= 1:
                is_fighting_in_melee_range = True
                if self.path and self.current_action == "walking":
                    print(
                        f"[DEBUG] Player {self.name}: Reached melee range of {self.combat_target.name} while walking, clearing path to fight.")
                    self.path = []
                    self.target_tile_coords = None
                self.current_action = "fighting"

        if self.path and self.move_cooldown == 0.0 and not is_fighting_in_melee_range:
            self.current_action = "walking"
            if not self.path: self.current_action = "idle"; return

            nx, ny = self.path[0]
            can_move = True
            if not (0 <= nx < tilemap.width and 0 <= ny < tilemap.height):
                print(f"[DEBUG] Player {self.name}: Next step ({nx},{ny}) out of map bounds. Cancelling path.")
                can_move = False;
                self.path = [];
                self.target_tile_coords = None
                if self.action_after_reaching_target: self.action_after_reaching_target = None; self.target_entity_for_action = None
                if self.in_combat:
                    print(f"[DEBUG] Player {self.name}: Path to combat target leads out of map. Leaving combat.")
                    self.leave_combat()

                    # TODO: Kolizja z terenem

            if can_move and self.game.is_tile_occupied_by_entity(nx, ny, excluding_entity=self):
                occupied_by_entity = None
                for e in all_entities:
                    if e.ix == nx and e.iy == ny and e != self and e.is_alive:
                        occupied_by_entity = e;
                        break

                can_move = False

                is_next_step_combat_target = self.combat_target and occupied_by_entity == self.combat_target
                is_next_step_action_target = self.target_entity_for_action and occupied_by_entity == self.target_entity_for_action

                if is_next_step_combat_target or is_next_step_action_target:
                    target_name = occupied_by_entity.name if occupied_by_entity else "target"
                    print(
                        f"[DEBUG] Player {self.name}: Next step is target {target_name} at ({nx},{ny}). Stopping before it.")
                    self.path = []
                else:
                    blocker_name = occupied_by_entity.name if occupied_by_entity else "unknown entity"
                    print(
                        f"[DEBUG] Player {self.name}: Path to target blocked by {blocker_name} at ({nx},{ny}). Cancelling path and current objective.")
                    self.path = []
                    self.target_tile_coords = None
                    if self.in_combat:
                        print(f"[DEBUG] Player {self.name}: Path to combat target blocked. Leaving combat.")
                        self.leave_combat()
                    if self.action_after_reaching_target:
                        print(f"[DEBUG] Player {self.name}: Path to action target blocked. Cancelling action.")
                        self.action_after_reaching_target = None
                        self.target_entity_for_action = None

            if can_move:
                self.path.pop(0);
                self.ix, self.iy = nx, ny;
                self.update_rect();
                self.move_cooldown = self.move_cooldown_max

            if not self.path:
                self.target_tile_coords = None
                if self.action_after_reaching_target:
                    action_to_run = self.action_after_reaching_target;
                    target_for_action = self.target_entity_for_action

                    self.action_after_reaching_target = None;
                    self.target_entity_for_action = None

                    print(
                        f"[DEBUG] Player.update: Executing queued action {action_to_run} on {target_for_action.name if target_for_action else 'None'}")
                    if target_for_action:
                        action_to_run(target_for_action)
                    else:
                        action_to_run()

                is_fighting_in_melee_range_after_action = False
                if self.in_combat and self.combat_target and self.combat_target.is_alive:
                    if max(abs(self.ix - self.combat_target.ix), abs(self.iy - self.combat_target.iy)) <= 1:
                        is_fighting_in_melee_range_after_action = True

                if is_fighting_in_melee_range_after_action:
                    self.current_action = "fighting"
                else:
                    if not self.in_combat:
                        self.current_action = "idle"

        elif not self.path:
            if self.in_combat and self.combat_target and self.combat_target.is_alive and \
                    max(abs(self.ix - self.combat_target.ix), abs(self.iy - self.combat_target.iy)) <= 1:
                self.current_action = "fighting"
            elif self.current_action == "walking":
                self.current_action = "idle"


class NPC(Entity):
    def __init__(self, game: "Game", name: str, ix: int, iy: int, image: pygame.Surface,
                 level: int = 1, max_hp: int = 20, attack_power: int = 5, defense: int = 1,
                 movement_pattern: str = "stationary", dialogue: Optional[list[str]] = None,
                 attack_speed: float = 2.0):
        super().__init__(game, name, ix, iy, image, level, max_hp, attack_power, defense, attack_speed)
        self.movement_pattern = movement_pattern
        self.dialogue = dialogue if dialogue else []
        self.patrol_points: list[tuple[int, int]] = []
        self.current_patrol_point_idx: int = 0
        self.path: list[tuple[int, int]] = []
        self.move_cooldown_max = 0.3
        self.move_cooldown = 0.0

    def update_ai(self, dt: float, tilemap: "TileMap", player: Player, all_entities: pygame.sprite.Group):
        pass

    def update(self, dt: float, tilemap: "TileMap", all_entities: pygame.sprite.Group):
        super().update(dt, tilemap, all_entities)
        if not self.is_alive:
            return

        player_ref = None
        for entity_sprite in all_entities:
            if isinstance(entity_sprite, Player):
                player_ref = entity_sprite;
                break

        is_fighting_in_melee_range = False
        if self.in_combat and self.combat_target and self.combat_target.is_alive:
            if max(abs(self.ix - self.combat_target.ix), abs(self.iy - self.combat_target.iy)) <= 1:
                is_fighting_in_melee_range = True

        if player_ref and self.is_alive:
            if not is_fighting_in_melee_range or isinstance(self, HostileNPC):
                self.update_ai(dt, tilemap, player_ref, all_entities)

        self.move_cooldown = max(0.0, self.move_cooldown - dt)

        if self.path and self.move_cooldown == 0.0 and not is_fighting_in_melee_range:
            self.current_action = "walking"
            if not self.path: self.current_action = "idle"; return

            nx, ny = self.path[0]
            can_move = True
            if not (0 <= nx < tilemap.width and 0 <= ny < tilemap.height):
                can_move = False;
                self.path = []

            if can_move and self.game.is_tile_occupied_by_entity(nx, ny, excluding_entity=self):
                occupied_by_entity = None
                for e in all_entities:
                    if e.ix == nx and e.iy == ny and e != self and e.is_alive:
                        occupied_by_entity = e;
                        break
                can_move = False

                is_next_step_combat_target = self.combat_target and occupied_by_entity == self.combat_target
                if is_next_step_combat_target:
                    print(f"[DEBUG] NPC {self.name}: Reached combat target {self.combat_target.name}. Stopping.")
                    self.path = []
                else:
                    print(
                        f"[DEBUG] NPC {self.name}: Path blocked by {occupied_by_entity.name if occupied_by_entity else 'unknown entity'}. Stopping.")
                    self.path = []

            if can_move:
                self.path.pop(0);
                self.ix, self.iy = nx, ny;
                self.update_rect();
                self.move_cooldown = self.move_cooldown_max

            if not self.path:
                if not is_fighting_in_melee_range:
                    self.current_action = "idle"
                else:
                    self.current_action = "fighting"
        elif not self.path:
            if self.in_combat and is_fighting_in_melee_range:
                self.current_action = "fighting"
            elif self.current_action == "walking":
                self.current_action = "idle"


class FriendlyNPC(NPC):
    def __init__(self, game: "Game", name: str, ix: int, iy: int, image: pygame.Surface,
                 level: int = 1, max_hp: int = 30, dialogue: Optional[list[str]] = None):
        super().__init__(game, name, ix, iy, image, level, max_hp, attack_power=0, defense=0,
                         movement_pattern="stationary", dialogue=dialogue, attack_speed=9999)

    def interact(self, interactor: "Entity"):
        print(f"[DEBUG] FriendlyNPC '{self.name}' interact called by '{interactor.name}'")
        if isinstance(interactor, Player):
            if interactor.path: interactor.path = []
            interactor.current_action = "idle"

            if self.dialogue:
                print(f"[DEBUG] FriendlyNPC '{self.name}' has dialogue. Calling self.game.ui.show_dialogue.")
                self.game.ui.show_dialogue(self.name, self.dialogue)
            else:
                print(
                    f"[DEBUG] FriendlyNPC '{self.name}' has NO dialogue. Calling self.game.ui.show_dialogue with default.")
                self.game.ui.show_dialogue(self.name, [f"Witaj, {interactor.name}!"])
        else:
            super().interact(interactor)

    def get_context_menu_options(self, interactor: "Entity") -> List[Dict[str, Any]]:
        options = super().get_context_menu_options(interactor)
        if self.is_alive and isinstance(interactor, Player):
            options.insert(0, {
                "text": f"Talk to {self.name}",
                "action": lambda ignored_target: self.game.initiate_dialogue_with_npc(self),
                "target": self
            })
            # Usunięto "Follow" dla FriendlyNPC dla uproszczenia
        return options

    def update_ai(self, dt: float, tilemap: "TileMap", player: Player, all_entities: pygame.sprite.Group):
        pass


class HostileNPC(NPC):
    def __init__(self, game: "Game", name: str, ix: int, iy: int, image: pygame.Surface,
                 level: int = 1, max_hp: int = 50, attack_power: int = 8, defense: int = 3,
                 aggro_radius: int = 5,
                 attack_speed: float = 1.8):
        super().__init__(game, name, ix, iy, image, level, max_hp, attack_power, defense,
                         movement_pattern="stationary", dialogue=None, attack_speed=attack_speed)
        self.aggro_radius = aggro_radius
        self.attack_cooldown_timer = self.attack_speed
        self.is_chasing = False
        self.start_ix, self.start_iy = ix, iy

    def get_context_menu_options(self, interactor: "Entity") -> List[Dict[str, Any]]:
        options = super().get_context_menu_options(interactor)
        if self.is_alive and isinstance(interactor, Player):
            if not (interactor.in_combat and interactor.combat_target == self):
                options.insert(0, {
                    "text": f"Attack {self.name}",
                    "action": lambda ignored_target: interactor.initiate_attack_on_target(self),
                    "target": self
                })
        return options

    def update_ai(self, dt: float, tilemap: "TileMap", player: Player, all_entities: pygame.sprite.Group):
        if not self.is_alive: return

        # Jeśli NPC jest w walce i w zasięgu, _handle_automatic_combat zajmie się atakiem.
        # AI tutaj decyduje o ściganiu/powrocie, jeśli nie jest w bezpośrednim zwarciu.
        if self.in_combat and self.combat_target == player:
            distance_to_player = max(abs(self.ix - player.ix), abs(self.iy - player.iy))
            if distance_to_player <= 1:
                if self.path: self.path = []
                self.current_action = "fighting"
                return
            else:  # Cel walki jest poza zasięgiem, ścigaj
                # Aktualizuj ścieżkę, jeśli gracz się ruszył, NPC nie ma ścieżki, lub ścieżka nie prowadzi do gracza
                if not self.path or (self.path and (player.ix, player.iy) != self.path[-1]):
                    print(
                        f"[DEBUG] HostileNPC {self.name} (AI): Combat target {player.name} out of melee, recalculating path.")
                    self.path = bresenham(self.ix, self.iy, player.ix, player.iy)
                    if self.path:
                        self.current_action = "walking"
                    else:
                        self.current_action = "fighting"  # Nie można dojść, ale wciąż w walce
                return

                # Logika poza walką (np. gracz umarł) lub gdy cel walki zniknął
        if not player.is_alive:
            if self.is_chasing or self.in_combat: self.leave_combat()
            self.is_chasing = False;
            if not self.path and (self.ix != self.start_ix or self.iy != self.start_iy):
                self.path = bresenham(self.ix, self.iy, self.start_ix, self.start_iy)
            self.current_action = "idle" if not self.path else "walking"
            return

        distance_to_player = max(abs(self.ix - player.ix), abs(self.iy - player.iy))

        # Rozpoczęcie ścigania i walki, jeśli gracz wszedł w zasięg aggro
        if not self.in_combat and distance_to_player <= self.aggro_radius and player.is_alive:
            print(f"[DEBUG] HostileNPC {self.name} spots {player.name} and enters combat (AI)!")
            self.enter_combat_with(player)
            if distance_to_player > 1:
                self.path = bresenham(self.ix, self.iy, player.ix, player.iy)
                if self.path:
                    self.current_action = "walking"
                else:
                    self.current_action = "fighting"
            return

            # Utrata celu pościgu, jeśli gracz za daleko (tylko jeśli is_chasing)
        elif self.is_chasing and distance_to_player > self.aggro_radius * 2:
            print(f"[DEBUG] HostileNPC {self.name}: Player {player.name} escaped chase.")
            if self.in_combat and self.combat_target == player: self.leave_combat()
            self.is_chasing = False
            if not self.path and (self.ix != self.start_ix or self.iy != self.start_iy):
                self.path = bresenham(self.ix, self.iy, self.start_ix, self.start_iy)
            self.current_action = "idle" if not self.path else "walking"

        # Powrót na pozycję startową, jeśli nie ściga, nie walczy i nie jest na miejscu
        if not self.in_combat and not self.is_chasing and self.movement_pattern == "stationary" and \
                (self.ix != self.start_ix or self.iy != self.start_iy) and not self.path:
            self.path = bresenham(self.ix, self.iy, self.start_ix, self.start_iy)
            if self.path:
                self.current_action = "walking"
            else:
                self.current_action = "idle"