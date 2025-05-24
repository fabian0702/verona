import websockets.sync.client
import json
from secrets import token_hex

class Proxy:
    def __init__(self, client:'Client', proxy_id:str, remote_host:str, remote_port:int):
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
    
    def stop(self):
        if not self.stopped:
            self.client.stop_proxy(self.proxy_id)

    def pause(self):
        self.client.pause_proxy(self.proxy_id)

    def resume(self):
        self.client.resume_proxy(self.proxy_id)

    def change_destination(self, remote_host:str, remote_port:int):
        """
        Change the destination of the proxy to a new remote host and port.
        :param remote_host: New remote host to which the proxy should connect.
        :param remote_port: New remote port to which the proxy should connect.
        """

        if self.remote_host == remote_host and self.remote_port == remote_port:
            return
        
        self.remote_host = remote_host
        self.remote_port = remote_port

        self.client.change_destination(self.proxy_id, remote_host, remote_port)

    def __del__(self):
        self.stop()

class Client:
    def __init__(self, socket_path:str='/run/verona/verona.sock'):
        self.ws = websockets.sync.client.unix_connect(socket_path, uri='ws://localhost/ws')
        self.proxies:dict[str, Proxy] = {}

    def new_proxy(self, local_port:int, remote_host:str, remote_port:int):
        proxy_id = self.start_proxy(local_port, remote_host, remote_port)
        proxy = Proxy(self, proxy_id, remote_host, remote_port)
        self.proxies[proxy_id] = proxy
        return proxy
    
    def start_proxy(self, local_port:int, remote_host:str, remote_port:int) -> str:
        """low level implementation of new_proxy, directly talks to websocket, for easy development use `self.new_proxy()`"""
        proxy_id = token_hex(6)
        data = json.dumps({'proxy_id':proxy_id, 'local_port':local_port, 'remote_host':remote_host, 'remote_port':remote_port})
        self._send_command(type='start_proxy', data=data)

        return proxy_id
    
    def stop_proxy(self, proxy_id:str):
        data = json.dumps({'proxy_id':proxy_id})
        self._send_command(type='stop_proxy', data=data)
        self.proxies.pop(proxy_id)

    def pause_proxy(self, proxy_id:str):
        self.change_pause_proxy(proxy_id, True)

    def resume_proxy(self, proxy_id:str):
        self.change_pause_proxy(proxy_id, False)

    def change_destination(self, proxy_id:str, remote_host:str, remote_port:int):
        data = json.dumps({'proxy_id':proxy_id, 'remote_host':remote_host, 'remote_port':remote_port})
        self._send_command(type='change_destination', data=data)

    def change_pause_proxy(self, proxy_id:str, pause:bool):
        data = json.dumps({'proxy_id':proxy_id, 'pause': pause})
        self._send_command(type='unpause_proxy', data=data)

    def _send_command(self, type:str, data:str):
        payload = json.dumps({'type':type, 'data':data})
        self.ws.send(payload)

if __name__ == '__main__':
    client = Client()
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