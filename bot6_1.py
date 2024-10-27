"""This is an example of a bot participating in the HackArena 2.0.

This bot will randomly move around the map,
use abilities and print the map to the console.
"""

import os
import random
from typing import Optional, Tuple, List, Dict
from collections import defaultdict
from hackathon_bot import *
from dataclasses import dataclass
from copy import deepcopy
import math

def get_poses_for_zone(zone: Zone) -> list[tuple[int,int]]:
    return [Pos(x+zone.x,y+zone.y) for x in range(zone.width) for y in range(zone.height)]


PIERDOLNIK = True

@dataclass(frozen=True)
class Pos():
    x: int
    y: int
    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y


@dataclass
class EnemyData:
    turret: Direction
    tank: Direction
    position: Pos
    visible: bool


@dataclass
class BulletData:
    bullet: Bullet
    position: Pos


@dataclass(frozen=True)
class ItemData:
    type: ItemType
    tick: int


global last_move
last_move: ResponseAction = None


opposite_dirs = {
    Direction.DOWN: Direction.UP,
    Direction.UP: Direction.DOWN,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT
}


def taxicab(p1:Pos, p2:Pos):
    return abs(p1.x-p2.x)+abs(p1.y-p2.y)

def adjacent(tiles: tuple[tuple[Tile]], pos: Pos, visited: dict[Pos, Pos]) -> tuple[Pos]:
    """Get adjacent tiles that aren't visited and arent a wall. Returns `Pos`!!!"""
    cross = (Pos(pos.x+1,pos.y),Pos(pos.x-1,pos.y),Pos(pos.x,pos.y+1),Pos(pos.x,pos.y-1))
    cross = (p for p in cross if p not in visited)
    cross = (p for p in cross if p.x>=0 and p.x<len(tiles[0]) and p.y>=0 and p.y<len(tiles))
    cross_tiles = ((p,tiles[p.y][p.x]) for p in cross) # tuple of (pos,tile) because tile is dumb
    adj = [x[0] for x in cross_tiles if not any(isinstance(y, Wall) or isinstance(y, Mine) or isinstance(y,Laser) for y in x[1].entities)]
    return adj

def heur_select_next(stack:list[Pos]):
    return 0


def bfs(map: Map, start: Pos, stop_criterion: callable) -> Optional[list[Pos]]:
    """Returns shortest path to a tile that matches criterion

    Args:
        map (Map): map
        start (Pos): root of the search tree
        stop_criterion (callable): function that evaluates whether the tile is what we are looking for

    Returns:
        Optional[list[Pos]]: Either list of positions to take, empty list (if at destination) or None, if impossible
    """
    cur = None
    stack = [start]
    parents = {start: None}
    while True:
        try:
            cur = stack.pop(heur_select_next(stack))
        except IndexError:
            return None
        if stop_criterion(cur):
            path = [cur]
            while True:
                parent = parents[cur]
                if parent==None:
                    return path[:-1] # without current position
                path.append(parent)
                cur = parent
        adj = adjacent(map.tiles,cur, parents)
        for x in adj:
            parents[x]=cur
        stack.extend(adj)


def get_move(direction) -> Tuple[int, int]:
    if direction == Direction.RIGHT:
        return 0, 1
    if direction == Direction.LEFT:
        return 0, -1
    if direction == Direction.UP:
        return 1, -1
    if direction == Direction.DOWN:
        return 1, 1


overwrite = None


