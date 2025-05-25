import websockets.sync.client
from threading import Thread
from typing import Callable, Optional

from pydantic import BaseModel

class GitWsMessage(BaseModel):
    service: str
    message: str
    action: str
    version: Optional[str] = None
    servie_name: Optional[str] = None

    def __str__(self) -> str:
        return f"GitWsMessage(service={self.service}, message={self.message}, action={self.action}, version={self.version})"

class GitWsClient:
    def __init__(self, git_websocket:tuple[str, int]) -> None:
        self.ws = websockets.sync.client.connect(f"ws://{git_websocket[0]}:{git_websocket[1]}/subscribe_to_updates")
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

    def start(self) -> None:
        """
        Start the WebSocket client in a separate thread to listen for messages.
        This method will block until the WebSocket connection is closed.
        """

        print("Starting Git WebSocket client...")

        while True:
            try:
                msg = self.ws.recv()
                if msg:
                    self.handle_msg(GitWsMessage.model_validate_json(msg))
            except websockets.ConnectionClosed:
                print("WebSocket connection closed.")
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break