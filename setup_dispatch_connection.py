#!/usr/bin/env python3
"""
Setup script to configure Meta MCP to connect to Dispatch MCP
Run this BEFORE starting Meta MCP
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.registry import get_registry, McpServerRegistration, TransportType
from core.router import get_router, RoutingRule, RoutingStrategy

async def setup_dispatch_connection():
    """Setup Dispatch MCP connection configuration"""
    print("🔧 Setting up Dispatch MCP connection for Meta MCP")
    print("=" * 50)
    
    # Get configuration
    dispatch_path = input("Enter the full path to dispatch-mcp directory: ").strip()
    dispatch_path = Path(dispatch_path).resolve()
    
    if not dispatch_path.exists():
        print(f"❌ Directory not found: {dispatch_path}")
        return False
    
    # Check if dispatch is built
    index_js = dispatch_path / "dist" / "index.js"
    if not index_js.exists():
        print("❌ Dispatch MCP not built. Run 'npm run build' in dispatch-mcp directory first.")
        return False
    
    # Get PSA configuration
    psa_url = input("Enter PSA service URL (default: http://localhost:9019): ").strip()
    if not psa_url:
        psa_url = "http://localhost:9019"
    
    redis_url = input("Enter Redis URL (default: redis://localhost:6379): ").strip()
    if not redis_url:
        redis_url = "redis://localhost:6379"
    
    # Initialize registry
    print("\n📝 Configuring Meta MCP registry...")
    registry = get_registry()
    await registry.initialize()
    
    # Check if dispatch already exists
    existing = registry.get_server_by_name("dispatch")
    if existing:
        print("⚠️  Dispatch server already registered")
        remove = input("Remove and re-register? (y/n): ").lower()
        if remove == 'y':
            await registry.unregister_server(existing.id)
            print("✅ Removed existing registration")
        else:
            print("✅ Using existing registration")
            return True
    
    # Create registration for Dispatch MCP
    registration = McpServerRegistration(
        name="dispatch",
        description="Dispatch ticket queue management MCP server",
        transport_type=TransportType.STDIO,
        transport_config={
            "command": "node",
            "args": [str(index_js)],
            "env": {
                "PSA_SERVICE_URL": psa_url,
                "REDIS_URL": redis_url,
                "CACHE_ENABLED": "true",
                "CACHE_TTL": "300"
            }
        },
        auto_connect=False,  # Don't auto-connect yet
        metadata={
            "dispatch_path": str(dispatch_path),
            "psa_url": psa_url,
            "tools_count": 16
        }
    )
    
    # Register the server
    try:
        server_id = await registry.register_server(registration)
        print(f"✅ Registered Dispatch MCP server with ID: {server_id}")
        
        # Add routing rules
        print("\n🔀 Adding routing rules...")
        router = get_router()
        
        # Add comprehensive dispatch routing rule
        dispatch_rule = RoutingRule(
            name="dispatch_routing",
            pattern=r"(ticket|queue|technician|tech|assign|workload|tier|dispatch|psa|hold|requeue|priority|eligible|pick|complete)",
            keywords=[
                "ticket", "tickets", "queue", "queued", "technician", "tech", 
                "assign", "assignment", "workload", "tier", "tier1", "tier2", "tier3",
                "dispatch", "psa", "hold", "requeue", "priority", "score",
                "eligible", "pick", "complete", "activity", "activities"
            ],
            server_names=["dispatch"],
            strategy=RoutingStrategy.SINGLE,
            priority=100,  # Highest priority
            confidence_threshold=0.3
        )
        
        router.add_routing_rule(dispatch_rule)
        print("✅ Routing rules configured")
        
        # Save configuration
        config_file = Path("dispatch_config.json")
        config_data = {
            "dispatch_path": str(dispatch_path),
            "psa_url": psa_url,
            "redis_url": redis_url,
            "server_id": server_id
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"\n✅ Configuration saved to {config_file}")
        print("\n✨ Setup complete!")
        print("\nNext steps:")
        print("1. Make sure Dispatch MCP is running in another terminal")
        print("2. Start Meta MCP with: python src/main.py")
        print("3. Meta MCP will connect to Dispatch automatically")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await registry.shutdown()

async def verify_setup():
    """Verify the setup is correct"""
    print("\n🔍 Verifying setup...")
    
    registry = get_registry()
    await registry.initialize()
    
    dispatch = registry.get_server_by_name("dispatch")
    if dispatch:
        print(f"✅ Dispatch server found: {dispatch.id}")
        print(f"   Status: {dispatch.status.value}")
        print(f"   Transport: {dispatch.registration.transport_type.value}")
    else:
        print("❌ Dispatch server not found in registry")
    
    await registry.shutdown()

async def main():
    if await setup_dispatch_connection():
        await verify_setup()

if __name__ == "__main__":
    asyncio.run(main())