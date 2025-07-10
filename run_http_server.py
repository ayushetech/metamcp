#!/usr/bin/env python3
"""
Run Meta MCP with HTTP endpoints for Postman testing
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# Import the main server
from main import MetaMCPServer

# Try to import admin/proxy routers, but don't fail if they have issues
admin_router = None
proxy_router = None

try:
    from api.admin import router as admin_router
    logging.info("✅ Admin router imported successfully")
except Exception as e:
    logging.warning(f"⚠️ Could not import admin router: {e}")

try:
    from api.proxy import router as proxy_router  
    logging.info("✅ Proxy router imported successfully")
except Exception as e:
    logging.warning(f"⚠️ Could not import proxy router: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Meta MCP HTTP Server",
    description="HTTP endpoints for Meta MCP orchestration server",
    version="1.0.0"
)

# Global Meta MCP server instance
meta_server = None

@app.on_event("startup")
async def startup_event():
    """Initialize Meta MCP server on startup"""
    global meta_server
    logger.info("🚀 Starting Meta MCP HTTP Server...")
    
    meta_server = MetaMCPServer()
    await meta_server.initialize()
    
    logger.info("✅ Meta MCP Server initialized and ready for HTTP requests")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global meta_server
    if meta_server:
        await meta_server.shutdown()
    logger.info("👋 Meta MCP Server shutdown complete")

# Health endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    if not meta_server:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Server not initialized"}
        )
    
    try:
        stats = await meta_server.registry.get_registry_stats()
        return {
            "status": "healthy",
            "server": "Meta MCP",
            "version": "1.0.0",
            "timestamp": "2025-07-07T13:25:00Z",
            "stats": stats
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# MCP Protocol endpoint
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests"""
    if not meta_server:
        return JSONResponse(
            status_code=503,
            content={"error": "Server not initialized"}
        )
    
    try:
        message_data = await request.json()
        response = await meta_server.server.handle_message(message_data)
        return response or {}
    except Exception as e:
        logger.error(f"MCP request error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": message_data.get("id") if 'message_data' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
        )

# MCP Health endpoint
@app.get("/mcp/health")
async def mcp_health():
    """MCP-specific health check"""
    if not meta_server:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Server not initialized"}
        )
    
    try:
        stats = await meta_server.registry.get_registry_stats()
        return {
            "status": "healthy",
            "server_name": "Meta MCP Server",
            "version": "1.0.0",
            "protocol_version": "2024-11-05",
            "stats": stats
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Include admin and proxy routers only if they imported successfully
if admin_router:
    try:
        app.include_router(admin_router)
        logger.info("✅ Admin router included")
    except Exception as e:
        logger.warning(f"⚠️ Could not include admin router: {e}")

if proxy_router:
    try:
        app.include_router(proxy_router)
        logger.info("✅ Proxy router included")
    except Exception as e:
        logger.warning(f"⚠️ Could not include proxy router: {e}")

# Create simplified admin endpoints for basic testing
@app.get("/admin/servers")
async def list_servers():
    """List all registered servers"""
    if not meta_server:
        return JSONResponse(status_code=503, content={"error": "Server not initialized"})
    
    try:
        servers = meta_server.registry.list_servers()
        return {
            "status": "success",
            "servers": [
                {
                    "id": server.id,
                    "name": server.name,
                    "status": server.status.value,
                    "tools_count": len(server.tools),
                    "transport_type": server.registration.transport_type.value
                }
                for server in servers
            ],
            "total_count": len(servers)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/admin/system/stats")
async def get_system_stats():
    """Get system statistics"""
    if not meta_server:
        return JSONResponse(status_code=503, content={"error": "Server not initialized"})
    
    try:
        stats = await meta_server.registry.get_registry_stats()
        return {
            "status": "success",
            "system_stats": stats
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/admin/tools")
async def list_all_tools():
    """List all available tools"""
    if not meta_server:
        return JSONResponse(status_code=503, content={"error": "Server not initialized"})
    
    try:
        active_servers = meta_server.registry.list_active_servers()
        all_tools = []
        
        # Add Meta MCP tools
        for tool_name, tool in meta_server.server.tools.items():
            all_tools.append({
                "name": tool_name,
                "description": tool.description,
                "server_name": "meta-mcp",
                "input_schema": tool.inputSchema
            })
        
        # Add tools from external servers
        for server in active_servers:
            if hasattr(server.client, 'tools'):
                for tool in server.client.tools:
                    all_tools.append({
                        "name": f"{server.name}.{tool.name}",
                        "description": tool.description,
                        "server_name": server.name,
                        "input_schema": tool.inputSchema
                    })
        
        return {
            "status": "success",
            "tools": all_tools,
            "total_count": len(all_tools)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/admin/routing/test")
async def test_routing(request: Request):
    """Test routing analysis"""
    if not meta_server:
        return JSONResponse(status_code=503, content={"error": "Server not initialized"})
    
    try:
        data = await request.json()
        request_text = data.get("request_text", "")
        available_servers = data.get("available_servers", [])
        
        if not available_servers:
            active_servers = meta_server.registry.list_active_servers()
            available_servers = [server.name for server in active_servers]
        
        # Get routing decision using the router
        from core.router import get_router
        router = get_router()
        
        decision = await router.route_request(
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
                "matched_rules": decision.matched_rules
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "Meta MCP HTTP Server",
        "version": "1.0.0",
        "description": "HTTP endpoints for Meta MCP orchestration server",
        "endpoints": {
            "health": "/health",
            "mcp": "/mcp",
            "mcp_health": "/mcp/health",
            "admin": "/admin/*",
            "docs": "/docs"
        }
    }

async def main():
    """Main function to run HTTP server"""
    print("🌟 Meta MCP - HTTP Server Mode")
    print("=" * 40)
    print("This will start Meta MCP with HTTP endpoints for Postman testing")
    print("Server will be available at: http://localhost:8000")
    print("API docs will be at: http://localhost:8000/docs")
    
    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )
    
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())