from hackathon_bot import *
from dataclasses import dataclass
import math


@dataclass
class Pos:
    x: int
    y: int


class MyBot(HackathonBot):
    def __init__(self) -> None:
        super().__init__()
        self.pos = None
        self.notwallmap: list[list[int]] = []
        self.init: bool = False
        self.direction: Direction = None
        self.turretDirection: Direction = None
        self.dimension = None

    def analize_map(self, map: Map):
        self.notwallmap = [[False for _ in range(self.dimension)] for _ in range(self.dimension)]
        for y, line in enumerate(map.tiles):
            for x, tile in enumerate(line):
                for entity in tile.entities:
                    if isinstance(entity, AgentTank):
                        self.pos = Pos(x, y)
                        self.direction = entity.direction
                        self.turretDirection =  entity.turret.direction
                    elif isinstance(entity, Wall):
                        self.notwallmap[y][x] = True
        self.init = True

    def get_tiles_to_see(self):
        tiles_to_see = []
        if self.turretDirection != self.direction:
            if self.turretDirection == Direction.UP:
                y = self.pos.y - 1
                while y >= 0:
                    if self.notwallmap[y][self.pos.x]:
                        break
                    tiles_to_see.append(Pos(self.pos.x, y))
                    y -= 1
            elif self.turretDirection == Direction.RIGHT:
                x = self.pos.x + 1
                while x < self.dimension:
                    if self.notwallmap[self.pos.y][x]:
                        break
                    tiles_to_see.append(Pos(x, self.pos.y))
                    x += 1
            elif self.turretDirection == Direction.DOWN:
                y = self.pos.y + 1
                while y < self.dimension:
                    if self.notwallmap[y][self.pos.x]:
                        break
                    tiles_to_see.append(Pos(self.pos.x, y))
                    y += 1
            elif self.turretDirection == Direction.LEFT:
                x = self.pos.x - 1
                while x >= 0:
                    if self.notwallmap[self.pos.y][x]:
                        break
                    tiles_to_see.append(Pos(x, self.pos.y))
                    x -= 1
        a = math.tan(math.pi/10)
        if self.direction == Direction.UP:
            for x in range(self.dimension):
                if x == self.pos.x:
                    a = -a
                y = int(round((x - self.pos.x) * a + self.pos.y, 0))
                while y >= 0:
                    if not self.notwallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y -= 1
        elif self.direction == Direction.DOWN:
            for x in range(self.dimension):
                if x == self.pos.x:
                    a = -a
                y = int(round((self.pos.x - x) * a + self.pos.y, 0))
                while y < self.dimension:
                    if not self.notwallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    y += 1
        elif self.direction == Direction.RIGHT:
            for y in range(self.dimension):
                if y == self.pos.y:
                    a = -a
                x = int(round(self.pos.x + a*(self.pos.y - y), 0))
                while x < self.dimension:
                    if not self.notwallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x += 1
        elif self.direction == Direction.LEFT:
            for y in range(self.dimension):
                if y == self.pos.y:
                    a = -a
                x = int(round(self.pos.x + a*(y - self.pos.y), 0))
                while x >= 0:
                    if not self.notwallmap[y][x]:
                        tiles_to_see.append(Pos(x, y))
                    x -= 1
        return tiles_to_see

    def update_diretion(self, tile: Tile):
        for entity in tile.entities:
            if isinstance(entity, AgentTank):
                self.direction = entity.direction
                self.turretDirection = entity.turret.direction
                break

    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        self.dimension = lobby_data.server_settings.grid_dimension
        pass

    def next_move(self, game_state: GameState) -> ResponseAction:
        if not self.init:
            self.analize_map(game_state.map)
        self.update_diretion(game_state.map.tiles[self.pos.y][self.pos.x])
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
