# examples/create_custom_mcp.py
#!/usr/bin/env python3
"""
Create Custom MCP Server Example
Shows how to create a simple custom MCP server and register it with Meta MCP
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.server import McpServer, McpServerManager
from mcp.protocol import McpTool
from core.registry import get_registry, McpServerRegistration, TransportType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_simple_calculator_mcp():
    """Create a simple calculator MCP server"""
    
    # Create the MCP server
    server = McpServer("Calculator MCP", "1.0.0")
    
    # Define calculator tools
    add_tool = McpTool(
        name="add",
        description="Add two numbers",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    )
    
    multiply_tool = McpTool(
        name="multiply",
        description="Multiply two numbers",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    )
    
    # Tool handlers
    async def handle_add(arguments):
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        result = a + b
        return [{"type": "text", "text": f"{a} + {b} = {result}"}]
    
    async def handle_multiply(arguments):
        a = arguments.get("a", 1)
        b = arguments.get("b", 1)
        result = a * b
        return [{"type": "text", "text": f"{a} × {b} = {result}"}]
    
    # Register tools
    server.add_tool(add_tool, handle_add)
    server.add_tool(multiply_tool, handle_multiply)
    
    logger.info("✅ Created Calculator MCP server with 2 tools")
    return server


async def run_calculator_mcp_server():
    """Run the calculator MCP server"""
    
    logger.info("🧮 Starting Calculator MCP Server")
    
    # Create the server
    server = await create_simple_calculator_mcp()
    
    # Create server manager
    manager = McpServerManager(server)
    
    # Run with stdio transport
    logger.info("🚀 Calculator MCP server running on stdio transport")
    logger.info("Send MCP JSON-RPC messages to test:")
    logger.info('{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": true}, "clientInfo": {"name": "test", "version": "1.0"}}}')
    
    await manager.run_stdio()


async def register_calculator_with_meta_mcp():
    """Register the calculator MCP with Meta MCP"""
    
    logger.info("📝 Registering Calculator MCP with Meta MCP")
    
    # Initialize Meta MCP registry
    registry = get_registry()
    await registry.initialize()
    
    # Create registration for calculator MCP
    registration = McpServerRegistration(
        name="calculator-mcp",
        description="Simple calculator MCP server for mathematical operations",
        transport_type=TransportType.STDIO,
        transport_config={
            "command": "python",
            "args": [str(Path(__file__).absolute()), "--run-server"]
        },
        auto_connect=True,
        metadata={
            "category": "utility",
            "tools": ["add", "multiply"],
            "created_by": "example"
        }
    )
    
    try:
        server_id = await registry.register_server(registration)
        logger.info(f"✅ Successfully registered Calculator MCP: {server_id}")
        
        # Try to connect
        success = await registry.connect_server(server_id)
        if success:
            logger.info("🔗 Successfully connected to Calculator MCP")
            
            # List available tools
            server_instance = registry.get_server(server_id)
            if server_instance and server_instance.client.connected:
                tools = server_instance.client.tools
                logger.info(f"🔧 Available tools: {[tool.name for tool in tools]}")
            
        else:
            logger.warning("⚠️ Failed to connect to Calculator MCP")
        
    except Exception as e:
        logger.error(f"❌ Failed to register Calculator MCP: {e}")
    
    finally:
        await registry.shutdown()


async def test_calculator_integration():
    """Test calculator integration with Meta MCP"""
    
    logger.info("🧪 Testing Calculator MCP Integration")
    
    # This would typically involve:
    # 1. Starting Meta MCP server
    # 2. Registering calculator MCP
    # 3. Testing tool calls through Meta MCP
    # 4. Verifying intelligent routing works
    
    logger.info("Integration test would involve full Meta MCP setup")
    logger.info("For now, run register_calculator_with_meta_mcp() with Meta MCP running")


def main():
    """Main function"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--run-server":
        # Run the calculator server directly
        asyncio.run(run_calculator_mcp_server())
    else:
        # Interactive menu
        print("🧮 Calculator MCP Example")
        print("=" * 30)
        print("1. Run Calculator MCP Server (stdio)")
        print("2. Register with Meta MCP")
        print("3. Test Integration")
        
        choice = input("\nChoose an option (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(run_calculator_mcp_server())
        elif choice == "2":
            asyncio.run(register_calculator_with_meta_mcp())
        elif choice == "3":
            asyncio.run(test_calculator_integration())
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
