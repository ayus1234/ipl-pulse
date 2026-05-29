"""WebSocket connection management."""

from fastapi import WebSocket
from typing import Dict, List, Set
import asyncio


class WebSocketManager:
    """Manages WebSocket connections and connection pools per match."""
    
    def __init__(self):
        # Match ID to Set of WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket to Match ID mapping for quick lookup on disconnect
        self.connection_to_match: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, match_id: str):
        """Connect a user to a specific match room."""
        await websocket.accept()
        
        if match_id not in self.active_connections:
            self.active_connections[match_id] = set()
            
        self.active_connections[match_id].add(websocket)
        self.connection_to_match[websocket] = match_id

    def disconnect(self, websocket: WebSocket):
        """Disconnect a user and remove from the pool."""
        match_id = self.connection_to_match.get(websocket)
        if match_id:
            if match_id in self.active_connections:
                self.active_connections[match_id].discard(websocket)
                if not self.active_connections[match_id]:
                    del self.active_connections[match_id]
            del self.connection_to_match[websocket]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client."""
        await websocket.send_json(message)

    async def broadcast_to_match(self, message: dict, match_id: str):
        """Broadcast a message to all clients in a match room."""
        if match_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[match_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.add(connection)
            
            for dead in dead_connections:
                self.disconnect(dead)

    async def heartbeat(self):
        """Send a ping/heartbeat to all connected clients every 30 seconds."""
        while True:
            await asyncio.sleep(30)
            ping_message = {"type": "ping", "timestamp": asyncio.get_event_loop().time()}
            
            for match_id, connections in list(self.active_connections.items()):
                dead_connections = set()
                for connection in connections:
                    try:
                        await connection.send_json(ping_message)
                    except Exception:
                        dead_connections.add(connection)
                        
                for dead in dead_connections:
                    self.disconnect(dead)
