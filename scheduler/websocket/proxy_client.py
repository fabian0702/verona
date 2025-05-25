import json
from secrets import token_hex

import websockets.sync.client

from scheduler.websocket.models import ProxyResponse


class Proxy:
    def __init__(self, client:'ProxyClient', proxy_id:str, remote_host:str, remote_port:int, local_port:int):
        """
        Proxy object to manage a single proxy connection.
        :param client: Client instance to communicate with the server.
        :param proxy_id: Unique identifier for the proxy.
        :param remote_host: Remote host to which the proxy connects.
        :param remote_port: Remote port to which the proxy connects.
        """

        self.stopped = False
        self.client = client
        self.proxy_id = proxy_id
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_port = local_port


    def stop(self):
        """
        Stop the proxy if it is currently running.
        :raises
            RuntimeError: If the proxy is already stopped or if the proxy ID is invalid.
        """

        if not self.stopped:
            self.stopped = True
            self.client.stop_proxy(self.proxy_id)


    def pause(self):
        """
        Pause the proxy if it is currently running.
        :raises
            RuntimeError: If the proxy is already paused or if the proxy ID is invalid.
        """

        self.client.pause_proxy(self.proxy_id)


    def resume(self):
        """
        Resume the proxy if it was paused.
        :raises
            RuntimeError: If the proxy is already running or if the proxy ID is invalid.
        """

        self.client.resume_proxy(self.proxy_id)


    def change_destination(self, remote_host:str, remote_port:int):
        """
        Change the destination of the proxy to a new remote host and port.
        :param remote_host: New remote host to which the proxy should connect.
        :param remote_port: New remote port to which the proxy should connect.
        :raises
            ValueError: If the remote host or port is invalid.
        """

        if self.remote_host == remote_host and self.remote_port == remote_port:
            return
        
        self.remote_host = remote_host
        self.remote_port = remote_port

        self.client.change_destination(self.proxy_id, remote_host, remote_port)


    def __del__(self):
        """
        Destructor to ensure the proxy is stopped when the object is deleted.
        This is a safety measure to prevent resource leaks.
        """

        self.stop()


