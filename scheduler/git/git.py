
from subprocess import check_output, CalledProcessError, STDOUT
from urllib.parse import urljoin
import os
from typing import Optional


REPO_PATH = os.environ.get('REPO_PATH', './')

class GitClient:
    def __init__(self, service: str, repo_url:str, clone: bool = True):
        """
        Initialize the Git client for a specific service.
        :param service: The name of the service (used as the directory name).
        :param repo_url: The URL of the Git repository.
        :param clone: Whether to clone the repository if it does not exist.
        """

        print(f"Initializing GitClient for service: {service} with repo URL: {repo_url}")

        self.repo_path = os.path.join(REPO_PATH, service)
        self.repo_url = os.path.join(repo_url, service+'.git')

        if clone:
            self.clone()


    def _run_command(self, command: list[str], cwd: Optional[str] = None) -> tuple[bool, str]:
        """
        Run a git command and return success status and output.
        """

        try:
            cwd = cwd or self.repo_path
            if not os.path.exists(cwd):
                return False, f"Directory {cwd} does not exist"
            
            output = check_output(command, cwd=cwd, stderr=STDOUT, text=True).strip()
            return True, output
        except CalledProcessError as e:
            error_msg = e.output.strip() if e.output else str(e)
            print(f"Git command failed: {' '.join(command)}\n{error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error running git command: {str(e)}"
            print(error_msg)
            return False, error_msg


    def _ensure_repo_exists(self) -> bool:
        """
        Ensure the repository directory exists.
        """

        if not os.path.exists(self.repo_path):
            print(f"Repository not found at {self.repo_path}. Try cloning first.")
            return False
        return True


    def clone(self) -> tuple[bool, Optional[str]]:
        """
        Clone the repository if it does not exist.
        """
        if os.path.exists(self.repo_path):
            print(f"Repository already exists at {self.repo_path}.")
            self.pull()
            return True, None
        
        os.makedirs(REPO_PATH, exist_ok=True)
        
        service_name = os.path.basename(self.repo_path)

        print(self.repo_url)
        
        success, output = self._run_command(
            ['git', 'clone', self.repo_url, service_name], 
            cwd=REPO_PATH
        )
        
        if success:
            print(f"Successfully cloned repository from {self.repo_url} to {self.repo_path}")
        else:
            print(f"Failed to clone repository from {self.repo_url}")
        
        return success, output


    def pull(self) -> tuple[bool, Optional[str]]:
        """
        Pull the latest changes from the remote repository.
        """

        if not self._ensure_repo_exists():
            return False, None
        
        success, output = self._run_command(['git', 'pull'])
        if success:
            print("Successfully pulled latest changes")
        return success, output


    def reset(self) -> tuple[bool, Optional[str]]:
        """
        Reset the local repository to match the remote repository.
        """

        if not self._ensure_repo_exists():
            return False, None
        
        success, _ = self._run_command(['git', 'fetch', '--all'])
        if not success:
            print("Failed to fetch all branches")
            return False, None

        success, output = self._run_command(['git', 'reset', '--hard'])
        if success:
            print("Successfully reset repository")
        return success, output


    def checkout(self, commit: str) -> tuple[bool, Optional[str]]:
        """
        Checkout a specific commit/branch in the local repository.
        """

        if not self._ensure_repo_exists():
            return False, None
        
        success, output = self._run_command(['git', 'checkout', commit])
        if success:
            print(f"Successfully checked out {commit}")
        return success, output


if __name__ == "__main__":
    # Example usage
    service_name = "example_service"
    repo_url = "git://github.com/username/repo.git"
    git_client = GitClient(service_name, repo_url)
    git_client.pull()