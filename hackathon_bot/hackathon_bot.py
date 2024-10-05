"""The main module for the hackathon bot.

This module contains the main class for the hackathon bot.

Classes
-------
HackathonBot
    Represents the hackathon bot.

Examples
--------
To run the hackathon bot, create a new class that inherits
from the `HackathonBot` class and implement the required methods.
Then, create an instance of the bot and run it using the `run` method.

.. code-block:: python

    import asyncio

    from hackathon_bot import (
        HackathonBot,
        GameState,
        GameResult,
        LobbyData,
        ResponseAction,
        WarningType,
    )

    class MyBot(HackathonBot):

        def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
            # Implement the lobby data received logic here

        def next_move(self, game_state: GameState) -> ResponseAction:
            # Implement the next move logic here
            # Return a response action

        def on_game_ended(self, game_result: GameResult) -> None:
            # Implement the game ended logic here

        def on_warning_received(self, warning: WarningType, message: str | None) -> None:
            # Implement the warning received logic here
            # (for example, print it)

    if __name__ == "__main__":
        bot = MyBot()
        bot.run()
"""

import asyncio
import json
import threading
import traceback
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import final

import humps
import websockets
from websockets import WebSocketClientProtocol as WebSocket

from . import argparser
from .actions import Pass, ResponseAction
from .enums import PacketType, WarningType
from .models import GameStateModel, GameResultModel, LobbyDataModel
from .payloads import (
    ConnectionRejectedPayload,
    GameEndPayload,
    GameStatePayload,
    LobbyDataPayload,
    Payload,
)
from .protocols import GameState, GameResult, LobbyData


