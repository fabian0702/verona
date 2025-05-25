
from subprocess import check_output, CalledProcessError
from urllib.parse import urljoin
import os

REPO_PATH = os.environ.get('REPO_PATH', './')

class GitClient:
    def __init__(self, service: str, repo_url:str, clone: bool = True):
        self.repo_path = os.path.join(os.getcwd(), service+'.git')
        self.repo_url = urljoin(repo_url, service)
        if clone:
            self.clone(self.repo_url)

    def clone(self):
        """
        Clone a Git repository from the given URL to the specified path.
        """
        try:
            check_output(['git', 'clone', self.repo_url, self.repo_path])
            print(f"Successfully cloned {self.repo_url} to {self.repo_path}.")
        except CalledProcessError as e:
            print("git clone failed:", e)

    def pull_latest(self):
        """
        Pull the latest changes from the remote repository.
        """
        try:
            check_output(['git', 'pull'], cwd=self.repo_path)
            print("Successfully pulled the latest changes.")
        except CalledProcessError as e:
            print("git pull failed:", e)

    def reset(self):
        """
        Reset the local repository to match the remote repository.
        """
        try:
            check_output(['git', 'reset', '--hard'], cwd=self.repo_path)
            print("Successfully reset the repository.")
        except CalledProcessError as e:
            print("git reset failed:", e)

    def checkout(self, commit: str):
        """
        Checkout a specific branch in the local repository.
        """
        try:
            check_output(['git', 'checkout', commit], cwd=self.repo_path)
            print(f"Successfully checked out commit {commit}.")
        except CalledProcessError as e:
            print(f"git checkout {commit} failed:", e)

if __name__ == "__main__":
    # Example usage
    service_name = "example_service"
    repo_url = "git://github.com/username/repo.git"
    git_client = GitClient(service_name, repo_url)
    git_client.pull_latest()