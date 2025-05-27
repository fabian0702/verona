import os
import yaml
import json

from python_on_whales import DockerClient

from scheduler.log import logger


COMPOSE_FILE_NAMES = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']

class File:
    @staticmethod
    def search_compose_file(file_path:str) -> str:
        """
        Search for the Docker Compose file in the current directory.
        :return: The path to the Docker Compose file.
        """
        import os
        for root, _, files in os.walk(file_path):
            for filename in COMPOSE_FILE_NAMES:
                if filename in files:
                    return os.path.join(root, filename)
        raise FileNotFoundError("Docker Compose file not found.")


    @staticmethod
    def rewrite_compose_file(compose_file:str):
        """
        Rewrite the Docker Compose file with new content.
        :param new_content: The new content to write to the Docker Compose file.
        """
        client = DockerClient(compose_files=[compose_file])

        config = client.compose.config(return_json=True)

        for name, service in config['services'].items():
            if 'ports' in service:
                ports = service['ports']
                
                labels = service.get('labels', {})

                labels.update({'ports_config':json.dumps(ports)})

                service['labels'] = labels

                service['ports'] = []
                
        rewritten_compose_file = os.path.join(os.path.dirname(compose_file), 'docker-compose_rewritten.yaml')

        with open(rewritten_compose_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Rewritten {compose_file} with new content.")
        return rewritten_compose_file