class HackathonBot(ABC):
    """Represents the hackathon bot.

    This class is used to create a new hackathon bot.

    Examples
    --------
    To run the hackathon bot, create a new class that inherits
    from the `HackathonBot` class and implement the required methods.
    Then, create an instance of the bot and run it using the `run` method.

    .. code-block:: python

        from hackathon_bot import (
            HackathonBot,
            GameState,
            GameResult,
            LobbyData,
            ResponseAction,
            WarningType,
        )

        class MyBot(HackathonBot):

            def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
                # Implement the lobby data received logic here

            def next_move(self, game_state: GameState) -> ResponseAction:
                # Implement the next move logic here
                # Return a response action (example below)

            def on_game_ended(self, game_result: GameResult) -> None:
                # Implement the game ended logic here

            def on_warning_received(self, warning: WarningType, message: str | None) -> None:
                # Implement the warning received logic here
                # (for example, print it)

        if __name__ == "__main__":
            bot = MyBot()
            bot.run()

    The `next_move` method should return a response action.
    The response action can be a `Movement`, `Rotation`, `Shoot` or `Pass` action.

    .. code-block:: python

        from hackathon_bot import (
            Movement,
            MovementDirection,
            Rotation,
            RotationDirection,
            Shoot,
            Pass,
        )

        async def next_move(self, game_state: GameState) -> ResponseAction:
            return Movement(MovementDirection.FORWARD)
            # or
            return Rotation(RotationDirection.LEFT, None)
            # or
            return Shoot()
            # or
            return Pass()  # to skip the tick
    """

    _lobby_data: LobbyDataModel
    _is_processing: bool = False
    _loop: asyncio.AbstractEventLoop

    def _get_server_url(self, args: argparser.Arguments) -> str:
        url = f"ws://{args.host}:{args.port}/?nickname={args.nickname}&playerType=hackathonBot"

        if args.code:
            url += f"&joinCode={args.code}"

        return url

    @abstractmethod
    def on_lobby_data_received(self, lobby_data: LobbyData) -> None:
        """Called when the lobby data is received.

        Parameters
        ----------
        lobby_data: :class:`LobbyData`
            The lobby data received from the server.
        """

    @abstractmethod
    def next_move(self, game_state: GameState) -> ResponseAction:
        """Called when the bot should make the next move.

        Parameters
        ----------
        game_state: :class:`GameState`
            The current game state.

        Returns
        -------
        ResponseAction
            The response action for the next move.

        Examples
        --------
        The response action can be a `Movement`, `Rotation`, `Shoot` or `Pass` action.

        .. code-block:: python

            from hackathon_bot import (
                HackathonBot,
                GameState,
                ResponseAction,
                Movement,
                MovementDirection,
                Rotation,
                RotationDirection,
                Shoot,
                Pass,
            )

            class MyBot(HackathonBot):

                # Other methods

                def next_move(self, game_state: GameState) -> ResponseAction:
                    return Movement(MovementDirection.FORWARD)
                    # or
                    return Rotation(RotationDirection.LEFT, None)
                    # or
                    return Shoot()
                    # or
                    return Pass()  # to skip the tick

        Notes
        -----
        If the method returns `None`, the bot will respond with `Pass` action.
        """

    @abstractmethod
    def on_game_ended(self, game_result: GameResult) -> None:
        """Called when the game has ended.

        Parameters
        ----------
        game_result: :class:`GameResult
            The game result with the scores of the players.
        """

    @abstractmethod
    def on_warning_received(self, warning: WarningType, message: str | None) -> None:
        """Called when a warning is received from the server.

        Parameters
        ----------
        warning: :class:`WarningType`
            The warning type.
        message: :class:`str` | :class:`None`
            The warning message.
            Only present for `Custom` warning type.
        """

    @final
    async def _send_packet(
        self,
        websocket,
        packet_type: PacketType,
        payload: Payload | None = None,
    ):
        packet = {"type": packet_type.value}

        if payload:
            packet["payload"] = humps.camelize(asdict(payload))

        await websocket.send(json.dumps(packet))

    @final
    def _handle_ping_packet(self, websocket: WebSocket) -> None:
        asyncio.run_coroutine_threadsafe(
            self._send_packet(websocket, PacketType.PONG), self._loop
        )

    @final
    def _handle_next_move(
        self, websocket: WebSocket, game_state: GameStateModel
    ) -> None:
        if self._is_processing:
            print("Skipping next game state due to ongoing processing!")
            return

        self._is_processing = True

        try:
            response_action = self.next_move(game_state)
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:  # pylint: disable=broad-except
            print(f"An error occurred during next move: {e}")
            print(traceback.format_exc())
            return
        finally:
            self._is_processing = False

        if response_action is None:
            response_action = Pass()

        payload = response_action.to_payload(game_state.id)
        asyncio.run_coroutine_threadsafe(
            self._send_packet(websocket, response_action.packet_type, payload),
            self._loop,
        )

    @final
    def _handle_messages(  # pylint: disable=too-many-return-statements
        self, websocket: WebSocket, message: websockets.Data
    ) -> None:
        data = humps.decamelize(json.loads(message))

        packet_type = PacketType(data["type"])

        if packet_type == PacketType.PING:
            self._handle_ping_packet(websocket)
            return

        if packet_type == PacketType.GAME_STATE:
            payload = GameStatePayload.from_json(data["payload"])
            player_id = self._lobby_data.player_id
            game_state = GameStateModel.from_payload(payload, player_id)
            threading.Thread(
                target=self._handle_next_move, args=(websocket, game_state)
            ).start()
            return

        if packet_type == PacketType.LOBBY_DATA:
            payload = LobbyDataPayload.from_json(data["payload"])
            lobby_data = LobbyDataModel.from_payload(payload)
            self._lobby_data = lobby_data
            self.on_lobby_data_received(lobby_data)
            return

        if packet_type & 0xF0 == PacketType.WARNING_GROUP:
            has_payload = packet_type & PacketType.HAS_PAYLOAD
            message = data["payload"] if has_payload else None
            self.on_warning_received(WarningType(packet_type), message)
            return

        if packet_type == PacketType.CONNECTION_ACCEPTED:
            print("Connected to the server.")
            return

        if packet_type == PacketType.CONNECTION_REJECTED:
            payload = ConnectionRejectedPayload.from_json(data["payload"])
            print(f"Connection rejected: {payload.reason}")
            return

        if packet_type == PacketType.GAME_START:
            print("Game started.")
            return

        if packet_type == PacketType.GAME_END:
            payload = GameEndPayload.from_json(data["payload"])
            game_result = GameResultModel.from_payload(payload)
            self.on_game_ended(game_result)
            return

    @final
    async def _start_loop(self, server_url: str) -> None:
        self._loop = asyncio.get_event_loop()
        async with websockets.connect(server_url) as websocket:
            while True:
                try:
                    message = await websocket.recv()
                    self._handle_messages(websocket, message)
                except websockets.exceptions.ConnectionClosedOK as e:
                    print(
                        "Connection closed by the server"
                        f"{': ' + e.rcvd.reason if e.rcvd and e.rcvd.reason else '.'}",
                    )
                    break
                except websockets.exceptions.ConnectionClosedError as e:
                    print(
                        "Connection closed with an "
                        f"{'error: ' + e.rcvd.reason if e.rcvd and e.rcvd.reason else 'unknown error.'}",
                    )
                    break
                except Exception as e:  # pylint: disable=broad-except
                    print(f"An error occurred: {e}")  # pragma: no cover
                    print(traceback.format_exc())  # pragma: no cover

    @final
    def run(self) -> None:
        """Connects to the server and runs the hackathon bot.

        Examples
        --------

        .. code-block:: python

            from hackathon_bot import HackathonBot

            class MyBot(HackathonBot):
                # Your bot implementation here

            if __name__ == "__main__":
                bot = MyBot()
                bot.run()
        """

        args = argparser.get_args()
        server_url = self._get_server_url(args)
        asyncio.run(self._start_loop(server_url))