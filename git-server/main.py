from fastapi import FastAPI, WebSocket
import os

app = FastAPI()


pool: list[WebSocket] = []
service_dir = "./services"
service_file = os.path.join(service_dir, "service.txt")


def get_services():
    """
    Function to get the list of services from the services directory.
    Each service is expected to have a directory with its name.
    """
    with open(service_file, "r") as file:
        services = [line.strip() for line in file if line.strip()]
    return services


@app.websocket("/subscribe_to_updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to subscribe to updates.
    Clients can connect to this endpoint to receive real-time updates.
    """
    await websocket.accept()
    pool.append(websocket)

    await websocket.send_json({"message": "Connected to WebSocket", "services": get_services()})
    
    try:
        while True:
            # Keep the connection open
            await websocket.receive_text()
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        pool.remove(websocket)



@app.get("/git_hook/{service_name}")
async def git_hook(service_name: str):
    """
    Git hook endpoint that gets called when a push is made to the repository.
    This endpoint can be used to trigger actions or notify clients.
    """
    print(f"Git hook triggered for service: {service_name}")
    
    # Notify all connected WebSocket clients about the update
    for websocket in pool:
        try:
            await websocket.send_json({"service": service_name, "message": "Repository updated", "action": "deploy"})
        except Exception as e:
            print(f"Error sending message: {e}")
    
    return {"message": f"Git hook triggered for service: {service_name}"}


@app.post("/rollback/{service_name}/{version}")
async def rollback(service_name: str, version: str):
    """
    Endpoint to handle rollbacks for a specific service.
    This endpoint can be used to revert the service to a previous version.
    """
    print(f"Rollback requested for service: {service_name}, version: {version}")
    
    for websocket in pool:
        try:
            await websocket.send_json({"service": service_name, "message": f"Rollback to version {version} requested", "action": "rollback", "version": version})
        except Exception as e:
            print(f"Error sending message: {e}")

    # Here you would implement the logic to perform the rollback
    # For now, we just simulate a successful rollback
    return {"message": f"Rollback for service {service_name} to version {version} successful"}