#!/usr/bin/env python3
"""
Register Real MCP Servers Example
This script demonstrates how to register real MCP servers with the Meta MCP system
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.registry import get_registry, McpServerRegistration, TransportType
from core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def register_real_mcp_servers():
    """Register real MCP servers for testing and demonstration"""
    
    # Initialize registry
    registry = get_registry()
    await registry.initialize()
    
    settings = get_settings()
    
    logger.info("🚀 Starting Real MCP Server Registration")
    
    # List of real MCP servers to register
    servers_to_register = []
    
    # 1. Weather MCP Server (No API key required)
    servers_to_register.append({
        "name": "weather-mcp",
        "description": "Real weather information MCP server using Open-Meteo API",
        "transport_type": TransportType.STDIO,
        "transport_config": {
            "command": "npx",
            "args": ["-y", "@h1deya/mcp-server-weather"]
        }
    })
    
    # 2. Memory MCP Server (No API key required)
    servers_to_register.append({
        "name": "memory-mcp",
        "description": "Official memory MCP server for persistent knowledge storage",
        "transport_type": TransportType.STDIO,
        "transport_config": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
        }
    })
    
    # 3. Filesystem MCP Server (No API key required)
    servers_to_register.append({
        "name": "filesystem-mcp",
        "description": "Official filesystem MCP server for secure file operations",
        "transport_type": TransportType.STDIO,
        "transport_config": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    })
    
    # 4. GitHub MCP Server (Requires API key)
    if settings.github_token:
        servers_to_register.append({
            "name": "github-mcp",
            "description": "Official GitHub MCP server for repository management",
            "transport_type": TransportType.STDIO,
            "transport_config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_token
                }
            }
        })
        logger.info("✅ GitHub token found - will register GitHub MCP server")
    else:
        logger.warning("⚠️  No GitHub token found - skipping GitHub MCP server")
    
    # 5. Slack MCP Server (Requires API key)
    if settings.slack_bot_token and settings.slack_team_id:
        servers_to_register.append({
            "name": "slack-mcp",
            "description": "Official Slack MCP server for workspace integration",
            "transport_type": TransportType.STDIO,
            "transport_config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-slack"],
                "env": {
                    "SLACK_BOT_TOKEN": settings.slack_bot_token,
                    "SLACK_TEAM_ID": settings.slack_team_id
                }
            }
        })
        logger.info("✅ Slack tokens found - will register Slack MCP server")
    else:
        logger.warning("⚠️  No Slack tokens found - skipping Slack MCP server")
    
    # 6. PostgreSQL MCP Server (Requires database)
    # Note: This assumes you have a local PostgreSQL instance
    # Modify the connection string as needed
    postgres_url = os.getenv("POSTGRES_URL", "postgresql://localhost/postgres")
    servers_to_register.append({
        "name": "postgres-mcp",
        "description": "Official PostgreSQL MCP server for database operations",
        "transport_type": TransportType.STDIO,
        "transport_config": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", postgres_url]
        }
    })
    
    # Register all servers
    registered_servers = []
    failed_servers = []
    
    for server_config in servers_to_register:
        try:
            logger.info(f"📡 Registering {server_config['name']}...")
            
            registration = McpServerRegistration(**server_config)
            server_id = await registry.register_server(registration)
            
            registered_servers.append({
                "id": server_id,
                "name": server_config["name"],
                "description": server_config["description"]
            })
            
            logger.info(f"✅ Successfully registered {server_config['name']} ({server_id})")
            
            # Wait a bit between registrations to avoid overwhelming the system
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Failed to register {server_config['name']}: {e}")
            failed_servers.append({
                "name": server_config["name"],
                "error": str(e)
            })
    
    # Connection phase
    logger.info("\n🔗 Connecting to registered servers...")
    
    connected_servers = []
    failed_connections = []
    
    for server in registered_servers:
        try:
            logger.info(f"🔌 Connecting to {server['name']}...")
            
            success = await registry.connect_server(server["id"])
            
            if success:
                # Get server instance to check capabilities
                instance = registry.get_server(server["id"])
                if instance:
                    tools_count = len(instance.tools)
                    resources_count = len(instance.resources)
                    prompts_count = len(instance.prompts)
                    
                    connected_servers.append({
                        **server,
                        "tools_count": tools_count,
                        "resources_count": resources_count,
                        "prompts_count": prompts_count
                    })
                    
                    logger.info(f"✅ Connected to {server['name']} - "
                              f"{tools_count} tools, {resources_count} resources, {prompts_count} prompts")
                else:
                    failed_connections.append({
                        **server,
                        "error": "Could not retrieve server instance"
                    })
            else:
                failed_connections.append({
                    **server,
                    "error": "Connection failed"
                })
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to {server['name']}: {e}")
            failed_connections.append({
                **server,
                "error": str(e)
            })
    
    # Summary
    logger.info("\n📊 Registration Summary:")
    logger.info(f"✅ Successfully registered: {len(registered_servers)} servers")
    logger.info(f"❌ Failed registrations: {len(failed_servers)} servers")
    logger.info(f"🔗 Successfully connected: {len(connected_servers)} servers")
    logger.info(f"🔌 Failed connections: {len(failed_connections)} servers")
    
    if connected_servers:
        logger.info("\n🎉 Active MCP Servers:")
        for server in connected_servers:
            logger.info(f"  • {server['name']}: {server['tools_count']} tools available")
    
    if failed_servers:
        logger.info("\n⚠️  Failed Registrations:")
        for server in failed_servers:
            logger.info(f"  • {server['name']}: {server['error']}")
    
    if failed_connections:
        logger.info("\n⚠️  Failed Connections:")
        for server in failed_connections:
            logger.info(f"  • {server['name']}: {server['error']}")
    
    # Get final registry stats
    stats = await registry.get_registry_stats()
    logger.info(f"\n📈 Registry Stats:")
    logger.info(f"  Total servers: {stats['total_servers']}")
    logger.info(f"  Active servers: {stats['active_servers']}")
    logger.info(f"  Total tools: {stats['total_tools']}")
    logger.info(f"  Total resources: {stats['total_resources']}")
    logger.info(f"  Total prompts: {stats['total_prompts']}")
    
    # Test a simple tool call
    if connected_servers:
        logger.info("\n🧪 Testing tool calls...")
        
        # Try to call a tool from the weather server
        weather_instance = registry.get_server_by_name("weather-mcp")
        if weather_instance and weather_instance.client.connected:
            try:
                logger.info("Testing weather tool...")
                
                # List available tools first
                weather_tools = [tool.name for tool in weather_instance.client.tools]
                logger.info(f"Weather server tools: {weather_tools}")
                
                if weather_tools:
                    # Try calling the first tool
                    tool_name = weather_tools[0]
                    logger.info(f"Calling tool: {tool_name}")
                    
                    # Note: Actual parameters depend on the tool's input schema
                    # This is just a demonstration
                    
            except Exception as e:
                logger.warning(f"Tool call test failed: {e}")
    
    # Cleanup
    await registry.shutdown()
    
    logger.info("\n🏁 Registration complete!")
    
    return {
        "registered_servers": registered_servers,
        "connected_servers": connected_servers,
        "failed_servers": failed_servers,
        "failed_connections": failed_connections,
        "stats": stats
    }


async def test_server_capabilities():
    """Test capabilities of registered servers"""
    
    registry = get_registry()
    await registry.initialize()
    
    logger.info("🔍 Testing server capabilities...")
    
    active_servers = registry.list_active_servers()
    
    for instance in active_servers:
        logger.info(f"\n📡 Server: {instance.name}")
        logger.info(f"   Status: {instance.status.value}")
        logger.info(f"   Transport: {instance.registration.transport_type.value}")
        
        if instance.client.connected:
            logger.info(f"   Tools ({len(instance.client.tools)}):")
            for tool in instance.client.tools[:3]:  # Show first 3 tools
                logger.info(f"     • {tool.name}: {tool.description}")
            
            if len(instance.client.tools) > 3:
                logger.info(f"     ... and {len(instance.client.tools) - 3} more")
            
            logger.info(f"   Resources ({len(instance.client.resources)}):")
            for resource in instance.client.resources[:3]:  # Show first 3 resources
                logger.info(f"     • {resource.name}: {resource.uri}")
            
            if len(instance.client.resources) > 3:
                logger.info(f"     ... and {len(instance.client.resources) - 3} more")
        else:
            logger.warning(f"   ⚠️  Not connected")
    
    await registry.shutdown()


if __name__ == "__main__":
    print("🌟 Meta MCP Server - Real Server Registration")
    print("=" * 50)
    
    # Check if npx is available
    import shutil
    if not shutil.which("npx"):
        print("❌ Error: npx (Node.js) not found!")
        print("Please install Node.js to run MCP servers.")
        sys.exit(1)
    
    print("✅ Node.js (npx) found")
    
    # Run registration
    try:
        result = asyncio.run(register_real_mcp_servers())
        
        if result["connected_servers"]:
            print(f"\n🎊 Success! {len(result['connected_servers'])} MCP servers are now active.")
            print("\nYou can now:")
            print("1. Test the Meta MCP server with Claude Desktop")
            print("2. Use the intelligent routing features")
            print("3. Call tools from any registered server")
            
            # Show next steps
            print("\n📋 Next Steps:")
            print("1. Add Meta MCP to your Claude Desktop config:")
            print('   {"mcpServers": {"meta-mcp": {"command": "python", "args": ["src/main.py"]}}}')
            print("2. Test with Postman using the provided collection")
            print("3. Try the intelligent routing features")
        else:
            print("\n⚠️  No servers connected successfully.")
            print("Check the logs above for specific errors.")
            
    except KeyboardInterrupt:
        print("\n👋 Registration cancelled by user")
    except Exception as e:
        print(f"\n❌ Registration failed: {e}")
        sys.exit(1)