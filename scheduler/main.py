import logging
import re
from typing import Dict
from scheduler.git.git import GitClient
from scheduler.websocket.gitserver_client import GitWsClient
from scheduler.docker.docker import DockerService
from scheduler.websocket.proxy_client import ProxyClient

# Configuration
GITSERVER = 'git://localhost:9418/'

# Setup logging
logger = logging.getLogger(__name__)

class Service:
    def __init__(self, name: str, proxy_client: ProxyClient):
        # Validate service name to prevent injection
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(f"Invalid service name: {name}")
        
        self.name = name
        self.proxy_client = proxy_client
        self.git_client = GitClient(name, GITSERVER)
        self.docker_service = DockerService(self.git_client, self.proxy_client)

    def deploy(self) -> bool:
        """Deploy the service by pulling latest code and restarting containers."""
        try:
            logger.info(f"Deploying service {self.name}...")
            self.git_client.clone()
            self.git_client.pull()
            self.docker_service.restart_service()
            logger.info(f"Service {self.name} deployed successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to deploy service {self.name}: {e}")
            return False

    def rollback(self, version: str) -> bool:
        """Rollback the service to a previous version."""
        try:
            logger.info(f"Rolling back service {self.name} to version {version}...")
            self.git_client.checkout(version)
            self.docker_service.restart_service()
            logger.info(f"Service {self.name} rolled back to version {version}.")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback service {self.name}: {e}")
            return False

class ServiceManager:
    def __init__(self):
        self.services: Dict[str, Service] = {}
        self.proxy_client = ProxyClient()

    def register_service(self, name: str) -> bool:
        """Register a new service with the given name."""
        if name in self.services:
            logger.warning(f"Service {name} is already registered.")
            return False
        
        try:
            service = Service(name, self.proxy_client)
            self.services[name] = service
            logger.info(f"Service {name} registered successfully.")
            return True
        
        except Exception as e:
            raise Exception(f"Failed to register service {name}: {e}")

    def deploy_service(self, name: str) -> bool:
        """Deploy the service with the given name."""
        if name not in self.services:
            raise Exception(f"Service {name} is not registered.")
        
        return self.services[name].deploy()

    def rollback_service(self, name: str, version: str) -> bool:
        """Rollback the service to a specific version."""
        if name not in self.services:
            raise Exception(f"Service {name} is not registered.")
        
        return self.services[name].rollback(version)

# Global service manager instance
service_manager = ServiceManager()

def main():
    logger.info("Starting scheduler...")

    gitserver_client = GitWsClient(('localhost', 8000))
    gitserver_client.on_deploy(service_manager.deploy_service)
    gitserver_client.on_rollback(service_manager.rollback_service)
    gitserver_client.on_register(service_manager.register_service)

    logger.info("Git server client initialized and event handlers registered.")

    gitserver_client.start()

if __name__ == "__main__":
    main()