class ExampleBot(HackathonBot):

    def __init__(self):
        super().__init__()
        self.my_pos: Pos = None
        self.my_tank: AgentTank = None
        self.enemies: Dict[str, EnemyData] = defaultdict()
        self.bullets: Dict[str, BulletData] = defaultdict()
        self.last_action: str = None # "final" in tick
        self.subtick_action: str = None # just a place to store it during a tick
        self.fight_started: bool = False
        self.current_zone_fight: Zone = None
        self.knownItems: dict[Pos|ItemData] = {}
        self.init = False
        self.mines: List[Pos] = []
        self.dimension = None
        self.visibility_cache = defaultdict()
        self.wall_map: List[List[bool]] = []
        self.last_pos: Pos = None
        
        #zone fighter
        self.last_corner: Pos = None

    def action(func):
        def inner(*args, **kwargs):
            args[0].subtick_action=func.__name__
            return func(*args, **kwargs)
        return inner
    
    def get_next_corner(self, game_state: GameState, corner: Pos) -> Pos:
        """This is to find enemy at our zone."""
        zone_root = Pos(self.current_zone_fight.x, self.current_zone_fight.y)
        if corner==zone_root:
            return Pos(corner.x+self.current_zone_fight.width-1,corner.y+self.current_zone_fight.height-1)
        else:
            return zone_root
    
    def find_stuff(self, game_state: GameState):
        self.enemies = defaultdict()

        for y,row in enumerate(game_state.map.tiles):
            for x,tile in enumerate(row):
                for ent in tile.entities:
                    if isinstance(ent, PlayerTank):
                        if ent.owner_id==game_state.my_agent.id:
                            self.my_pos=Pos(x,y)
                            self.my_tank = ent
                        else:
                            self.enemies[ent.owner_id] = EnemyData(ent.turret.direction, ent.direction, Pos(x, y), True)
                    elif isinstance(ent, Bullet):
                        self.bullets[ent.id] = BulletData(ent, Pos(x, y))
                    elif isinstance(ent, Mine):
                        self.mines.append(Pos(x, y))
                    # elif isinstance(ent, Item):
                    #    self.knownItems[Pos(x, y)] = ItemData(ent.type, game_state.tick)

    def calculate(self):
        rotations = [Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT]

        for tank_rot in rotations:
            for tur_rot in rotations:
                for x in range(self.dimension):
                    for y in range(self.dimension):
                        if not self.wall_map[y][x]:
                            key = (tank_rot, tur_rot, x, y)
                            self.visibility_cache[key] = self.fog_of_war_manager.calculate_visibility_grid(Pos(x, y), tank_rot, tur_rot)

    def get_cached_result(self, tank_rot, tur_rot, x, y):
        key = (tank_rot, tur_rot, x, y)
        return self.visibility_cache.get(key, None)

    def predict_bullets(self):
        destoyed_bullets = []
        next_bullets = deepcopy(self.bullets)

        for id, bullet in next_bullets.items():
            index, direction = get_move(bullet.bullet.direction)
            for _ in range(2):  # bullet.bullet.speed
                x, y = next_bullets[id].position[0], next_bullets[id].position[1]
                next_bullets[id].position = Pos(x + direction if index == 0 else x, y + direction if index == 1 else y)
                if x<0 or x>= self.dimension-1 or y<0 or y>= self.dimension-1 or self.wall_map[y][x]: # czyli jest w ścianie #TODO dodać że także czołg może
                    destoyed_bullets.append(id)
        
        for bullet_id in destoyed_bullets:
            next_bullets.pop(bullet_id, None)

        return next_bullets
    
    def update_bullets(self):
        self.bullets = self.predict_bullets()

    # for themself self.get_dodge_actions(self.my_pos, self.my_tank.direction)
    def get_dodge_action(self, obj_pos, obj_rot) -> Movement | Rotation | int:
        for bullet in self.bullets.values():
            # check if bullet is going towards tank
            if bullet.position[0] == obj_pos[0] and \
                ((bullet.bullet.direction == Direction.RIGHT and bullet.position[1] < obj_pos[1]) or
                (bullet.bullet.direction == Direction.LEFT and bullet.position[1] > obj_pos[1])):
                    if obj_rot in [Direction.DOWN, Direction.UP]:  # check if bullet and tank directions crosses
                        # check if up or down is not a wall

                        up_move = Pos(obj_pos[0], obj_pos[1] - 1)
                        if not self.wall_map[up_move.y][up_move.x]:
                            return Movement(MovementDirection.FORWARD if obj_rot == Direction.UP else MovementDirection.BACKWARD)

                        down_move = Pos(obj_pos[0], obj_pos[1] + 1)
                        if not self.wall_map[down_move.y][down_move.x]:
                            return Movement(MovementDirection.BACKWARD if obj_rot == Direction.UP else MovementDirection.FORWARD)
                    elif (distance := abs(bullet.position[1] - obj_pos[1])) > 2:  # have time to execute 2 actions
                        up_move = Pos(obj_pos[0], obj_pos[1] - 1)
                        if not self.wall_map[up_move.y][up_move.x]:
                            if distance <= 7:
                                return Rotation(RotationDirection.RIGHT if obj_rot == Direction.LEFT else RotationDirection.LEFT, None)
                            return distance

                        down_move = Pos(obj_pos[0], obj_pos[1] + 1)
                        if not self.wall_map[down_move.y][down_move.x]:
                            if distance <= 7:
                                return Rotation(RotationDirection.LEFT if obj_rot == Direction.LEFT else RotationDirection.RIGHT, None)
                            return distance
                    else:
                        if self.my_tank.turret.direction % 2 == bullet.bullet.direction % 2 and \
                            self.my_tank.turret.direction != bullet.bullet.direction and \
                                self.my_tank.turret.bullet_count != 0:
                            return AbilityUse(Ability.FIRE_DOUBLE_BULLET if self.my_tank.secondary_item == ItemType.DOUBLE_BULLET else Ability.FIRE_BULLET)
                        return 0  # unable to dodge
            if bullet.position[1] == obj_pos[1] and \
                ((bullet.bullet.direction == Direction.UP and bullet.position[0] > obj_pos[0]) or
                (bullet.bullet.direction == Direction.DOWN and bullet.position[0] < obj_pos[0])):
                    if obj_rot in [Direction.LEFT, Direction.RIGHT]:  # check if bullet and tank directions crosses
                        # check if up or down is not a wall

                        right_move = Pos(obj_pos[0] + 1, obj_pos[1])
                        if not self.wall_map[right_move.y][right_move.x]:
                            return Movement(MovementDirection.FORWARD if obj_rot == Direction.RIGHT else MovementDirection.BACKWARD)

                        left_move = Pos(obj_pos[0] - 1, obj_pos[1])
                        if not self.wall_map[left_move.y][left_move.x]:
                            return Movement(MovementDirection.BACKWARD if obj_rot == Direction.RIGHT else MovementDirection.FORWARD)
                    elif (distance := abs(bullet.position[0] - obj_pos[0])) > 2:  # have time to execute 2 actions

                        right_move = Pos(obj_pos[0] + 1, obj_pos[1])
                        if not self.wall_map[right_move.y][right_move.x]:
                            if distance <= 7:
                                return Rotation(RotationDirection.RIGHT if obj_rot == Direction.UP else RotationDirection.LEFT, None)
                            return distance

                        left_move = Pos(obj_pos[0] - 1, obj_pos[1])
                        if not self.wall_map[left_move.y][left_move.x]:
                            if distance <= 7:
                                return Rotation(RotationDirection.LEFT if obj_rot == Direction.UP else RotationDirection.RIGHT, None)
                            return distance
                    else:
                        if self.my_tank.turret.direction % 2 == bullet.bullet.direction % 2 and \
                            self.my_tank.turret.direction != bullet.bullet.direction and \
                                self.my_tank.turret.bullet_count != 0:
                            return AbilityUse(Ability.FIRE_DOUBLE_BULLET if self.my_tank.secondary_item == ItemType.DOUBLE_BULLET else Ability.FIRE_BULLET)
                        return 0  # unable to dodge

    def analize_map(self, map: Map):
        self.wall_map = [[False for _ in range(self.dimension)] for _ in range(self.dimension)]
        for y, line in enumerate(map.tiles):
            for x, tile in enumerate(line):
                for entity in tile.entities:
                    if isinstance(entity, Wall):
                        self.wall_map[y][x] = True
        # self.fog_of_war_manager = FogOfWarManager(self.wall_map)
        self.init = True

    def get_tiles_probably_visible(self, pos: Pos, direction: Direction, turretDirection: Direction) -> list[Pos]:
        tiles_to_see = []
        if turretDirection != direction:
            if turretDirection == Direction.UP:
                y = pos.y - 1
                while y >= 0:
                    if self.wall_map[y][pos.x]:
                        break
                    tiles_to_see.append(Pos(pos.x, y))
                    y -= 1
            elif turretDirection == Direction.RIGHT:
                x = pos.x + 1
                while x < self.dimension:
                    if self.wall_map[pos.y][x]:
                        break
                    tiles_to_see.append(Pos(x, pos.y))
                    x += 1
            elif turretDirection == Direction.DOWN:
                y = pos.y + 1
                while y < self.dimension:
                    if self.wall_map[y][pos.x]:
                        break
                    tiles_to_see.append(Pos(pos.x, y))
                    y += 1
            elif turretDirection == Direction.LEFT:
                x = pos.x - 1
                while x >= 0:
                    if self.wall_map[pos.y][x]:
                        break
                    tiles_to_see.append(Pos(x, pos.y))
                    x -= 1
        a = math.tan(math.pi/10)
        if direction == Direction.UP:
            for x in range(self.dimension):
                if x == pos.x:
                    a = -a
                y = int(round((x - pos.x) * a + pos.y, 0))
                while y >= 0:
                    if not self.wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y -= 1
        elif direction == Direction.DOWN:
            for x in range(self.dimension):
                if x == pos.x:
                    a = -a
                y = int(round((pos.x - x) * a + pos.y, 0))
                while y < self.dimension:
                    if not self.wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y += 1
        elif direction == Direction.RIGHT:
            for y in range(self.dimension):
                if y == pos.y:
                    a = -a
                x = int(round(pos.x + a*(pos.y - y), 0))
                while x < self.dimension:
                    if not self.wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x += 1
        elif direction == Direction.LEFT:
            for y in range(self.dimension):
                if y == pos.y:
                    a = -a
                x = int(round(pos.x + a*(y - pos.y), 0))
                while x >= 0:
                    if not self.wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x -= 1
        return tiles_to_see

    def get_tiles_to_see(self) -> list[Pos]: # old one
        return self.get_tiles_probably_visible(self.my_pos, self.my_tank.direction, self.my_tank.turret.direction)
