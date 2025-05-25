from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException
from python_on_whales.components.container.cli_wrapper import Container

from scheduler.websocket.proxy_client import ProxyClient, Proxy
from scheduler.git.git import GitClient

import os
import yaml
import json

from typing import Optional
from pydantic import BaseModel, RootModel

class PortConfig(BaseModel):
    published: Optional[int | str] = None
    target: int | str
    protocol: str

    def proxy_config(self) -> tuple[int, int]:
        """
        Returns the port configuration for the proxy.
        :return: A tuple containing the published and target ports.
        """
        return int(self.published or self.target), int(self.target)
    
class PortConfigList(RootModel):
    root: list[PortConfig]

    def proxy_config(self) -> list[tuple[int, int]]:
        """
        Returns the port configurations for the proxy.
        :return: A list of tuples containing the published and target ports.
        """
        return [port.proxy_config() for port in self.root]

COMPOSE_FILE_NAMES = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']

class Service:
    def __init__(self, git_client:GitClient, websocket_client:ProxyClient):
        """
        Initialize the Service with a Docker Compose file.
        :param compose_file: Path to the Docker Compose file.
        """

        self.git_client = git_client

        self.compose_file = self.search_compose_file()
        self.rewrite_compose_file()
        self.websocket_client = websocket_client
        self.proxies:dict[str, dict[int, Proxy]] = {}

        self.build_containers()
        self.start_containers()
        self.setup_proxies()


    def search_compose_file(self) -> str:
        """
        Search for the Docker Compose file in the current directory.
        :return: The path to the Docker Compose file.
        """
        import os
        for root, dirs, files in os.walk(self.git_client.repo_path):
            for filename in COMPOSE_FILE_NAMES:
                if filename in files:
                    return os.path.join(root, filename)
        raise FileNotFoundError("Docker Compose file not found.")


    def rewrite_compose_file(self):
        """
        Rewrite the Docker Compose file with new content.
        :param new_content: The new content to write to the Docker Compose file.
        """
        client = DockerClient(compose_files=[self.compose_file])

        config = client.compose.config(return_json=True)

        for name, service in config['services'].items():
            if 'ports' in service:
                ports = service['ports']
                
                service['labels'].update({'ports_config':json.dumps(ports)})

                service['ports'] = []
                
        self.rewritten_compose_file = os.path.join(os.path.dirname(self.compose_file), 'docker-compose_rewritten.yaml')

        with open(self.rewritten_compose_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print(f"Rewritten {self.compose_file} with new content.")
        self.docker = DockerClient(compose_files=[self.rewritten_compose_file])
        return self.rewritten_compose_file

    def start_containers(self):
        """
        Start a Docker Compose project using the specified compose file.
        """

        self.docker.compose.up(detach=True)

        return self.docker.compose.ps()

    def find_container_ip(self, container:Container) -> Optional[str]:
        """
        Find the IP address of a container.
        :param container: The container to find the IP address for.
        :return: The IP address of the container.
        """
        if not container.network_settings:
            print(f'Container {container.name} has no network settings')
            return None
        
        for name, network in (container.network_settings.networks or {}).items():
            if name == 'host':
                print('Skipping host network container')
                continue
            if network.ip_address:
                return network.ip_address
        
        return container.network_settings.ip_address


    def find_ip_ports(self, container:Container) -> list[tuple[int, str, int]]:
        """
        Find the IP and port of a container.
        :param container: The container to find the IP and port for.
        :return: A tuple containing the IP address and port number.
        """
        labels = container.config.labels or {}
        if not 'ports_config' in labels:
            return []
        
        port_config = PortConfigList.model_validate_json(labels['ports_config'])

        container_ip = self.find_container_ip(container)

        if not container_ip:
            print('Container IP absent for some reason skipping container')
            return []

        return [(host_port, container_ip, container_port) for host_port, container_port in port_config.proxy_config()]


    def setup_proxies(self):
        """
        Setup proxies for the service based on the Docker Compose file.
        """

        for container in self.docker.compose.ps(all=True):
            proxies:dict[int, Proxy] = {}
            for host_port, container_ip, container_port in self.find_ip_ports(container):
                proxy = self.websocket_client.new_proxy(host_port, container_ip, container_port)
                proxies.update({host_port: proxy})
            if proxies:
                self.proxies.update({container.name:proxies})

    
    def update_proxy_destination(self, container:Container):
        """
        Update the proxy destination for the container.
        :param container: The container to update.
        """

        proxies = self.proxies.get(container.name)
        if not proxies:
            print(f'No proxy found for container {container.name}')
            return
        
        ip_ports = self.find_ip_ports(container)

        for host_port, container_ip, container_port in ip_ports:
            proxy = proxies.get(host_port)
            if not proxy:
                print(f'No proxy found for host port {host_port} in container {container.name}')
                new_proxy = self.websocket_client.new_proxy(host_port, container_ip, container_port)
                self.proxies[container.name].update({host_port: new_proxy})
                continue
            
            print(f'Updating proxy destination for container {container.name} to {container_ip}:{container_port}')
            proxy.change_destination(container_ip, int(container_port))

        host_ports = [host_port for host_port, _, _ in ip_ports]

        proxies_val = list(proxies.items())

        for old_host_port, proxy in proxies_val:
            if old_host_port not in host_ports:
                print(f'Removing proxy for host port {old_host_port} in container {container.name}')
                proxy.stop()
                del self.proxies[container.name][old_host_port]

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
        
        for container in self.proxies.values():
            for proxy in container.values():
                proxy.pause()


    def resume_proxies(self):
        """
        resume all proxies for this service
        """

        for container in self.proxies.values():
            for proxy in container.values():
                proxy.resume()


    def restart_service(self):
        """
        restart the containers of the service
        """

        self.build_containers()

        self.pause_proxies()

        self.stop_containers()

        self.rewrite_compose_file()

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

        for container in self.proxies.values():
            for proxy in container.values():
                print(f'Stopping proxy {proxy.proxy_id}')
                proxy.stop()
    
    
if __name__ == "__main__":
    ws_client = ProxyClient()
    git_client = GitClient("test", "git://github.com/username/repo.git", clone=False)
    svc = Service(git_client, ws_client)
    
    input()

    svc.restart_service()

    input()

    svc.teardown()

    ws_client.close()