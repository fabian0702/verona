from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException

from scheduler.websocket.client import Client, Proxy

class Service:
    def __init__(self, compose_file:str, websocket_client:Client):
        """
        Initialize the Service with a Docker Compose file.
        :param compose_file: Path to the Docker Compose file.
        """
        self.compose_file = compose_file
        self.docker = DockerClient(compose_files=[compose_file])
        self.websocket_client = websocket_client
        self.proxies:list[Proxy] = []

        self.build_containers()
        self.start_containers()

    def start_containers(self):
        """
        Start a Docker Compose project using the specified compose file.
        """

        self.docker.compose.up(detach=True)

        return self.docker.compose.ps()
    
    def setup_proxies(self):
        """
        Setup proxies for the service based on the Docker Compose file.
        """

        for container in self.docker.compose.ps(all=True):
            labels = container.config.labels or {}
            host_port, container_port = labels.get('host_port'), labels.get('container_port')
            if host_port and container_port:
                container_ip = container.network_settings.ip_address
                if not container_ip:
                    print('Container IP absent for some reason skipping container')
                    continue

                proxy = self.websocket_client.new_proxy(int(host_port), container_ip, int(container_port))
                self.proxies.append(proxy)

    def build_containers(self):
        """
        build/rebuild the containers of the service
        """

        try:
            self.docker.compose.build()
        except DockerException:
            print('failed to build containers')

    def pause_proxies(self):
        """
        pause all proxies for this service
        """
        
        for proxy in self.proxies:
            proxy.pause()

    def resume_proxies(self):
        """
        resume all proxies for this service
        """

        for proxy in self.proxies:
            proxy.resume()

    def restart_service(self):
        """
        restart the containers of the service
        """

        self.build_containers()

        self.pause_proxies()
        self.stop_containers()

        self.start_containers()
        self.resume_proxies()

    def stop_containers(self):
        """
        Stop a Docker Compose project using the specified compose file.
        """
        try:
            self.docker.compose.down()
            return True
        except DockerException as e:
            pass

        for container in self.docker.compose.ps():
            try:
                self.docker.container.stop(container.id)
            except DockerException as e:
                pass
        return False
    
    def teardown(self):
        """
        Teardown the service by stopping all containers and proxies.
        """
        
        self.stop_containers()

        for proxy in self.proxies:
            proxy.stop()
    
    
if __name__ == "__main__":
    ws_client = Client()
    svc = Service("test/docker-compose.yml", ws_client)
    svc.start_containers()