# --- common action parts

    def move_towards(self, target:Pos, turret: bool):
        """Moves tank towards target, or rotates it to make it possible in future.
        
        If turret==true, rotate turret instead.

        Args:
            target (Pos): _description_
            turret (bool): _description_

        Returns:
            _type_: _description_
        """
        deltax = target.x-self.my_pos.x
        deltay = target.y-self.my_pos.y

        # !!! Prioritize shorter axis, so that we enter the line of sight immediately.
        if abs(deltax)<abs(deltay):
            deltax=0
        else:
            deltay=0

        checked_dir = self.my_tank.turret.direction if turret else self.my_tank.direction 

        wishdir: Direction=Direction.UP
        if deltax>0:
            wishdir=Direction.RIGHT
        elif deltax<0:
            wishdir=Direction.LEFT
        elif deltay>0:
            wishdir=Direction.DOWN
        elif deltay<0:
            wishdir=Direction.UP

        if turret:
            if wishdir==checked_dir:
                return Pass()
            elif wishdir==opposite_dirs[checked_dir]:
                return Rotation(None, RotationDirection.LEFT) # arbitrary
        else:
            if wishdir==checked_dir:
                return Movement(MovementDirection.FORWARD)
            elif wishdir==opposite_dirs[checked_dir]:
                return Movement(MovementDirection.BACKWARD)
        if wishdir==Direction.UP and checked_dir==Direction.RIGHT or \
            wishdir==Direction.RIGHT and checked_dir==Direction.DOWN or \
            wishdir==Direction.DOWN and checked_dir==Direction.LEFT or \
            wishdir==Direction.LEFT and checked_dir==Direction.UP:
            if turret:
                return Rotation(None, RotationDirection.LEFT)
            else:
                return Rotation(RotationDirection.LEFT, None)
        elif wishdir==Direction.DOWN and checked_dir==Direction.RIGHT or \
            wishdir==Direction.LEFT and checked_dir==Direction.DOWN or \
            wishdir==Direction.UP and checked_dir==Direction.LEFT or \
            wishdir==Direction.RIGHT and checked_dir==Direction.UP:
            if turret:
                return Rotation(None, RotationDirection.RIGHT)
            else:
                return Rotation(RotationDirection.RIGHT, None)
        else:
            raise RuntimeError("This shouldn't be possible")

    def search(self, game_state: GameState, func: callable) -> Optional[ResponseAction]:
        """Searches closest tile matching a criterion.

        Args:
            game_state (GameState): game
            func (callable): function that takes `Pos` and returns True or False

        Returns:
            _type_: Action that advances player towards the goal. If goal can't be reached, returns `None`.
        """
        path = bfs(game_state.map, self.my_pos, func)
        if path is None: # impossible path
            return None
        if not len(path): # at destination
            return Pass()
        next_step = path[-1]

        if next_step in [enemy.position for enemy in self.enemies.values()]:
            return self.shoot_tile(game_state, next_step)

        return self.move_towards(next_step, turret=False)

    def place_mine(self):
        x, y = self.my_pos.x, self.my_pos.y
        match self.my_tank.direction:
            case Direction.UP:
                self.mines.append(Pos(x, y+1))
            case Direction.RIGHT:
                self.mines.append(Pos(x-1, y))
            case Direction.DOWN:
                self.mines.append(Pos(x, y-1))
            case Direction.LEFT:
                self.mines.append(Pos(x+1, y))

        return AbilityUse(Ability.DROP_MINE)

    def laser_kill(self) -> bool:
        if self.my_tank.secondary_item != ItemType.LASER:
            return False
        for enemy in self.enemies.values():
            if enemy.visible:
                if enemy.position[0] == self.my_pos[0] and \
                   enemy.tank in [Direction.LEFT, Direction.RIGHT] and \
                   ((self.my_tank.turret == Direction.RIGHT and enemy.position[1] > self.my_pos[1]) or
                   (self.my_tank.turret == Direction.LEFT and enemy.position[1] < self.my_pos[1])):
                    return True
                if enemy.position[1] == self.my_pos[1] and \
                   enemy.tank in [Direction.UP, Direction.DOWN] and \
                   ((self.my_tank.turret == Direction.UP and enemy.position[0] < self.my_pos[0]) or
                   (self.my_tank.turret == Direction.DOWN and enemy.position[0] > self.my_pos[0])):
                    return True
        return False
        
