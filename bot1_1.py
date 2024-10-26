"""This is an example of a bot participating in the HackArena 2.0.

This bot will randomly move around the map,
use abilities and print the map to the console.
"""

import os
from pprint import pprint
import random

from hackathon_bot import *
from dataclasses import dataclass
from typing import List, Tuple, Dict
from collections import defaultdict
from copy import deepcopy
import math

def get_poses_for_zone(zone: Zone) -> list[tuple[int,int]]:
    return [Pos(x+zone.x,y+zone.y) for x in range(zone.width) for y in range(zone.height)]

@dataclass(unsafe_hash=True, frozen=False)
class Pos():
    x: int
    y: int 
    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y



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
    adj = [x[0] for x in cross_tiles if not any(isinstance(y, Wall) for y in x[1].entities)]
    return adj

def heur_select_next(stack:list[Pos]):
    return 0

def bfs(map: Map, start: Pos, target: Pos) -> list[Pos]:
    prev = None
    cur = None
    stack = [start]
    parents = {start: None}
    while True:
        cur = stack.pop(heur_select_next(stack))
        if cur==target:
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


@dataclass
class EnemyData:
    turret: Direction
    tank: Direction
    position: Tuple[int, int]
    visible: bool


@dataclass
class BulletData:
    bullet: Bullet
    position: Pos


def get_move(direction) -> Tuple[int, int]:
    if direction == Direction.RIGHT:
        return 0, 1
    if direction == Direction.LEFT:
        return 0, -1
    if direction == Direction.UP:
        return 1, -1
    if direction == Direction.DOWN:
        return 1, 1