class ProxyClient:
    def __init__(self, socket_path:str='/run/verona/verona.sock'):
        """
        Initialize the ProxyClient to manage WebSocket connections for proxy operations.
        :param socket_path: The path to the WebSocket server socket.
        :raises
            RuntimeError: If the WebSocket connection cannot be established.
        """
        try:
            self.ws = websockets.sync.client.unix_connect(socket_path, uri='ws://localhost/ws')
        except Exception as e:
            raise RuntimeError(f"Failed to connect to WebSocket server at {socket_path}: {e}")
        
        self.proxies:dict[str, Proxy] = {}
        self.closed = False


    def new_proxy(self, local_port:int, remote_host:str, remote_port:int):
        """
        Create a new proxy that binds to the specified local port and connects to the specified remote host and port.
        :param local_port: The local port to bind the proxy to.
        :param remote_host: The remote host to which the proxy should connect.
        :param remote_port: The remote port to which the proxy should connect.
        :return: A Proxy object representing the created proxy.
        :raises
            ValueError: If the local port is already in use or if the remote host/port is invalid.
        """

        proxy_id = self.start_proxy(local_port, remote_host, remote_port)
        proxy = Proxy(self, proxy_id, remote_host, remote_port, local_port)
        self.proxies[proxy_id] = proxy
        return proxy
    
    
    def start_proxy(self, local_port:int, remote_host:str, remote_port:int) -> str:
        """
        low level implementation of new_proxy, directly talks to websocket, for easy development use `self.new_proxy()`
        :param local_port: The local port to bind the proxy to.
        :param remote_host: The remote host to which the proxy should connect.
        :param remote_port: The remote port to which the proxy should connect.
        :return: A unique identifier for the created proxy.
        :raises
            ValueError: If the local port is already in use or if the remote host/port is invalid.
        """

        if local_port < 1024 or local_port > 65535:
            raise ValueError(f"Invalid local port: {local_port}. Must be between 1024 and 65535.")
        if not remote_host or not isinstance(remote_host, str):
            raise ValueError(f"Invalid remote host: {remote_host}. Must be a non-empty string.")
        if remote_port < 1 or remote_port > 65535:
            raise ValueError(f"Invalid remote port: {remote_port}. Must be between 1 and 65535.")
        if local_port in [p.local_port for p in self.proxies.values()]:
            raise ValueError(f"Local port {local_port} is already in use by another proxy.")

        proxy_id = token_hex(6)
        data = json.dumps({'proxy_id':proxy_id, 'local_port':local_port, 'remote_host':remote_host, 'remote_port':remote_port})
        self._send_command(type='start_proxy', data=data)

        return proxy_id
    
    def stop_proxy(self, proxy_id:str):
        """
        Stop the proxy with the given ID.
        :param proxy_id: The ID of the proxy to stop.
        :raises
            ValueError: If the proxy ID is invalid or the proxy is already stopped.
        """

        if not self._is_valid_proxy(proxy_id):
            raise ValueError(f"Invalid proxy ID: {proxy_id}")
        
        data = json.dumps({'proxy_id':proxy_id})
        self._send_command(type='stop_proxy', data=data)
        if proxy_id in self.proxies:
            self.proxies.pop(proxy_id)

    def _is_valid_proxy(self, proxy_id:str) -> bool:
        """
        Check if the given proxy ID is valid.
        :param proxy_id: The ID of the proxy to check.
        :return: True if the proxy ID is valid, False otherwise.
        """
        return proxy_id in self.proxies and not self.proxies[proxy_id].stopped


    def pause_proxy(self, proxy_id:str):
        """
        Pause the proxy with the given ID.
        :param proxy_id: The ID of the proxy to pause.
        :raises
            ValueError: If the proxy ID is invalid or the proxy is already paused.
        """

        self.change_proxy_pause_state(proxy_id, True)

    def resume_proxy(self, proxy_id:str):
        """
        Resume the proxy with the given ID.
        :param proxy_id: The ID of the proxy to resume.
        :raises
            ValueError: If the proxy ID is invalid or the proxy is already running.
        """

        self.change_proxy_pause_state(proxy_id, False)

    def change_destination(self, proxy_id:str, remote_host:str, remote_port:int):
        """
        Change the destination of the proxy with the given ID to a new remote host and port.
        :param proxy_id: The ID of the proxy to change the destination for.
        :param remote_host: New remote host to which the proxy should connect.
        :param remote_port: New remote port to which the proxy should connect.
        :raises
            ValueError: If the proxy ID is invalid or the remote host/port is invalid.
        """

        if not self._is_valid_proxy(proxy_id):
            raise ValueError(f"Invalid proxy ID: {proxy_id}")
        
        data = json.dumps({'proxy_id':proxy_id, 'remote_host':remote_host, 'remote_port':remote_port})
        self._send_command(type='change_destination', data=data)


    def change_proxy_pause_state(self, proxy_id:str, pause:bool):
        """
        Change the pause state of the proxy with the given ID.
        :param proxy_id: The ID of the proxy to change the pause state for.
        :param pause: True to pause the proxy, False to resume it.
        :raises
            ValueError: If the proxy ID is invalid or the pause state is not a boolean.
        """

        if not self._is_valid_proxy(proxy_id):
            raise ValueError(f"Invalid proxy ID: {proxy_id}")

        data = json.dumps({'proxy_id':proxy_id, 'pause': pause})
        self._send_command(type='set_proxy_pause_state', data=data)


    def _wait_for_response(self):
        """
        Wait for a response from the WebSocket server.
        :return: The response message from the server.
        :raises
            RuntimeError: If the WebSocket connection is closed or if the response indicates an error.
        """

        if not self.ws or self.closed:
            raise RuntimeError("WebSocket connection is closed")
        
        response = ProxyResponse.model_validate_json(self.ws.recv())
        if response.is_error:
            print(f"Error from server: {response.msg}")
            raise Exception(f"Error from server: {response.msg}")
        
        return response.msg


    def _send_command(self, type:str, data:str):
        """
        Send a command to the WebSocket server.
        :param type: The type of command to send.
        :param data: The data to send with the command, serialized as a JSON string.
        :raises
            RuntimeError: If the WebSocket connection is closed or if sending the command fails.
        """

        if not self.ws or self.closed:
            raise RuntimeError("WebSocket connection is closed")
        
        try:
            payload = json.dumps({'type':type, 'data':data})
            self.ws.send(payload)
            self._wait_for_response()
        except Exception as e:
            print(f"Failed to send command {type}: {e}")
            raise


    def close(self):
        """
        Close the WebSocket connection.
        This method should be called when the client is no longer needed.
        """

        if self.closed:
            return
        
        print("Closing WebSocket connection...")
        try:
            self.ws.close()
        except Exception as e:
            print(f"Error closing WebSocket: {e}")
        finally:
            self.closed = True


if __name__ == '__main__':
    client = ProxyClient()
    print('[*] starting proxy, press enter to continue')
    proxy = client.new_proxy(8080, 'localhost', 4444)
    input()
    print('[*] pausing proxy input, press enter to continue')
    proxy.pause()
    input()
    print('[*] resuming proxy input, press enter to continue')
    proxy.resume()
    input()
    print('[*] changing destination, press enter to finish')
    proxy.change_destination('localhost', 5555)
    input()
    print('[*] stopping proxy')