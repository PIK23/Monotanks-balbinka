from hackathon_bot import Direction, Rotation
from typing import List, Tuple
import math
from queue import Queue
from pos import Pos


class FogOfWarManager:
    def __init__(self, wall_grid: List[List[bool]]):
        self.wall_grid = wall_grid
        self.width = len(wall_grid)
        self.height = len(wall_grid[0])

    @staticmethod
    def to_degrees(direction: Direction) -> int:
        if direction == Direction.UP: return 0
        if direction == Direction.RIGHT: return 90
        if direction == Direction.DOWN: return 180
        if direction == Direction.LEFT: return 270
        return 0

    def calculate_visibility_grid(self, obj_pos: Pos, obj_rot: Rotation, tur_rot: Rotation) -> List[Pos]:
        tank_position = (obj_pos.x + 0.5, obj_pos.y + 0.5)
        view_angle = 144
        tank_direction = FogOfWarManager.to_degrees(obj_rot)
        visited = [[False] * self.height for _ in range(self.width)]
        queue = Queue()

        positions = []

        queue.put((obj_pos.x, obj_pos.y))

        while not queue.empty():
            x, y = queue.get()

            if visited[y][x] or self.wall_grid[y][x]:
                continue

            visited[y][x] = True

            is_visible = (self.is_cell_visible(tank_position, (x + 0.25, y + 0.25), view_angle, tank_direction) or
                          self.is_cell_visible(tank_position, (x + 0.25, y + 0.75), view_angle, tank_direction) or
                          self.is_cell_visible(tank_position, (x + 0.75, y + 0.75), view_angle, tank_direction) or
                          self.is_cell_visible(tank_position, (x + 0.75, y + 0.25), view_angle, tank_direction))

            if is_visible:
                positions.append(Pos(x, y))
                self.enqueue_adjacent_cells(queue, x, y)

        self.update_turret_visibility(obj_pos, tur_rot, positions)

        return positions

    @staticmethod
    def normalize_angle(angle: float) -> float:
        while angle < -180:
            angle += 360
        while angle > 180:
            angle -= 360
        return angle

    def update_turret_visibility(self, obj_pos, tur_rot, positions: List[Pos]):
        start_x, start_y = obj_pos.x, obj_pos.y
        end_x, end_y = obj_pos.x, obj_pos.y
        step_x, step_y = 0, 0

        match tur_rot:
            case Direction.UP:
                start_y, end_y, step_y = obj_pos.y, -1, -1
            case Direction.RIGHT:
                start_x, end_x, step_x = obj_pos.x, self.width, 1
            case Direction.DOWN:
                start_y, end_y, step_y = obj_pos.y, self.height, 1
            case Direction.LEFT:
                start_x, end_x, step_x = obj_pos.x, -1, -1

        x, y = start_x, start_y

        while x != end_x or y != end_y:
            if self.wall_grid[y][x]:
                break

            positions.append(Pos(x, y))
            x += step_x
            y += step_y

    def is_cell_visible(self, tank_position: Tuple[float, float], cell_position: Tuple[float, float],
                        view_angle: float, tank_direction: float) -> bool:
        dx = cell_position[0] - tank_position[0]
        dy = cell_position[1] - tank_position[1]

        angle_to_cell = (math.atan2(dy, dx) * 180 / math.pi) + 90
        angle_difference = self.normalize_angle(angle_to_cell - tank_direction)

        return abs(angle_difference) <= view_angle / 2 and self.is_line_of_sight_clear(tank_position, cell_position)

    def is_line_of_sight_clear(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        x0, y0 = start
        x1, y1 = end

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        threshold = 0.1
        increment = 0.1

        while True:
            ix, iy = math.floor(x0), math.floor(y0)

            if self.wall_grid[iy][ix]:
                return False

            if abs(x0 - x1) < threshold and abs(y0 - y1) < threshold:
                break

            e2 = 2 * err

            if e2 > -dy:
                err -= dy
                x0 += sx * increment

            if e2 < dx:
                err += dx
                y0 += sy * increment

        return True

    def enqueue_adjacent_cells(self, queue: Queue, x: int, y: int) -> None:
        if x > 0:
            queue.put((x - 1, y))
        if x < self.width - 1:
            queue.put((x + 1, y))
        if y > 0:
            queue.put((x, y - 1))
        if y < self.height - 1:
            queue.put((x, y + 1))
