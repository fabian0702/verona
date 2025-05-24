# Use an official Python image as the base
FROM python:3.12-slim

# Install Git
RUN apt-get update && apt-get install -y git curl && apt-get clean

# Set the working directory in the container
WORKDIR /app

# Copy the setup.py and other necessary files into the container
COPY setup.py /app/
COPY . /app/

# Install the Python package
RUN pip install -r requirements.txt

# Expose a port for the Git server (default Git port is 9418)
EXPOSE 9418

# Start script
RUN chmod +x entrypoint.sh