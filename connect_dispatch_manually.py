#!/usr/bin/env python3
"""
Manually connect to Dispatch MCP server after Meta MCP is running
Use this if auto-connect didn't work
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.registry import get_registry

async def connect_dispatch():
    """Manually connect to dispatch server"""
    print("🔌 Manually connecting to Dispatch MCP server...")
    
    registry = get_registry()
    await registry.initialize()
    
    # Find dispatch server
    dispatch = registry.get_server_by_name("dispatch")
    if not dispatch:
        print("❌ Dispatch server not found. Run setup_dispatch_connection.py first")
        return False
    
    print(f"Found Dispatch server: {dispatch.id}")
    print(f"Current status: {dispatch.status.value}")
    
    if dispatch.status.value == "active":
        print("✅ Already connected!")
        return True
    
    # Try to connect
    print("Attempting connection...")
    success = await registry.connect_server(dispatch.id)
    
    if success:
        print("✅ Successfully connected to Dispatch MCP!")
        
        # Wait for tools to be discovered
        await asyncio.sleep(2)
        
        # Refresh server info
        dispatch = registry.get_server(dispatch.id)
        print(f"Available tools: {len(dispatch.tools)}")
        
        if dispatch.tools:
            print("\nDispatch tools:")
            for tool in sorted(dispatch.tools)[:5]:
                print(f"  • {tool}")
            if len(dispatch.tools) > 5:
                print(f"  ... and {len(dispatch.tools) - 5} more")
    else:
        print("❌ Failed to connect")
        print("\nTroubleshooting:")
        print("1. Make sure Dispatch MCP is running in another terminal")
        print("2. Check that 'node dist/index.js' works in dispatch-mcp directory")
        print("3. Verify PSA service is accessible")
        
    return success

async def main():
    try:
        await connect_dispatch()
    except KeyboardInterrupt:
        print("\n👋 Cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())