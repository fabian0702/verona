import time

from typing import Optional, Callable

from websockets.sync import client as websockets
from websockets.exceptions import ConnectionClosed
from websockets.protocol import State as WebSocketState

from scheduler.websocket.models import GitWsMessage


class GitWsClient:
    def __init__(self, git_websocket:tuple[str, int]) -> None:
        """
        Initialize the Git WebSocket client.
        :param git_websocket: A tuple containing the host and port of the Git WebSocket server.
        """

        self._running = False 

        self.host, self.port = git_websocket
        self.ws:websockets.ClientConnection = None  # Type hint for WebSocket connection
        self._connect()

        self.handle_rollback = lambda svc, version: None
        self.handle_deploy = lambda svc: None
        self.handle_register = lambda svc: None
    

    def on_rollback(self, func:Callable) -> None:
        """
        Register a callback function to handle rollback messages.
        :param func: The function to call when a rollback message is received.
        """
        self.handle_rollback = func


    def on_deploy(self, func:Callable) -> None:
        """
        Register a callback function to handle deploy messages.
        :param func: The function to call when a deploy message is received.
        """
        self.handle_deploy = func


    def on_register(self, func:Callable) -> None:
        """
        Register a callback function to handle registration messages.
        :param func: The function to call when a registration message is received.
        """
        self.handle_register = func

    
    def handle_msg(self, msg:GitWsMessage) -> None:
        """
        Handle incoming messages from the WebSocket.
        :param msg: The message received from the WebSocket.
        """
        try:
            match msg.action:
                case "rollback":
                    print(f"Rollback requested for service: {msg.service}, version: {msg.version}")
                    self.handle_rollback(msg.service, msg.version)
                case "deploy":
                    print(f"Deploy requested for service: {msg.service}")
                    self.handle_deploy(msg.service)
                case "register":
                    print(f"Registering service: {msg.service}")
                    self.handle_register(msg.service)
                case _:
                    print(f"Unknown action: {msg.action} for service: {msg.service}")
        except Exception as e:
            print(f"Error handling message {msg.action} for service {msg.service}: {e}")

    def _is_connected(self) -> bool:
        """
        Check if WebSocket is connected and ready.
        """

        return self.ws is not None and self.ws.state == WebSocketState.OPEN


    def _connect(self) -> None:
        """
        Attempt to connect to the WebSocket server.
        """

        if self._is_connected():
            print("WebSocket connection already open.")
            return
        print(f"Connecting to WebSocket server at ws://{self.host}:{self.port}/subscribe_to_updates")

        for _ in range(5):  # Try 5 times to ensure connection
            try:
                self.ws = websockets.connect(f"ws://{self.host}:{self.port}/subscribe_to_updates")
                print("Connected to WebSocket server")
                return
            except ConnectionClosed:
                print("WebSocket connection closed, retrying...")
                time.sleep(1)
            except Exception as e:
                print(f"Failed to connect: {e}")
                time.sleep(5)
        
        raise ConnectionError(f"Could not connect to WebSocket server at ws://{self.host}:{self.port}/subscribe_to_updates after multiple attempts.")


    def start(self) -> None:
        """
        Start the WebSocket client in a separate thread to listen for messages.
        This method will block until the WebSocket connection is closed.
        """

        print("Starting Git WebSocket client...")

        self._running = True

        while self._running:
            try:
                if not self._is_connected():
                    print("WebSocket connection not open, attempting to connect...")
                    self._connect()
                
                msg = self.ws.recv()
                if msg:
                    self.handle_msg(GitWsMessage.model_validate_json(msg))
            except ConnectionClosed:
                print("WebSocket connection closed. Attempting to reconnect...")
                self._connect()
            except ConnectionError as e:
                raise e     # Re-raise connection errors to be handled by the caller
            except Exception as e:
                print(f"Error receiving message: {e}")
                time.sleep(1)


    def stop(self) -> None:
        """
        Stop the WebSocket client gracefully.
        """

        self._running = False
        if self.ws and self.ws.state == WebSocketState.OPEN:
            self.ws.close()
        print("Git WebSocket client stopped")