#---- actions

    @action
    def rush_zones(self, game_state: GameState):
        global overwrite
        def bullet_or_target_zone(pos: Pos):
            global overwrite
            tile = game_state.map.tiles[pos.y][pos.x]
            if self.my_tank.secondary_item!=ItemType.LASER:
                # if we don't have laser
                for ent in tile.entities:
                    if isinstance(ent, Item) and ent.type==ItemType.LASER:
                        if taxicab(pos, self.my_pos)<5:
                            # if laser is close, get rid of anything, and confirm target
                            match self.my_tank.secondary_item:
                                # get rid of anything
                                case SecondaryItemType.DOUBLE_BULLET:
                                    overwrite = AbilityUse(Ability.FIRE_DOUBLE_BULLET)
                                case SecondaryItemType.MINE:
                                    overwrite = AbilityUse(Ability.DROP_MINE)
                                case SecondaryItemType.RADAR:
                                    overwrite = AbilityUse(Ability.USE_RADAR)
                            return True
                
            elif not self.my_tank.secondary_item:
                for ent in tile.entities:
                    if isinstance(ent, Item) and ent.type==ItemType.DOUBLE_BULLET:
                        if taxicab(pos, self.my_pos)<2:
                            return True
            if tile.zone and not (isinstance(tile.zone, CapturedZone) and tile.zone.player_id==self.my_tank.owner_id):
                return True
            return False
        
        next_move = self.search(game_state, bullet_or_target_zone)
        return overwrite if overwrite else next_move
    
    @action
    def go_to(self, game_state: GameState, target: Pos):
        def is_target(pos: Pos):
            return target==pos
        
        if isinstance(self.last_action,Movement) and self.my_pos==self.last_pos:
            # unbug
            return Rotation(RotationDirection.LEFT, RotationDirection.LEFT)
        return self.search(game_state, is_target)
    

    @action
    def go_to_direct_line(self, game_state: GameState, target: Pos):
        def is_direct_to(pos: Pos):
            x_axis = pos.x==target.x
            y_axis = pos.y==target.y
            if x_axis:
                # look if everything between player and target is free
                if pos.y<target.y:
                    r = range(pos.y+1,target.y)
                else:
                    r = range(target.y+1,pos.y)
                for yi in r:
                    if any(isinstance(ent,Wall) for ent in game_state.map.tiles[yi][pos.x].entities):
                        return False
                return True
            elif y_axis:
                if pos.x<target.x:
                    r = range(pos.x+1,target.x)
                else:
                    r = range(target.x+1, pos.x)
                for xi in r:
                    if any(isinstance(ent,Wall) for ent in game_state.map.tiles[pos.y][xi].entities):
                        return False
                return True
            return False
        
        return self.search(game_state, is_direct_to)
    
    @action
    def shoot_tile(self, game_state: GameState, enemy: Pos):
        # find where I need to stand to shoot

        rotation = self.move_towards(enemy, turret=True) # this is bad name, but it's goal is to rotate the turret, not move
        
        if not isinstance(rotation,Pass):
            return rotation

        # We are angled properly

        next_move = self.go_to_direct_line(game_state, enemy)
        if isinstance(next_move, Pass):
            if self.my_tank.secondary_item==SecondaryItemType.LASER:
                next_move = AbilityUse(Ability.USE_LASER)
            elif self.my_tank.secondary_item==SecondaryItemType.DOUBLE_BULLET:
                next_move = AbilityUse(Ability.FIRE_DOUBLE_BULLET)
            else:
                if self.my_tank.turret.bullet_count:
                    next_move = AbilityUse(Ability.FIRE_BULLET)
                else:
                    if PIERDOLNIK and self.my_tank.turret.ticks_to_regenerate_bullet>1: #intentional
                        if self.my_tank.direction==self.my_tank.turret.direction:
                            # move sideways
                            return Rotation(RotationDirection.LEFT,None)
                        else:
                            match self.my_tank.direction:
                                # opposite
                                case Direction.UP:
                                    p = (0,1)
                                case Direction.DOWN:
                                    p = (0,-1)
                                case Direction.RIGHT:
                                    p = (-1,0)
                                case Direction.LEFT:
                                    p = (1,0)
                            if any(isinstance(x,Wall) for x in game_state.map.tiles[self.my_pos.y+p[1]][self.my_pos.x+p[0]].entities):
                                return Movement(MovementDirection.FORWARD)
                            else:
                                return Movement(MovementDirection.BACKWARD)

        return next_move

    @action
    def zone_fighter(self, game_state: GameState):
        if len(self.enemies):
            # we dont differentiate between enemies, if there are more then oh well
            next_pos = self.shoot_tile(game_state, self.get_nearest_enemy([enemy.position for enemy in self.enemies.values()],self.my_pos))
        else:
            next_pos = self.go_to(game_state, self.next_corner)
            if not next_pos or isinstance(next_pos,Pass): # at the corner
                self.next_corner = self.get_next_corner(game_state, self.next_corner)
                next_pos = self.go_to(game_state, self.next_corner)
        return next_pos

    def is_corridor_behind(self, game_state: GameState):
        if self.my_tank.direction==Direction.UP:
            check = [Pos(self.my_pos.x-1,self.my_pos.y+1),Pos(self.my_pos.x+1,self.my_pos.y+1)]
        elif self.my_tank.direction==Direction.DOWN:
            check = [Pos(self.my_pos.x-1,self.my_pos.y-1),Pos(self.my_pos.x+1,self.my_pos.y-1)]
        elif self.my_tank.direction==Direction.LEFT:
            check = [Pos(self.my_pos.x+1,self.my_pos.y-1),Pos(self.my_pos.x+1,self.my_pos.y+1)]
        else:
            check = [Pos(self.my_pos.x-1,self.my_pos.y-1),Pos(self.my_pos.x-1,self.my_pos.y+1)]
        
        #@TODO: replace with fast wall check
        for tile in check:
            if all(isinstance(x,Wall) for x in game_state.map.tiles[tile.y][tile.x].entities):
                return True
        return False
