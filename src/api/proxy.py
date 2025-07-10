# src/api/proxy.py
"""
MCP Proxy API
Provides MCP protocol endpoints for external clients
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging
import uuid

from ..mcp.server import McpServer
from ..core.registry import get_registry
from ..services.tool_aggregator import get_tool_aggregator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP Proxy"])


# Create Meta MCP server instance
meta_mcp_server = McpServer("Meta MCP Server", "1.0.0")


async def setup_meta_server_tools():
    """Setup tools for the Meta MCP server"""
    from ..main import (
        list_registered_servers, register_mcp_server, connect_to_server,
        list_all_tools, call_tool_on_server, intelligent_tool_routing,
        get_server_health
    )
    
    # Register Meta MCP tools
    tools_to_register = [
        ("list_registered_servers", "List all registered MCP servers", list_registered_servers),
        ("register_mcp_server", "Register a new MCP server", register_mcp_server),
        ("connect_to_server", "Connect to a registered server", connect_to_server),
        ("list_all_tools", "List all available tools", list_all_tools),
        ("call_tool_on_server", "Call a tool on a specific server", call_tool_on_server),
        ("intelligent_tool_routing", "Analyze request for intelligent routing", intelligent_tool_routing),
        ("get_server_health", "Get health status of servers", get_server_health)
    ]
    
    for tool_name, description, handler in tools_to_register:
        from ..mcp.protocol import McpTool
        
        tool = McpTool(
            name=tool_name,
            description=description,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        meta_mcp_server.add_tool(tool, handler)


@router.post("/")
async def handle_mcp_request(request: Request):
    """Handle MCP protocol requests"""
    try:
        message_data = await request.json()
        
        # Ensure Meta MCP server is set up
        if not meta_mcp_server.tools:
            await setup_meta_server_tools()
        
        # Handle the MCP message
        response = await meta_mcp_server.handle_message(message_data)
        
        return response
        
    except Exception as e:
        logger.error(f"MCP request handling error: {e}")
        
        # Return MCP error response
        return {
            "jsonrpc": "2.0",
            "id": message_data.get("id") if 'message_data' in locals() else None,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        }


@router.get("/health")
async def mcp_health_check():
    """MCP-specific health check"""
    try:
        registry = get_registry()
        stats = await registry.get_registry_stats()
        
        return {
            "status": "healthy",
            "server_name": "Meta MCP Server",
            "version": "1.0.0",
            "protocol_version": "2024-11-05",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"MCP health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/capabilities")
async def get_mcp_capabilities():
    """Get MCP server capabilities"""
    return {
        "capabilities": meta_mcp_server.capabilities,
        "server_info": meta_mcp_server.get_server_info()
    }