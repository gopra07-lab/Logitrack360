from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
import math
from datetime import datetime

app = FastAPI()

truck_data = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

class LocationData(BaseModel):
    truck_id: str
    latitude: float
    longitude: float
    engine_temp: float

WAREHOUSE = {"lat": 28.6139, "lon": 77.2090}
RADIUS_KM = 5

def is_inside_geofence(lat, lon):
    distance = math.sqrt(
        (lat - WAREHOUSE["lat"])**2 +
        (lon - WAREHOUSE["lon"])**2
    ) * 111
    return distance <= RADIUS_KM

def check_alerts(data: LocationData):
    alerts = []

    if not is_inside_geofence(data.latitude, data.longitude):
        alerts.append("GEOFENCE_VIOLATION")

    if data.engine_temp > 100:
        alerts.append("HIGH_ENGINE_TEMPERATURE")

    return alerts

@app.post("/location")
async def receive_location(data: LocationData):
    entry = {
        "truck_id": data.truck_id,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "engine_temp": data.engine_temp,
        "timestamp": str(datetime.utcnow())
    }

    truck_data.append(entry)

    alerts = check_alerts(data)

    response = {
        "truck_id": data.truck_id,
        "location": [data.latitude, data.longitude],
        "alerts": alerts
    }

    await manager.broadcast(response)

    return {
        "status": "success",
        "data": response
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def home():
    return {
        "message": "LogiTrack 360 Running 🚚",
        "total_records": len(truck_data)
    }
