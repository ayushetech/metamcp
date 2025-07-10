# src/api/admin.py
"""
Admin API for Meta MCP Server Management
Provides REST endpoints for managing MCP servers, health monitoring, and configuration
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging

from ..core.registry import get_registry, McpServerRegistration, TransportType
from ..core.router import get_router, RoutingRule, RoutingStrategy
from ..services.health_monitor import get_health_monitor
from ..services.connection_manager import get_connection_manager
from ..services.tool_aggregator import get_tool_aggregator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# Server Management Endpoints
@router.post("/servers/register")
async def register_server(registration: McpServerRegistration):
    """Register a new MCP server"""
    try:
        registry = get_registry()
        server_id = await registry.register_server(registration)
        
        return {
            "status": "success",
            "server_id": server_id,
            "message": f"Registered server: {registration.name}"
        }
    except Exception as e:
        logger.error(f"Failed to register server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/servers")
async def list_servers():
    """List all registered servers"""
    try:
        registry = get_registry()
        servers = registry.list_servers()
        
        return {
            "status": "success",
            "servers": [
                {
                    "id": server.id,
                    "name": server.name,
                    "status": server.status.value,
                    "transport_type": server.registration.transport_type.value,
                    "tools_count": len(server.tools),
                    "resources_count": len(server.resources),
                    "prompts_count": len(server.prompts),
                    "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None
                }
                for server in servers
            ],
            "total_count": len(servers)
        }
    except Exception as e:
        logger.error(f"Failed to list servers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    """Get detailed information about a specific server"""
    try:
        registry = get_registry()
        server = registry.get_server(server_id)
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server not found: {server_id}"
            )
        
        return {
            "status": "success",
            "server": {
                "id": server.id,
                "name": server.name,
                "status": server.status.value,
                "registration": server.registration.__dict__,
                "tools": server.tools,
                "resources": server.resources,
                "prompts": server.prompts,
                "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None,
                "health_check_failures": server.health_check_failures
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/servers/{server_id}/connect")
async def connect_server(server_id: str, background_tasks: BackgroundTasks):
    """Connect to a registered server"""
    try:
        registry = get_registry()
        
        def connect_task():
            asyncio.create_task(registry.connect_server(server_id))
        
        background_tasks.add_task(connect_task)
        
        return {
            "status": "success",
            "message": f"Connection initiated for server {server_id}"
        }
    except Exception as e:
        logger.error(f"Failed to connect server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/servers/{server_id}/disconnect")
async def disconnect_server(server_id: str):
    """Disconnect from a server"""
    try:
        registry = get_registry()
        success = await registry.disconnect_server(server_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Disconnected from server {server_id}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to disconnect from server {server_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/servers/{server_id}")
async def unregister_server(server_id: str):
    """Unregister a server"""
    try:
        registry = get_registry()
        success = await registry.unregister_server(server_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Unregistered server {server_id}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server not found: {server_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Health Monitoring Endpoints
@router.get("/health/servers")
async def get_all_server_health():
    """Get health status of all servers"""
    try:
        health_monitor = get_health_monitor()
        health_status = health_monitor.get_all_health_status()
        
        return {
            "status": "success",
            "health_status": {
                name: {
                    "healthy": status.healthy,
                    "last_check": status.last_check.isoformat(),
                    "response_time": status.response_time,
                    "consecutive_failures": status.consecutive_failures,
                    "last_error": status.last_error
                }
                for name, status in health_status.items()
            },
            "summary": {
                "total_servers": len(health_status),
                "healthy_servers": sum(1 for s in health_status.values() if s.healthy),
                "unhealthy_servers": sum(1 for s in health_status.values() if not s.healthy)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health/servers/{server_name}")
async def get_server_health(server_name: str):
    """Get health status of specific server"""
    try:
        health_monitor = get_health_monitor()
        health_status = health_monitor.get_health_status(server_name)
        
        if not health_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No health data found for server: {server_name}"
            )
        
        return {
            "status": "success",
            "server_name": server_name,
            "health_status": {
                "healthy": health_status.healthy,
                "last_check": health_status.last_check.isoformat(),
                "response_time": health_status.response_time,
                "consecutive_failures": health_status.consecutive_failures,
                "last_error": health_status.last_error
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get health status for {server_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Tool Management Endpoints
@router.get("/tools")
async def list_all_tools():
    """List all tools from all servers"""
    try:
        tool_aggregator = get_tool_aggregator()
        tools = tool_aggregator.get_all_tools()
        
        return {
            "status": "success",
            "tools": [
                {
                    "name": tool.name,
                    "full_name": tool.full_name,
                    "description": tool.description,
                    "server_name": tool.server_name,
                    "namespace": tool.namespace,
                    "input_schema": tool.input_schema,
                    "last_updated": tool.last_updated.isoformat()
                }
                for tool in tools
            ],
            "total_count": len(tools)
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tools/search")
async def search_tools(query: str, limit: int = 10):
    """Search tools by name or description"""
    try:
        tool_aggregator = get_tool_aggregator()
        tools = tool_aggregator.search_tools(query, limit)
        
        return {
            "status": "success",
            "query": query,
            "tools": [
                {
                    "name": tool.name,
                    "full_name": tool.full_name,
                    "description": tool.description,
                    "server_name": tool.server_name
                }
                for tool in tools
            ],
            "result_count": len(tools)
        }
    except Exception as e:
        logger.error(f"Failed to search tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tools/stats")
async def get_tool_stats():
    """Get tool usage statistics"""
    try:
        tool_aggregator = get_tool_aggregator()
        stats = tool_aggregator.get_aggregation_stats()
        popular_tools = tool_aggregator.get_popular_tools(10)
        
        return {
            "status": "success",
            "aggregation_stats": stats,
            "popular_tools": [
                {
                    "tool_name": name,
                    "call_count": stats.call_count,
                    "success_rate": stats.success_count / stats.call_count if stats.call_count > 0 else 0,
                    "avg_response_time": stats.avg_response_time,
                    "last_used": stats.last_used.isoformat() if stats.last_used else None
                }
                for name, stats in popular_tools
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get tool stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Routing Management Endpoints
@router.get("/routing/rules")
async def get_routing_rules():
    """Get all routing rules"""
    try:
        router_service = get_router()
        stats = router_service.get_routing_stats()
        
        return {
            "status": "success",
            "routing_stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get routing rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/routing/test")
async def test_routing(request_text: str, available_servers: List[str] = None):
    """Test routing analysis for a request"""
    try:
        router_service = get_router()
        
        if available_servers is None:
            registry = get_registry()
            active_servers = registry.list_active_servers()
            available_servers = [server.name for server in active_servers]
        
        decision = await router_service.route_request(
            request_text, 
            available_servers,
            {"request_id": "test"}
        )
        
        return {
            "status": "success",
            "request_text": request_text,
            "routing_decision": {
                "matched_servers": decision.matched_servers,
                "strategy": decision.strategy.value,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "matched_rules": decision.matched_rules,
                "fallback_servers": decision.fallback_servers
            }
        }
    except Exception as e:
        logger.error(f"Failed to test routing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# System Management Endpoints
@router.get("/system/stats")
async def get_system_stats():
    """Get overall system statistics"""
    try:
        registry = get_registry()
        health_monitor = get_health_monitor()
        connection_manager = get_connection_manager()
        tool_aggregator = get_tool_aggregator()
        router_service = get_router()
        
        registry_stats = await registry.get_registry_stats()
        health_stats = health_monitor.get_all_health_status()
        connection_stats = connection_manager.get_connection_stats()
        tool_stats = tool_aggregator.get_aggregation_stats()
        routing_stats = router_service.get_routing_stats()
        
        return {
            "status": "success",
            "system_stats": {
                "registry": registry_stats,
                "health": {
                    "total_monitored": len(health_stats),
                    "healthy_count": sum(1 for s in health_stats.values() if s.healthy),
                    "unhealthy_count": sum(1 for s in health_stats.values() if not s.healthy)
                },
                "connections": connection_stats,
                "tools": tool_stats,
                "routing": routing_stats
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/system/maintenance")
async def perform_maintenance():
    """Perform system maintenance tasks"""
    try:
        connection_manager = get_connection_manager()
        
        # Clean up idle connections
        await connection_manager.cleanup_idle_connections()
        
        return {
            "status": "success",
            "message": "Maintenance tasks completed",
            "tasks_performed": [
                "Cleaned up idle connections"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to perform maintenance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
