import os
from os.path import join, isfile
import subprocess

services_dir = "./services"
git_store = "./store"
report_server = 'http://localhost:8000/git_hook/'

for service in os.listdir(services_dir):
    r_path = join(services_dir, service)
    if isfile(r_path):
        # Probably not a service
        continue

    # Init bare git repo
    bare_repo = join(git_store, f"{service}.git")
    subprocess.run(["git", "init", "--bare", f"--template={r_path}", bare_repo])

    # Add hooking
    hook_dir = join(bare_repo, "hooks") 
    os.makedirs(hook_dir)
    hook_file = join(hook_dir, "post-receive")
    with open(hook_file, "w+") as file:
        file.write(f"#!/bin/sh\ncurl {report_server}{service}\n")
    
    os.chmod(hook_file, 0o775)

    
    

