import asyncio
import os
from pathlib import Path
from src.core.registry import get_registry, McpServerRegistration, TransportType

async def register_dispatch():
    """Register the Dispatch MCP server"""
    registry = get_registry()
    await registry.initialize()
    
    # Path to your dispatch MCP - UPDATE THIS
    dispatch_path = "../dispatch-mcp"
    
    # Check if server already exists
    existing_server = registry.get_server_by_name("dispatch")
    if existing_server:
        print(f"⚠️  Server 'dispatch' already exists with ID: {existing_server.id}")
        print(f"   Status: {existing_server.status.value}")
        
        # Try to connect if not already connected
        if existing_server.status.value != "active":
            print("   Attempting to connect...")
            success = await registry.connect_server(existing_server.id)
            if success:
                print("   ✅ Connected successfully!")
            else:
                print("   ❌ Failed to connect")
        else:
            print("   ✅ Already connected!")
        return
    
    registration = McpServerRegistration(
        name="dispatch",
        description="Dispatch ticket queue management MCP server",
        transport_type=TransportType.STDIO,
        transport_config={
            "command": "node",
            "args": [str(Path(dispatch_path) / "dist" / "index.js")],
            "env": {
                "PSA_SERVICE_URL": os.getenv("PSA_SERVICE_URL", "http://localhost:9019"),
                "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
                "CACHE_ENABLED": "true",
                "CACHE_TTL": "300"
            }
        },
        auto_connect=True
    )
    
    try:
        server_id = await registry.register_server(registration)
        print(f"✅ Successfully registered Dispatch MCP with ID: {server_id}")
    except Exception as e:
        print(f"❌ Failed to register Dispatch MCP: {e}")

if __name__ == "__main__":
    asyncio.run(register_dispatch())