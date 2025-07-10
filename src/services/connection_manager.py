# src/services/connection_manager.py
"""
Connection Manager Service
Manages connections to MCP servers with pooling and retry logic
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Connection information"""
    server_name: str
    connected: bool
    connection_time: datetime
    last_activity: datetime
    request_count: int
    error_count: int


class ConnectionManager:
    """Manages MCP server connections"""
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self.connections: Dict[str, ConnectionInfo] = {}
        self.connection_pool: Dict[str, Any] = {}  # Actual connection objects
        self.connection_lock = asyncio.Lock()
    
    async def get_connection(self, server_name: str):
        """Get connection for server"""
        async with self.connection_lock:
            if server_name in self.connection_pool:
                conn_info = self.connections[server_name]
                conn_info.last_activity = datetime.utcnow()
                conn_info.request_count += 1
                return self.connection_pool[server_name]
            
            return None
    
    async def add_connection(self, server_name: str, connection: Any):
        """Add new connection to pool"""
        async with self.connection_lock:
            self.connection_pool[server_name] = connection
            self.connections[server_name] = ConnectionInfo(
                server_name=server_name,
                connected=True,
                connection_time=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                request_count=0,
                error_count=0
            )
            logger.info(f"Added connection for {server_name}")
    
    async def remove_connection(self, server_name: str):
        """Remove connection from pool"""
        async with self.connection_lock:
            if server_name in self.connection_pool:
                del self.connection_pool[server_name]
            
            if server_name in self.connections:
                del self.connections[server_name]
            
            logger.info(f"Removed connection for {server_name}")
    
    async def cleanup_idle_connections(self, idle_timeout: int = 300):
        """Clean up idle connections"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=idle_timeout)
        
        async with self.connection_lock:
            idle_servers = [
                name for name, info in self.connections.items()
                if info.last_activity < cutoff_time
            ]
            
            for server_name in idle_servers:
                await self.remove_connection(server_name)
                logger.info(f"Cleaned up idle connection: {server_name}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.connections),
            "max_connections": self.max_connections,
            "connections": {
                name: {
                    "connected": info.connected,
                    "connection_time": info.connection_time.isoformat(),
                    "last_activity": info.last_activity.isoformat(),
                    "request_count": info.request_count,
                    "error_count": info.error_count
                }
                for name, info in self.connections.items()
            }
        }


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager