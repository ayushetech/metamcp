# unregister_dispatch.py
import asyncio
import os
from pathlib import Path
from src.core.registry import get_registry

async def fix_dispatch():
    registry = get_registry()
    await registry.initialize()
    
    # First, unregister existing
    existing = registry.get_server_by_name("dispatch")
    if existing:
        await registry.unregister_server(existing.id)
        print("Unregistered existing dispatch server")
    
    # Re-register with absolute path
    dispatch_path = Path("../dispatch-mcp").resolve()  # UPDATE THIS
    
    from src.core.registry import McpServerRegistration, TransportType
    
    registration = McpServerRegistration(
        name="dispatch",
        description="Dispatch MCP",
        transport_type=TransportType.STDIO,
        transport_config={
            "command": "node",
            "args": [str(dispatch_path / "dist" / "index.js")],
            "env": {
                "PSA_SERVICE_URL": "http://localhost:9019",
                "REDIS_URL": "redis://localhost:6379",
                "CACHE_ENABLED": "true",
                "CACHE_TTL": "300"
            }
        },
        auto_connect=True
    )
    
    server_id = await registry.register_server(registration)
    print(f"Re-registered dispatch server: {server_id}")
    
    # Try to connect
    success = await registry.connect_server(server_id)
    print(f"Connection {'successful' if success else 'failed'}")

if __name__ == "__main__":
    asyncio.run(fix_dispatch())