import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.core.events import manager
from app.core.security import get_current_user
from app.db.database import SessionLocal

# Esta instancia de 'router' es necesaria para que main.py pueda incluirla
router = APIRouter()

@router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Autenticación en el primer mensaje: el token no queda en la URL ni en logs.
        token = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        with SessionLocal() as db:
            await get_current_user(token=token, db=db)
        await manager.connect(websocket, accepted=True)
        await websocket.send_json({"type": "CONNECTED", "payload": {}})
        while True:
            # Mantiene la conexión viva esperando mensajes (aunque no hagamos nada con ellos)
            await websocket.receive_text()
    except (HTTPException, asyncio.TimeoutError):
        await websocket.close(code=1008)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

