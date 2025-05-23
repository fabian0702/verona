import os
from os.path import join, isfile
import subprocess

services_dir = "./services"
git_store = "./store"


for service in os.listdir(services_dir):
    r_path = join(services_dir, service)
    if isfile(r_path):
        # Probably not a service
        continue

    # Init bare git repo
    bare_repo = join(git_store, "{service}.git")
    subprocess.run(["git", "init", "--bare", f"--template={r_path}", bare_repo])

    # Add hooking
    hook_dir = join(bare_repo, "hooks") 
    os.makedirs(hook_dir)
    with open(join(hook_dir, "post-receive"), "w+") as file:
        file.write("#!/bin/sh\necho 1")
    

