# src/services/health_monitor.py
"""
Health Monitor Service
Monitors health of all registered MCP servers
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status information"""
    server_name: str
    healthy: bool
    last_check: datetime
    response_time: float
    consecutive_failures: int
    last_error: Optional[str] = None


class HealthMonitor:
    """Monitors health of MCP servers"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.health_status: Dict[str, HealthStatus] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start_monitoring(self):
        """Start health monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_servers()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _check_all_servers(self):
        """Check health of all registered servers"""
        from ..core.registry import get_registry
        
        registry = get_registry()
        servers = registry.list_servers()
        
        for server in servers:
            await self._check_server_health(server)
    
    async def _check_server_health(self, server):
        """Check health of individual server"""
        start_time = datetime.utcnow()
        
        try:
            # Simple ping test
            if hasattr(server.client, 'connected') and server.client.connected:
                # Try to list tools as a health check
                await server.client.request("tools/list", {})
                
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                self.health_status[server.name] = HealthStatus(
                    server_name=server.name,
                    healthy=True,
                    last_check=datetime.utcnow(),
                    response_time=response_time,
                    consecutive_failures=0
                )
            else:
                self._record_failure(server.name, "Not connected")
                
        except Exception as e:
            self._record_failure(server.name, str(e))
    
    def _record_failure(self, server_name: str, error: str):
        """Record health check failure"""
        current_status = self.health_status.get(server_name)
        consecutive_failures = current_status.consecutive_failures + 1 if current_status else 1
        
        self.health_status[server_name] = HealthStatus(
            server_name=server_name,
            healthy=False,
            last_check=datetime.utcnow(),
            response_time=0.0,
            consecutive_failures=consecutive_failures,
            last_error=error
        )
        
        logger.warning(f"Health check failed for {server_name}: {error}")
    
    def get_health_status(self, server_name: str) -> Optional[HealthStatus]:
        """Get health status for specific server"""
        return self.health_status.get(server_name)
    
    def get_all_health_status(self) -> Dict[str, HealthStatus]:
        """Get health status for all servers"""
        return self.health_status.copy()
    
    def is_server_healthy(self, server_name: str) -> bool:
        """Check if server is healthy"""
        status = self.health_status.get(server_name)
        return status.healthy if status else False


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
