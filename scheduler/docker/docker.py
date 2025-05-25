from typing import Optional

from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException
from python_on_whales.components.container.cli_wrapper import Container

from scheduler.websocket.proxy_client import ProxyClient, Proxy
from scheduler.git.git import GitClient
from scheduler.docker.file import File
from scheduler.docker.models import PortConfigList


class DockerService:
    def __init__(self, git_client:GitClient, websocket_client:ProxyClient):
        """
        Initialize the Service with a Docker Compose file.
        :param compose_file: Path to the Docker Compose file.
        """

        self.git_client = git_client

        self.compose_file = File.search_compose_file(git_client.repo_path)
        self.rewrite_compose_file()

        self.websocket_client = websocket_client
        self.proxies:dict[str, dict[int, Proxy]] = {}

        self.build_containers()
        self.start_containers()
        self.setup_proxies()


    def start_containers(self) -> None:
        """
        Start the containers of the service using Docker Compose.
        """

        try:
            self.docker.compose.up(detach=True, quiet=True, remove_orphans=True)
            return  # Success, no need to start individually
        except DockerException:
            print('Failed to start containers, trying to start them individually')
            
        for container in self.docker.compose.ps(all=True):
            if container.state.status != 'running':
                try:
                    self.docker.container.start(container.id)
                except DockerException:
                    print(f'Failed to start container {container.name}, skipping')
        

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


    def get_container_port_mappings(self, container:Container) -> list[tuple[int, str, int]]:
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


    def setup_proxies(self) -> None:
        """
        Setup proxies for the service based on the Docker Compose file.
        """

        for container in self.docker.compose.ps(all=True):
            proxies:dict[int, Proxy] = {}

            for host_port, container_ip, container_port in self.get_container_port_mappings(container):
                proxy = self.websocket_client.new_proxy(host_port, container_ip, container_port)
                proxies.update({host_port: proxy})

            self.proxies.update({container.name:proxies})

    
    def update_proxy_destination(self, container: Container) -> None:
        """
        Update the proxy destination for the container.
        :param container: The container to update.
        """

        proxies = self.proxies.get(container.name)
        if not proxies:
            print(f'No proxy found for container {container.name}')
            return
        
        container_port_mappings = self.get_container_port_mappings(container)
        current_host_ports = {host_port for host_port, _, _ in container_port_mappings}
        
        self._update_existing_proxies(container, proxies, container_port_mappings)
        self._create_missing_proxies(container, proxies, container_port_mappings)
        self._remove_stale_proxies(container, proxies, current_host_ports)


    def _update_existing_proxies(self, container: Container, proxies: dict[int, Proxy], port_mappings: list[tuple[int, str, int]]) -> None:
        """
        Update destinations for existing proxies.
        """

        for host_port, container_ip, container_port in port_mappings:
            if host_port in proxies:
                try:
                    print(f'Updating proxy destination for container {container.name} to {container_ip}:{container_port}')
                    proxies[host_port].change_destination(container_ip, container_port)
                except Exception as e:
                    print(f'Failed to update proxy for port {host_port}: {e}')



    def _create_missing_proxies(self, container: Container, proxies: dict[int, Proxy], port_mappings: list[tuple[int, str, int]]) -> None:
        """
        Create new proxies for ports that don't have them.
        """

        for host_port, container_ip, container_port in port_mappings:
            if host_port not in proxies:
                try:
                    print(f'Creating new proxy for host port {host_port} in container {container.name}')
                    proxy = self.websocket_client.new_proxy(host_port, container_ip, container_port)
                    if proxy:  # Verify proxy was created successfully
                        proxies[host_port] = proxy
                    else:
                        print(f'Failed to create proxy for port {host_port}: proxy creation returned None')
                except Exception as e:
                    print(f'Failed to create proxy for port {host_port}: {e}')


    def _remove_stale_proxies(self, container: Container, proxies: dict[int, Proxy], current_host_ports: set[int]) -> None:
        """
        Remove proxies for ports that no longer exist.
        """

        stale_ports = set(proxies.keys()) - current_host_ports
        for stale_port in stale_ports:
            print(f'Removing proxy for host port {stale_port} in container {container.name}')
            proxies[stale_port].stop()
            del proxies[stale_port]


    def update_proxies(self) -> None:
        """
        Update the proxies for the service by checking each container.
        """

        for container in self.docker.compose.ps(all=True):
            print(f'Updating proxy destination for container {container.name}')
            self.update_proxy_destination(container)


    def build_containers(self) -> None:
        """
        build/rebuild the containers of the service
        """

        try:
            self.docker.compose.build(quiet=True)
        except DockerException as e:
            print(f'Failed to build containers: {e}')


    def pause_proxies(self) -> None:
        """
        pause all proxies for this service
        """
        
        for container in self.proxies.values():
            for proxy in container.values():
                proxy.pause()


    def resume_proxies(self) -> None:
        """
        resume all proxies for this service
        """

        for container in self.proxies.values():
            for proxy in container.values():
                proxy.resume()


    def rewrite_compose_file(self) -> None:
        """
        Rewrite the compose file to ensure it is up to date.
        """

        self.rewritten_compose_file = File.rewrite_compose_file(self.compose_file)
        self.docker = DockerClient(compose_files=[self.rewritten_compose_file])


    def restart_service(self) -> None:
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


    def stop_containers(self) -> None:
        """
        Stop a Docker Compose project using the specified compose file.
        """

        try:
            self.docker.compose.down(quiet=True, remove_orphans=True)
            return
        except DockerException:
            print('Failed to stop containers, trying to stop them individually')

        for container in self.docker.compose.ps():
            try:
                self.docker.container.stop(container.id)
            except DockerException:
                print(f'Failed to stop container {container.name}, skipping')


    def teardown(self) -> None:
        """
        Teardown the service by stopping all containers and proxies.
        """

        self.stop_containers()

        for container in self.proxies.values():
            for proxy in container.values():
                try:
                    print(f'Stopping proxy {proxy.proxy_id}')
                    proxy.stop()
                except Exception as e:
                    print(f'Failed to stop proxy {proxy.proxy_id}: {e}')
        
        self.proxies.clear()
        self.websocket_client.close()
    
    
if __name__ == "__main__":
    ws_client = ProxyClient()
    git_client = GitClient("test", "git://github.com/username/repo.git", clone=False)
    svc = DockerService(git_client, ws_client)
    
    input()

    svc.restart_service()

    input()

    svc.teardown()

    ws_client.close()