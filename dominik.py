from hackathon_bot import *
from dataclasses import dataclass
import math


@dataclass
class Pos:
    x: int
    y: int


@dataclass
class ItemData:
    type: ItemType
    tick: int


class MyBot(HackathonBot):
    def __init__(self) -> None:
        super().__init__()
        self.pos = None
        self.wallmap: list[list[int]] = []
        self.init: bool = False
        self.direction: Direction = None
        self.turretDirection: Direction = None
        self.dimension = None
        self.knownItems: dict[Pos|ItemData] = {}

    def analize_map(self, map: Map):
        self.wallmap = [[False for _ in range(self.dimension)] for _ in range(self.dimension)]
        for y, line in enumerate(map.tiles):
            for x, tile in enumerate(line):
                for entity in tile.entities:
                    if isinstance(entity, AgentTank):
                        self.pos = Pos(x, y)
                        self.direction = entity.direction
                        self.turretDirection =  entity.turret.direction
                    elif isinstance(entity, Wall):
                        self.wallmap[y][x] = True
        self.init = True

    def get_tiles_probably_visible(self, pos: Pos, direction: Direction, turretDirection: Direction) -> list[Pos]:
        tiles_to_see = []
        if turretDirection != direction:
            if turretDirection == Direction.UP:
                y = pos.y - 1
                while y >= 0:
                    if self.wallmap[y][pos.x]:
                        break
                    tiles_to_see.append(Pos(pos.x, y))
                    y -= 1
            elif turretDirection == Direction.RIGHT:
                x = pos.x + 1
                while x < self.dimension:
                    if self.wallmap[pos.y][x]:
                        break
                    tiles_to_see.append(Pos(x, pos.y))
                    x += 1
            elif turretDirection == Direction.DOWN:
                y = pos.y + 1
                while y < self.dimension:
                    if self.wallmap[y][self.pos.x]:
                        break
                    tiles_to_see.append(Pos(self.pos.x, y))
                    y += 1
            elif turretDirection == Direction.LEFT:
                x = pos.x - 1
                while x >= 0:
                    if self.wallmap[pos.y][x]:
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
                    if not self.wallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y -= 1
        elif direction == Direction.DOWN:
            for x in range(self.dimension):
                if x == pos.x:
                    a = -a
                y = int(round((pos.x - x) * a + pos.y, 0))
                while y < self.dimension:
                    if not self.wallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y += 1
        elif direction == Direction.RIGHT:
            for y in range(self.dimension):
                if y == pos.y:
                    a = -a
                x = int(round(pos.x + a*(pos.y - y), 0))
                while x < self.dimension:
                    if not self.wallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x += 1
        elif direction == Direction.LEFT:
            for y in range(self.dimension):
                if y == pos.y:
                    a = -a
                x = int(round(pos.x + a*(y - pos.y), 0))
                while x >= 0:
                    if not self.wallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x -= 1
        return tiles_to_see

    def get_tiles_to_see(self) -> list[Pos]: # old one
        return self.get_tiles_probably_visible(self.pos, self.direction, self.turretDirection)

    def update_diretion(self, tile: Tile):
        for entity in tile.entities:
            if isinstance(entity, AgentTank):
                self.direction = entity.direction
                self.turretDirection = entity.turret.direction
                break

    def update_items_list(self, tiles: list[list[Tile]], visible_tiles: list[Pos], tick: int):
        for pos in visible_tiles:
            tile = tiles[pos.y][pos.x]
            for entity in tile.entities:
                if isinstance(entity, Item):
                    self.knownItems[pos] = ItemData(entity.type, tick)
        for pos, item in self.knownItems.items():
            item: ItemData
            if tick - item.tick > 100:
                self.knownItems.pop(pos)
                    

    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        self.dimension = lobby_data.server_settings.grid_dimension
        pass

    def next_move(self, game_state: GameState) -> ResponseAction:
        if not self.init:
            self.analize_map(game_state.map)
        self.update_diretion(game_state.map.tiles[self.pos.y][self.pos.x])
        self.update_items_list(game_state.map.tiles, self.get_tiles_to_see(), game_state.tick)
        if game_state.tick % 10 == 0:
            tiles_to_see = self.get_tiles_to_see()
            print([(pos.x, pos.y) for pos in tiles_to_see])
            return Rotation(None, RotationDirection.RIGHT)

    def on_game_ended(self, game_result: GameResult) -> None:
        pass

    def on_warning_received(self, warning: WarningType, message: str | None) -> None:
        pass


if __name__ == "__main__":
    bot = MyBot()
    bot.run()
