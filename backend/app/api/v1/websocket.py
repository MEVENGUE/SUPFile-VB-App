"""
WebSocket endpoints for real-time synchronization
"""
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token

logger = logging.getLogger(__name__)

# Store active connections: {user_id: Set[WebSocket]}
active_connections: Dict[int, Set[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Add a new WebSocket connection"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected. Remaining connections: {len(self.active_connections.get(user_id, set()))}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast_to_user(self, message: dict, user_id: int):
        """Broadcast message to all connections of a user"""
        await self.send_personal_message(message, user_id)


manager = ConnectionManager()


async def get_user_id_from_websocket(websocket: WebSocket) -> int:
    """Extract user ID from WebSocket query parameters or headers"""
    # Try to get token from query params
    token = websocket.query_params.get("token")
    if not token:
        raise ValueError("No authentication token provided")
    
    try:
        payload = verify_token(token, token_type="access")
        if payload is None:
            raise ValueError("Invalid or expired token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")
        
        return int(user_id)
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")


async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time file synchronization
    Usage: ws://host/api/v1/ws?token=JWT_TOKEN
    """
    user_id = None
    try:
        # Authenticate user
        user_id = await get_user_id_from_websocket(websocket)
        await manager.connect(websocket, user_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping/pong for keepalive
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "subscribe":
                    # User can subscribe to specific events
                    await websocket.send_json({
                        "type": "subscribed",
                        "events": message.get("events", [])
                    })
                else:
                    # Echo back unknown messages
                    await websocket.send_json({
                        "type": "echo",
                        "message": message
                    })
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
    except ValueError as e:
        logger.error(f"Authentication failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        if user_id:
            manager.disconnect(websocket, user_id)


# Helper functions to send notifications
async def notify_file_created(user_id: int, file_data: dict):
    """Notify user about a new file"""
    await manager.broadcast_to_user({
        "type": "file_created",
        "data": file_data
    }, user_id)


async def notify_file_updated(user_id: int, file_data: dict):
    """Notify user about a file update"""
    await manager.broadcast_to_user({
        "type": "file_updated",
        "data": file_data
    }, user_id)


async def notify_file_deleted(user_id: int, file_id: int):
    """Notify user about a file deletion"""
    await manager.broadcast_to_user({
        "type": "file_deleted",
        "data": {"file_id": file_id}
    }, user_id)


async def notify_folder_created(user_id: int, folder_data: dict):
    """Notify user about a new folder"""
    await manager.broadcast_to_user({
        "type": "folder_created",
        "data": folder_data
    }, user_id)


async def notify_folder_updated(user_id: int, folder_data: dict):
    """Notify user about a folder update"""
    await manager.broadcast_to_user({
        "type": "folder_updated",
        "data": folder_data
    }, user_id)


async def notify_folder_deleted(user_id: int, folder_id: int):
    """Notify user about a folder deletion"""
    await manager.broadcast_to_user({
        "type": "folder_deleted",
        "data": {"folder_id": folder_id}
    }, user_id)

