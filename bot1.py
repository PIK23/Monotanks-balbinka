"""This is an example of a bot participating in the HackArena 2.0.

This bot will randomly move around the map,
use abilities and print the map to the console.
"""

import os
import random

from hackathon_bot import *
from dataclasses import dataclass
from typing import List, Tuple, Dict
from collections import defaultdict

def get_poses_for_zone(zone: Zone) -> list[tuple[int,int]]:
    return [Pos(x+zone.x,y+zone.y) for x in range(zone.width) for y in range(zone.height)]

@dataclass(frozen=True)
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
        self.enemies: Dict[str, EnemyData] = defaultdict
        self.bullets: Dict[str, BulletData] = defaultdict
        self.not_wall_map: List[Pos] = [] # TODO

    def find_me(self, game_state: GameState) -> tuple[Pos,AgentTank]:
        for y,row in enumerate(game_state.map.tiles):
            for x,tile in enumerate(row):
                if any(isinstance(z, AgentTank) for z in tile.entities):
                    for ent in tile.entities:
                        if isinstance(ent, AgentTank):
                            return Pos(x,y),ent 
    
    # TODO get visible positions
    def parse_tiles_positions(self, game_state: GameState, positions: List[Pos]):
        map = game_state.map.tiles
        for x, y in positions:
            for entity in map[x, y]:
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

    def predict_bullets(self):
        destoyed_bullets = []
        for id, bullet in self.bullets.items():
            index, direction = get_move(bullet.bullet.direction)
            for _ in range(bullet.bullet.speed):
                self.bullets[id][index] += direction
                if self.bullets[id].position not in self.not_wall_map:  # czyli jest w ścianie
                    destoyed_bullets.append(id)
        for bullet_id in destoyed_bullets:
            self.bullets.pop(bullet_id)
    
    def laser_kill(self) -> bool:
        if self.bot.item != ItemType.LASER:
            return False
        for enemy in self.enemies.values():
            if enemy.visible:
                if enemy.position[1] == self.bot.position[1] and \
                   enemy.tank in [Direction.LEFT, Direction.RIGHT] and \
                   ((self.bot.turret == Direction.RIGHT and enemy.position[0] > self.bot.position[0]) or
                   (self.bot.turret == Direction.LEFT and enemy.position[0] < self.bot.position[0])):
                    return True
                if enemy.position[0] == self.bot.position[0] and \
                   enemy.tank in [Direction.UP, Direction.DOWN] and \
                   ((self.bot.turret == Direction.UP and enemy.position[0] < self.bot.position[0]) or
                   (self.bot.turret == Direction.DOWN and enemy.position[0] > self.bot.position[0])):
                    return True
        return False

    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        print(f"Lobby data received: {lobby_data}")

    def next_move(self, game_state: GameState) -> ResponseAction:
        self.predict_bullets()

        # Check if the agent is dead
        if game_state.my_agent.is_dead:
            # Return pass to avoid warnings from the server
            # when the bot tries to make an action with a dead tank
            return Pass()

        self.my_pos,self.my_tank = self.find_me(game_state)
        return self.brain(game_state)

    def on_game_ended(self, game_result: GameResult) -> None:
        print(f"Game ended: {game_result}")

    def on_warning_received(self, warning: WarningType, message: str | None) -> None:
        print(f"Warning received: {warning} - {message}")


if __name__ == "__main__":
    bot = ExampleBot()
    bot.run()