import os
from os.path import join, isfile
import subprocess

services_dir = "./services"
git_store = "./store"
service_file = join(services_dir, "service.txt")
report_server = 'http://localhost:8000/git_hook/'

# Setting git username and email
subprocess.run(["git", "config", "--global", "user.name", "Verona Git"])
subprocess.run(["git", "config", "--global", "user.email", "verona@mntain.ch"])

for service in os.listdir(services_dir):
    r_path = join(services_dir, service)
    if isfile(r_path):
        # Probably not a service
        continue

    # Init bare git repo
    bare_repo = join(git_store, f"{service}.git")
    subprocess.run(["git", "init", r_path])
    subprocess.run(["git", "add", "."], cwd=r_path)
    subprocess.run(["git", "commit", "-m", "Initial Commit (script)"], cwd=r_path)
    subprocess.run(["git", "clone", "--bare", r_path, bare_repo])

    # Add hooking
    hook_dir = join(bare_repo, "hooks") 
    os.makedirs(hook_dir, exist_ok=True)
    hook_file = join(hook_dir, "post-receive")
    with open(hook_file, "w+") as file:
        file.write(f"#!/bin/sh\ncurl {report_server}{service}\n")
    
    os.chmod(hook_file, 0o775)

    # Registering the service in the file
    with open(service_file, "a+") as file:
        file.write(f"{service}\n")

    
    