class ExampleBot(HackathonBot):

    def __init__(self):
        super().__init__()
        self.my_pos: Pos = None
        self.my_tank: AgentTank = None
        self.enemies: Dict[str, EnemyData] = defaultdict()
        self.bullets: Dict[str, BulletData] = defaultdict()
        self.not_wall_map: List[Pos] = []
        self.init: bool = False
        self.dimension = None

    def find_me(self, game_state: GameState) -> tuple[Pos, AgentTank]:
        for y,row in enumerate(game_state.map.tiles):
            for x,tile in enumerate(row):
                if any(isinstance(z, AgentTank) for z in tile.entities):
                    for ent in tile.entities:
                        if isinstance(ent, AgentTank):
                            return Pos(x,y),ent 
                        
    def analize_map(self, map: Map):
        self.not_wall_map = [[False for _ in range(self.dimension)] for _ in range(self.dimension)]
        for y, line in enumerate(map.tiles):
            for x, tile in enumerate(line):
                for entity in tile.entities:
                    if isinstance(entity, Wall):
                        self.not_wall_map[y][x] = True
        self.init = True

    def get_tiles_to_see(self) -> List[Pos]:
        tiles_to_see = []
        if self.my_tank.turret.direction != self.my_tank.direction:
            if self.my_tank.turret.direction == Direction.UP:
                y = self.my_pos.y - 1
                while y >= 0:
                    if self.not_wall_map[y][self.my_pos.x]:
                        break
                    tiles_to_see.append(Pos(self.my_pos.x, y))
                    y -= 1
            elif self.my_tank.turret.direction == Direction.RIGHT:
                x = self.my_pos.x + 1
                while x < self.dimension:
                    if self.not_wall_map[self.my_pos.y][x]:
                        break
                    tiles_to_see.append(Pos(x, self.my_pos.y))
                    x += 1
            elif self.my_tank.turret.direction == Direction.DOWN:
                y = self.my_pos.y + 1
                while y < self.dimension:
                    if self.not_wall_map[y][self.my_pos.x]:
                        break
                    tiles_to_see.append(Pos(self.my_pos.x, y))
                    y += 1
            elif self.my_tank.turret.direction == Direction.LEFT:
                x = self.my_pos.x - 1
                while x >= 0:
                    if self.not_wall_map[self.my_pos.y][x]:
                        break
                    tiles_to_see.append(Pos(x, self.my_pos.y))
                    x -= 1
        a = math.tan(math.pi/10)
        if self.my_tank.direction == Direction.UP:
            for x in range(self.dimension):
                if x == self.my_pos.x:
                    a = -a
                y = int(round((x - self.my_pos.x) * a + self.my_pos.y, 0))
                while y >= 0:
                    if not self.not_wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y -= 1
        elif self.my_tank.direction == Direction.DOWN:
            for x in range(self.dimension):
                if x == self.my_pos.x:
                    a = -a
                y = int(round((self.my_pos.x - x) * a + self.my_pos.y, 0))
                while y < self.dimension:
                    if not self.not_wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y += 1
        elif self.my_tank.direction == Direction.RIGHT:
            for y in range(self.dimension):
                if y == self.my_pos.y:
                    a = -a
                x = int(round(self.my_pos.x + a*(self.my_pos.y - y), 0))
                while x < self.dimension:
                    if not self.not_wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x += 1
        elif self.my_tank.direction == Direction.LEFT:
            for y in range(self.dimension):
                if y == self.my_pos.y:
                    a = -a
                x = int(round(self.my_pos.x + a*(y - self.my_pos.y), 0))
                while x >= 0:
                    if not self.not_wall_map[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x -= 1
        return tiles_to_see
    
    # TODO get visible positions
    def parse_tiles_positions(self, game_state: GameState, positions: List[Pos] = None):
        map = game_state.map.tiles
        for position in self.get_tiles_to_see():
                x, y = position[0], position[1]
                for entity in map[y][x].entities:
                    if isinstance(entity, PlayerTank) and game_state.my_agent.id != entity.owner_id:
                        self.enemies[entity.owner_id] = EnemyData(entity.turret, entity.direction, (x, y), True) 
                    if isinstance(entity, Bullet):
                        self.bullets[entity.id] = BulletData(entity, Pos(x, y))

    def go_to(self, game_state: GameState, target: Pos):
        path = bfs(game_state.map, self.my_pos, target)
        if not len(path):
            return Pass()
        next_step = path[-1]
        deltax = next_step.x-self.my_pos.x
        deltay = next_step.y-self.my_pos.y

        wishdir: Direction
        if deltax>0:
            wishdir=Direction.RIGHT
        elif deltax<0:
            wishdir=Direction.LEFT
        elif deltay>0:
            wishdir=Direction.DOWN
        elif deltay<0:
            wishdir=Direction.UP

        if wishdir==self.my_tank.direction:
            return Movement(MovementDirection.FORWARD)
        elif wishdir==opposite_dirs[self.my_tank.direction]:
            return Movement(MovementDirection.BACKWARD)
        elif wishdir==Direction.UP and self.my_tank.direction==Direction.RIGHT or \
             wishdir==Direction.RIGHT and self.my_tank.direction==Direction.DOWN or \
             wishdir==Direction.DOWN and self.my_tank.direction==Direction.LEFT or \
             wishdir==Direction.LEFT and self.my_tank.direction==Direction.UP:
            return Rotation(RotationDirection.RIGHT, None)
        elif wishdir==Direction.DOWN and self.my_tank.direction==Direction.RIGHT or \
             wishdir==Direction.LEFT and self.my_tank.direction==Direction.DOWN or \
             wishdir==Direction.UP and self.my_tank.direction==Direction.LEFT or \
             wishdir==Direction.RIGHT and self.my_tank.direction==Direction.UP:
            return Rotation(RotationDirection.LEFT, None)

    def brain(self, game_state: GameState):
        
        closest = None
        zone_dist = 999
        # @ Can make this without looping
        for zone in game_state.map.zones:
            tiles = get_poses_for_zone(zone)
            for tile in tiles:
                d= taxicab(self.my_pos,tile)
                if not closest or zone_dist>d:
                    zone_dist=d
                    closest=tile
        
        return self.go_to(game_state, closest)
    
    def calculate_visible(self) -> List[Pos]: ...  # TODO

    def update_visibility(self, game_state: GameState):
        tiles_to_check = self.calculate_visible()
        self.parse_tiles_positions(game_state, tiles_to_check)

    def find_true_positions(self):
        true_positions = []
        for y, row in enumerate(self.not_wall_map):     
            for x, value in enumerate(row):             
                if value:                              
                    true_positions.append(Pos(x, y))      
        return true_positions

    def predict_bullets(self):
        destoyed_bullets = []
        next_bullets = deepcopy(self.bullets)

        for id, bullet in next_bullets.items():
            index, direction = get_move(bullet.bullet.direction)
            for _ in range(2):  # bullet.bullet.speed
                x, y = next_bullets[id].position[0], next_bullets[id].position[1]
                next_bullets[id].position = Pos(x + direction if index == 0 else x, y + direction if index == 1 else y)       # TODO change assingment: TypeError: 'Pos' object does not support item assignment
                if next_bullets[id].position not in self.find_true_positions():  # czyli jest w ścianie
                    destoyed_bullets.append(id)
        
        for bullet_id in destoyed_bullets:
            next_bullets.pop(bullet_id, None)

        return next_bullets
    
    def update_bullets(self):
        self.bullets = self.predict_bullets()

    def dodge_bullet(self):
        for bullet in self.bullets.values():
            # check if bullet is going towards tank
            if bullet.position[0] == self.my_pos[0] and \
                ((bullet.bullet.direction == Direction.RIGHT and bullet.position[1] < self.my_pos[1]) or
                (bullet.bullet.direction == Direction.LEFT and bullet.position[1] > self.my_pos[1])):
                    return True
            if bullet.position[1] == self.my_pos[1] and \
                ((bullet.bullet.direction == Direction.UP and bullet.position[0] > self.my_pos[0]) or
                (bullet.bullet.direction == Direction.DOWN and bullet.position[0] < self.my_pos[0])):
                    return True
    
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

    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        self.dimension = lobby_data.server_settings.grid_dimension

    def next_move(self, game_state: GameState) -> ResponseAction:
        if not self.init:
            self.analize_map(game_state.map)

        self.my_pos,self.my_tank = self.find_me(game_state)

        if game_state.tick % 10 == 0:
            tiles_to_see = self.get_tiles_to_see()
            print([(pos.x, pos.y) for pos in tiles_to_see])
            return Rotation(None, RotationDirection.RIGHT)

        self.parse_tiles_positions(game_state)
        self.update_bullets()
        if len(self.bullets.values()) != 0:
            pprint(self.bullets)

        # Check if the agent is dead
        if game_state.my_agent.is_dead:
            # Return pass to avoid warnings from the server
            # when the bot tries to make an action with a dead tank
            return Pass()

        return self.brain(game_state)

    def on_game_ended(self, game_result: GameResult) -> None:
        print(f"Game ended: {game_result}")

    def on_warning_received(self, warning: WarningType, message: str | None) -> None:
        print(f"Warning received: {warning} - {message}")


if __name__ == "__main__":
    bot = ExampleBot()
    bot.run()