# --- actions end

    def get_good_visibility_spot(self) -> Pos:
        x_, y_ = self.dimension//2, self.dimension//2
        spots = []
        for y in range(-5, 6):
            for x in range(-5, 6):
                if not self.wall_map[y_+y][x_+x]:
                    spots.append(Pos(x_+x, y_+y))
        return random.choice(spots)

    def get_nearest_enemy(self, enemies: list[Pos], pos: Pos):
        closest = None
        min_dist = 999
        for x in enemies:
            if taxicab(x,pos)<min_dist:
                min_dist=taxicab(x,pos)
                closest = x
        return closest

    def decide_action(self, game_state: GameState):
        next_move = None
        if self.my_tank.secondary_item==SecondaryItemType.RADAR:
            next_move=AbilityUse(Ability.USE_RADAR)
        elif self.my_tank.secondary_item==SecondaryItemType.MINE:
            if self.is_corridor_behind(game_state):
                next_move=AbilityUse(Ability.DROP_MINE)
        if not next_move and self.fight_started:
            next_move = self.zone_fighter(game_state)
            zone = game_state.map.tiles[self.my_pos.y][self.my_pos.x].zone
            if zone and zone.status!=ZoneStatus.BEING_CONTESTED:
                self.fight_started=False
        elif not next_move:
            next_move = self.rush_zones(game_state)
            if isinstance(next_move, Pass):
                # if we arrived, check if this is a fight
                zone = game_state.map.tiles[self.my_pos.y][self.my_pos.x].zone
                if not zone:
                    # we are at item and for some reason we can't pick it up
                    return Pass()
                if zone.status==ZoneStatus.BEING_CONTESTED:
                    if not self.fight_started:
                        self.fight_started=True
                        self.current_zone_fight=zone
                        self.next_corner=Pos(zone.x,zone.y)
                    next_move = self.zone_fighter(game_state)
                else:
                    # capturing, spin instead of standing
                    if len(self.enemies)==0:
                        next_move=Rotation(RotationDirection.LEFT,RotationDirection.RIGHT)
                    else:
                        next_move = self.shoot_tile(game_state, self.get_nearest_enemy([enemy.position for enemy in self.enemies.values()],self.my_pos))


            if next_move is None: # can't do that for some reason (no zones!)
                guard_spot = self.get_good_visibility_spot()
                next_move=self.go_to(game_state, guard_spot)

        
        self.last_action=self.subtick_action
        return next_move



    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        print(f"Lobby data received: {lobby_data}")
        self.dimension = lobby_data.server_settings.grid_dimension

    def next_move(self, game_state: GameState) -> ResponseAction:
        if not self.init:
            self.analize_map(game_state.map)
        if game_state.my_agent.is_dead:
            self.fight_started=False
            self.current_zone_fight=None
            # Return pass to avoid warnings from the server
            # when the bot tries to make an action with a dead tank
            return Pass()
        self.find_stuff(game_state)
        self.update_bullets()
        next_action = self.get_dodge_action(self.my_pos, self.my_tank.direction)
        if not isinstance(next_action, ResponseAction):
            next_action = self.decide_action(game_state)
        self.last_action = next_action
        self.last_pos = self.my_pos
        return next_action

    def on_game_ended(self, game_result: GameResult) -> None:
        print(f"Game ended: {game_result}")

    def on_warning_received(self, warning: WarningType, message: str | None) -> None:
        print(f"Warning received: {warning} - {message}")


if __name__ == "__main__":
    bot = ExampleBot()
    bot.run()