from fastapi import FastAPI, WebSocket

app = FastAPI()


pool: list[WebSocket] = []

@app.websocket("/subscribe_to_updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to subscribe to updates.
    Clients can connect to this endpoint to receive real-time updates.
    """
    await websocket.accept()
    pool.append(websocket)
    
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
            await websocket.send_json({"service": service_name, "message": "Repository updated"})
        except Exception as e:
            print(f"Error sending message: {e}")
    
    return {"message": f"Git hook triggered for service: {service_name}"}