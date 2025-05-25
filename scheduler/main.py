from scheduler.git.git import GitClient
from scheduler.websocket.gitserver_client import GitWsClient
from scheduler.docker.docker import DockerService
from scheduler.websocket.proxy_client import ProxyClient

GITSERVER = 'git://github.com/username/'

class Service:
    def __init__(self, proxy_client: ProxyClient):
        self.proxy_client = proxy_client

    def register(self, name: str):
        self.name = name
        self.git_client = GitClient(name, f"git://github.com/username/")
        self.docker_service = DockerService(self.git_client, self.proxy_client)

    def deploy(self):
        """
        Deploy the service by pulling the latest code and restarting the Docker containers.
        """
        print(f"Deploying service {self.name}...")
        self.git_client.clone()
        self.git_client.pull_latest()
        self.docker_service.restart_service()
        print(f"Service {self.name} deployed successfully.")

    def rollback(self, version: str):
        """
        Rollback the service to a previous version.
        :param version: The version to rollback to.
        """
        print(f"Rolling back service {self.name} to version {version}...")
        self.git_client.checkout(version)
        self.docker_service.restart_service()
        print(f"Service {self.name} rolled back to version {version}.")

services:dict[str, Service] = {}

def register_service(name: str):
    """
    Register a new service with the given name and proxy client.
    :param name: The name of the service.
    :param proxy_client: The proxy client to use for the service.
    """
    if name in services:
        print(f"Service {name} is already registered.")
        return
    
    proxy_client = ProxyClient()

    service = Service(proxy_client)
    service.register(name)
    services[name] = service
    print(f"Service {name} registered successfully.")

def deploy_service(name: str):
    """
    Deploy the service with the given name.
    :param name: The name of the service to deploy.
    """
    if name not in services:
        print(f"Service {name} is not registered.")
        return
    
    services[name].deploy()

    print(f"Service {name} deployed successfully.")

def rollback_service(name: str, version: str):
    """
    Rollback the service with the given name to a specific version.
    :param name: The name of the service to rollback.
    :param version: The version to rollback to.
    """
    if name not in services:
        print(f"Service {name} is not registered.")
        return
    
    services[name].rollback(version)

    print(f"Service {name} rolled back to version {version}.")


def main():
    print("Starting scheduler...")

    gitserver_client = GitWsClient(('localhost', 8000))
    gitserver_client.on_deploy(deploy_service)
    gitserver_client.on_rollback(rollback_service)
    gitserver_client.on_register(register_service)

    print("Git server client initialized and event handlers registered.")

    gitserver_client.start()

if __name__ == "__main__":
    main()