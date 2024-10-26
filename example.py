"""This is an example of a bot participating in the HackArena 2.0.

This bot will randomly move around the map,
use abilities and print the map to the console.
"""

import os
import random

from hackathon_bot import *


class ExampleBot(HackathonBot):

    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        print(f"Lobby data received: {lobby_data}")

    def next_move(self, game_state: GameState) -> ResponseAction:
        self._print_map(game_state.map)

        # Check if the agent is dead
        if game_state.my_agent.is_dead:
            # Return pass to avoid warnings from the server
            # when the bot tries to make an action with a dead tank
            return Pass()

        return self._get_random_action()

    def on_game_ended(self, game_result: GameResult) -> None:
        print(f"Game ended: {game_result}")

    def on_warning_received(self, warning: WarningType, message: str | None) -> None:
        print(f"Warning received: {warning} - {message}")

    def _get_random_action(self):
        return random.choice(
            [
                Movement(MovementDirection.FORWARD),
                Movement(MovementDirection.BACKWARD),
                Rotation(RotationDirection.LEFT, RotationDirection.LEFT),
                Rotation(RotationDirection.LEFT, RotationDirection.RIGHT),
                Rotation(RotationDirection.LEFT, None),
                Rotation(RotationDirection.RIGHT, RotationDirection.LEFT),
                Rotation(RotationDirection.RIGHT, RotationDirection.RIGHT),
                Rotation(RotationDirection.RIGHT, None),
                Rotation(None, RotationDirection.LEFT),
                Rotation(None, RotationDirection.RIGHT),
                Rotation(None, None),  # Useless, better use Pass()
                #AbilityUse(Ability.FIRE_BULLET),
                #AbilityUse(Ability.FIRE_DOUBLE_BULLET),
                #AbilityUse(Ability.USE_LASER),
                #AbilityUse(Ability.USE_RADAR),
                #AbilityUse(Ability.DROP_MINE),
                Pass(),
            ]
        )

    def _print_map(self, game_map: Map):
        os.system("cls" if os.name == "nt" else "clear")
        end = " "

        for row in game_map.tiles:
            for tile in row:
                entity = tile.entities[0] if tile.entities else None

                if isinstance(entity, Wall):
                    print("#", end=end)
                elif isinstance(entity, Laser):
                    if entity.orientation is Orientation.HORIZONTAL:
                        print("|", end=end)
                    elif entity.orientation is Orientation.VERTICAL:
                        print("-", end=end)
                elif isinstance(entity, DoubleBullet):
                    if entity.direction == Direction.UP:
                        print("⇈", end=end)
                    elif entity.direction == Direction.RIGHT:
                        print("⇉", end=end)
                    elif entity.direction == Direction.DOWN:
                        print("⇊", end=end)
                    elif entity.direction == Direction.LEFT:
                        print("⇇", end=end)
                elif isinstance(entity, Bullet):
                    if entity.direction is Direction.UP:
                        print("↑", end=end)
                    elif entity.direction is Direction.RIGHT:
                        print("→", end=end)
                    elif entity.direction is Direction.DOWN:
                        print("↓", end=end)
                    elif entity.direction is Direction.LEFT:
                        print("←", end=end)
                elif isinstance(entity, AgentTank):
                    print("A", end=end)
                elif isinstance(entity, PlayerTank):
                    print("P", end=end)
                elif isinstance(entity, Mine):
                    print("x" if entity.exploded else "X", end=end)
                elif isinstance(entity, Item):
                    match (entity.type):
                        case SecondaryItemType.DOUBLE_BULLET:
                            print("D", end=end)
                        case SecondaryItemType.LASER:
                            print("L", end=end)
                        case SecondaryItemType.MINE:
                            print("M", end=end)
                        case SecondaryItemType.RADAR:
                            print("R", end=end)
                elif tile.zone:
                    index = chr(tile.zone.index)
                    index = index.upper() if tile.is_visible else index.lower()
                    print(index, end=end)
                elif tile.is_visible:
                    print(".", end=end)
                else:
                    print(" ", end=end)
            print()


if __name__ == "__main__":
    bot = ExampleBot()
    bot.run()
