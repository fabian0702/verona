from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException
from python_on_whales.components.container.cli_wrapper import Container

from client import Client, Proxy

class Service:
    def __init__(self, compose_file:str, websocket_client:Client):
        """
        Initialize the Service with a Docker Compose file.
        :param compose_file: Path to the Docker Compose file.
        """
        self.compose_file = compose_file
        self.docker = DockerClient(compose_files=[compose_file])
        self.websocket_client = websocket_client
        self.proxies:dict[str, Proxy] = {}

        self.build_containers()
        self.start_containers()
        self.setup_proxies()


    def start_containers(self):
        """
        Start a Docker Compose project using the specified compose file.
        """

        self.docker.compose.up(detach=True)

        return self.docker.compose.ps()


    def find_ip_port(self, container:Container) -> tuple[int | None, str | None, int | None]:
        """
        Find the IP and port of a container.
        :param container: The container to find the IP and port for.
        :return: A tuple containing the IP address and port number.
        """
        labels = container.config.labels or {}
        host_port, container_port = labels.get('host_port'), labels.get('container_port')
        if not host_port or not container_port:
            return None, None, None

        container_ip = None
        for name, network in (container.network_settings.networks or {}).items():
            if name == 'host':
                print('Skipping host network container')
                continue
            if network.ip_address:
                container_ip = network.ip_address
                break
        
        container_ip = container_ip or container.network_settings.ip_address

        if not container_ip:
            print('Container IP absent for some reason skipping container')
            return None, None, None

        return int(host_port), container_ip, int(container_port)


    def setup_proxies(self):
        """
        Setup proxies for the service based on the Docker Compose file.
        """

        for container in self.docker.compose.ps(all=True):
            host_port, container_ip, container_port = self.find_ip_port(container)
            if host_port is None or container_ip is None or container_port is None:
                print(f'Skipping container {container.name} due to missing port or IP information')
                continue

            proxy = self.websocket_client.new_proxy(int(host_port), container_ip, int(container_port))
            self.proxies.update({container.name:proxy})

    
    def update_proxy_destination(self, container:Container):
        """
        Update the proxy destination for the container.
        :param container: The container to update.
        """
        host_port, container_ip, container_port = self.find_ip_port(container)
        if host_port is None or container_ip is None or container_port is None:
            print(f'Skipping update for container {container.name} due to missing port or IP information')
            return

        proxy = self.proxies.get(container.name)
        if not proxy:
            print(f'No proxy found for container {container.name}')
            return
        
        print(f'Updating proxy destination for container {container.name} to {container_ip}:{container_port}')

        proxy.change_destination(container_ip, int(container_port))

    def update_proxies(self):
        """
        Update the proxies for the service by checking each container.
        """

        for container in self.docker.compose.ps(all=True):
            print(f'Updating proxy destination for container {container.name}')
            self.update_proxy_destination(container)

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
        
        for proxy in self.proxies.values():
            proxy.pause()


    def resume_proxies(self):
        """
        resume all proxies for this service
        """

        for proxy in self.proxies.values():
            proxy.resume()


    def restart_service(self):
        """
        restart the containers of the service
        """

        self.build_containers()

        self.pause_proxies()

        self.stop_containers()

        self.start_containers()

        self.update_proxies()

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

        for proxy in self.proxies.values():
            proxy.stop()
    
    
if __name__ == "__main__":
    ws_client = Client()
    svc = Service("test/docker-compose.yml", ws_client)
    
    input()

    svc.restart_service()

    input()

    svc.teardown()
