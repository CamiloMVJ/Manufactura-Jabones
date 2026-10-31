from typing import List, Dict, Any
from fastapi import WebSocket
from datetime import datetime
import json

class ConnectionManager:
    """Gestiona las conexiones WebSocket activas."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, accepted: bool = False):
        if not accepted:
            await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Envía notificación a todos los usuarios conectados."""
        message = {
            "type": event_type,
            "payload": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        # Iteramos sobre una copia para evitar errores si alguien se desconecta
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

# --- ESTA ES LA LÍNEA QUE FALTABA ---
manager = ConnectionManager()

