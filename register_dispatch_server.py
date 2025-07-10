import asyncio
import os
from pathlib import Path
from src.core.registry import get_registry, McpServerRegistration, TransportType

async def register_dispatch_server():
    """Register the Dispatch MCP server with Meta MCP"""
    registry = get_registry()
    await registry.initialize()
    
    # Update this path to where your dispatch-mcp is located
    dispatch_mcp_path = Path("../dispatch-mcp")
    
    registration = McpServerRegistration(
        name="dispatch",
        description="Dispatch ticket queue management MCP server for PSA integration",
        transport_type=TransportType.STDIO,
        transport_config={
            "command": "node",
            "args": [str(dispatch_mcp_path / "dist" / "index.js")],  # Adjust if your entry point is different
            "env": {
                "PSA_SERVICE_URL": os.getenv("PSA_SERVICE_URL", "http://localhost:9019"),
                "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
                "CACHE_ENABLED": os.getenv("CACHE_ENABLED", "true"),
                "CACHE_TTL": os.getenv("CACHE_TTL", "300")
            }
        },
        auto_connect=True,
        # Define capabilities based on your tools
        capabilities={
            "tools": [
                "dispatch_fetch_next_tickets",
                "dispatch_fetch_next_tickets_with_teams",
                "dispatch_get_eligible_tickets",
                "dispatch_get_current_working_tickets",
                "dispatch_get_current_assigned_tickets",
                "dispatch_get_tickets_on_hold",
                "dispatch_manually_assign_ticket",
                "dispatch_manually_pick_ticket",
                "dispatch_complete_ticket",
                "dispatch_requeue_ticket",
                "dispatch_get_technician_workload",
                "dispatch_get_ticket_activities",
                "dispatch_get_technician_activities",
                "dispatch_get_queued_tickets",
                "dispatch_update_ticket_priority",
                "dispatch_recalculate_scores"
            ]
        }
    )
    
    try:
        server_id = await registry.register_server(registration)
        print(f"Successfully registered Dispatch MCP server with ID: {server_id}")
        
        # Verify connection
        servers = await registry.list_servers()
        dispatch_server = next((s for s in servers if s.id == server_id), None)
        
        if dispatch_server:
            print(f"Server status: {dispatch_server.status}")
            print(f"Available tools: {len(dispatch_server.available_tools or [])}")
    except Exception as e:
        print(f"Failed to register Dispatch MCP server: {e}")

if __name__ == "__main__":
    asyncio.run(register_dispatch_server())