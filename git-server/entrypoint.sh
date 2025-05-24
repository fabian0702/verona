#!/bin/bash

# Setup hooks
echo "Setting up git hooks..."
python setup.py

echo "Starting git server..."
# Start git server and python server
uvicorn main:app &
# Start git daemon with store as the base path
git daemon --base-path=./store --export-all --reuseaddr --informative-errors --verbose --enable=receive-pack --detach &

# Wait for servers to finsih
wait