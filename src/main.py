"""
Meta MCP Server - Main Application
A real MCP server that aggregates and routes to multiple MCP servers
"""

import asyncio
import logging
import sys
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from core.registry import get_registry, McpServerRegistration, TransportType
from core.config import get_settings
from core.router import get_router
from mcp.protocol import McpError
from mcp.server import McpServer, McpServerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("meta_mcp.log")
    ]
)
logger = logging.getLogger(__name__)

settings = get_settings()


class MetaMCPServer:
    """Meta MCP Server implementation"""
    
    def __init__(self):
        self.server = McpServer("Meta MCP Server", "1.0.0")
        self.manager = McpServerManager(self.server)
        self.registry = None
        self.router = None
    
    async def initialize(self):
        """Initialize the Meta MCP server"""
        logger.info("Starting Meta MCP Server...")
        
        # Initialize registry
        self.registry = get_registry()
        await self.registry.initialize()
        
        # Initialize router
        self.router = get_router()
        
        # Register tools
        self._register_tools()
        
        # Register example servers if in debug mode
        if settings.debug and settings.auto_register_examples:
            await self._register_example_servers()
        
        logger.info("Meta MCP Server initialized successfully")
    
    def _register_tools(self):
        """Register all Meta MCP tools"""
        from mcp.protocol import McpTool
        
        # Define tools
        tools = [
            {
                "name": "list_registered_servers",
                "description": "List all registered MCP servers and their status",
                "schema": {"type": "object", "properties": {}, "required": []},
                "handler": self.list_registered_servers
            },
            {
                "name": "register_mcp_server", 
                "description": "Register a new MCP server",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Server name"},
                        "description": {"type": "string", "description": "Server description"},
                        "transport_type": {"type": "string", "description": "Transport type"},
                        "command": {"type": "string", "description": "Command to run"},
                        "args": {"type": "array", "description": "Command arguments"},
                        "auto_connect": {"type": "boolean", "description": "Auto-connect"}
                    },
                    "required": ["name", "command"]
                },
                "handler": self.register_mcp_server
            },
            {
                "name": "connect_to_server",
                "description": "Connect to a registered MCP server",
                "schema": {
                    "type": "object", 
                    "properties": {
                        "server_name": {"type": "string", "description": "Server name"}
                    },
                    "required": ["server_name"]
                },
                "handler": self.connect_to_server
            },
            {
                "name": "list_all_tools",
                "description": "List all tools from all connected servers",
                "schema": {"type": "object", "properties": {}, "required": []},
                "handler": self.list_all_tools
            },
            {
                "name": "call_tool_on_server",
                "description": "Call a tool on a specific MCP server",
                "schema": {
                    "type": "object",
                    "properties": {
                        "server_name": {"type": "string", "description": "Server name"},
                        "tool_name": {"type": "string", "description": "Tool name"},
                        "arguments": {"type": "object", "description": "Tool arguments"}
                    },
                    "required": ["server_name", "tool_name"]
                },
                "handler": self.call_tool_on_server
            },
            {
                "name": "intelligent_tool_routing",
                "description": "Analyze query and suggest best tools/servers",
                "schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Query to analyze"},
                        "max_suggestions": {"type": "integer", "description": "Max suggestions"}
                    },
                    "required": ["query"]
                },
                "handler": self.intelligent_tool_routing
            },
            {
                "name": "get_server_health",
                "description": "Check health status of all servers", 
                "schema": {"type": "object", "properties": {}, "required": []},
                "handler": self.get_server_health
            }
        ]
        
        # Register each tool
        for tool_def in tools:
            tool = McpTool(
                name=tool_def["name"],
                description=tool_def["description"],
                inputSchema=tool_def["schema"]
            )
            self.server.add_tool(tool, tool_def["handler"])
        
        logger.info(f"Registered {len(tools)} Meta MCP tools")
    
    async def list_registered_servers(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all registered servers"""
        try:
            stats = await self.registry.get_registry_stats()
            return [{
                "type": "text",
                "text": f"Found {stats['total_servers']} registered servers ({stats['active_servers']} active)"
            }]
        except Exception as e:
            logger.error(f"Failed to list servers: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    async def register_mcp_server(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Register a new MCP server"""
        try:
            name = arguments.get("name")
            description = arguments.get("description", "")
            transport_type = arguments.get("transport_type", "stdio")
            command = arguments.get("command")
            args = arguments.get("args", [])
            auto_connect = arguments.get("auto_connect", True)
            
            # Create registration
            registration = McpServerRegistration(
                name=name,
                description=description,
                transport_type=TransportType(transport_type),
                transport_config={
                    "command": command,
                    "args": args
                },
                auto_connect=auto_connect
            )
            
            server_id = await self.registry.register_server(registration)
            
            return [{
                "type": "text",
                "text": f"Successfully registered server: {name} (ID: {server_id})"
            }]
            
        except Exception as e:
            logger.error(f"Failed to register server: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    async def connect_to_server(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Connect to a server"""
        try:
            server_name = arguments.get("server_name")
            instance = self.registry.get_server_by_name(server_name)
            
            if not instance:
                return [{"type": "text", "text": f"Server not found: {server_name}"}]
            
            success = await self.registry.connect_server(instance.id)
            
            if success:
                return [{
                    "type": "text", 
                    "text": f"Connected to {server_name} - {len(instance.tools)} tools available"
                }]
            else:
                return [{"type": "text", "text": f"Failed to connect to {server_name}"}]
                
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    async def list_all_tools(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all tools"""
        try:
            active_servers = self.registry.list_active_servers()
            
            if not active_servers:
                return [{"type": "text", "text": "No active servers found"}]
            
            tools_text = "Available tools:\n"
            total_tools = 0
            
            for instance in active_servers:
                tools_text += f"\n{instance.name}:\n"
                for tool in instance.client.tools:
                    tools_text += f"  • {tool.name}: {tool.description}\n"
                    total_tools += 1
            
            tools_text += f"\nTotal: {total_tools} tools across {len(active_servers)} servers"
            
            return [{"type": "text", "text": tools_text}]
            
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    async def call_tool_on_server(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Call a tool on a server"""
        try:
            server_name = arguments.get("server_name")
            tool_name = arguments.get("tool_name")
            tool_args = arguments.get("arguments", {})
            
            instance = self.registry.get_server_by_name(server_name)
            if not instance:
                return [{"type": "text", "text": f"Server not found: {server_name}"}]
            
            if not instance.client.connected:
                return [{"type": "text", "text": f"Server not connected: {server_name}"}]
            
            # Check if tool exists
            tool = instance.client.get_tool_by_name(tool_name)
            if not tool:
                available_tools = [t.name for t in instance.client.tools]
                return [{
                    "type": "text", 
                    "text": f"Tool '{tool_name}' not found. Available: {', '.join(available_tools)}"
                }]
            
            # Call the tool
            result = await instance.client.call_tool(tool_name, tool_args)
            
            return [{
                "type": "text",
                "text": f"Tool executed successfully on {server_name}:\n{json.dumps(result, indent=2)}"
            }]
            
        except Exception as e:
            logger.error(f"Failed to call tool: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    async def intelligent_tool_routing(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhanced intelligent routing with domain-specific awareness"""
        try:
            query = arguments.get("query")
            max_suggestions = arguments.get("max_suggestions", 5)
            
            active_servers = self.registry.list_active_servers()
            if not active_servers:
                return [{"type": "text", "text": "No active servers available for routing"}]
            
            # Domain-specific patterns
            domain_patterns = {
                "dispatch": {
                    "keywords": ["ticket", "queue", "technician", "assign", "workload", "tier", "psa", "hold", "requeue", "dispatch"],
                    "patterns": [
                        r".*next ticket.*", r".*eligible ticket.*", r".*assign.*ticket.*",
                        r".*complete.*ticket.*", r".*technician.*workload.*", r".*ticket.*priority.*",
                        r".*queued ticket.*", r".*ticket.*on hold.*", r".*ticket.*activities.*"
                    ],
                    "confidence_boost": 0.3
                },
                "weather": {
                    "keywords": ["weather", "temperature", "forecast", "rain", "snow", "climate", "conditions"],
                    "patterns": [r".*weather.*", r".*temperature.*", r".*forecast.*"],
                    "confidence_boost": 0.4
                },
                "github": {
                    "keywords": ["repository", "repo", "github", "commit", "pull request", "issue", "code", "branch"],
                    "patterns": [r".*repository.*", r".*github.*", r".*pull request.*", r".*commit.*"],
                    "confidence_boost": 0.3
                },
                "memory": {
                    "keywords": ["remember", "recall", "store", "memory", "knowledge", "save", "retrieve"],
                    "patterns": [r".*remember.*", r".*store.*info.*", r".*recall.*", r".*save.*for later.*"],
                    "confidence_boost": 0.3
                },
                "filesystem": {
                    "keywords": ["file", "directory", "folder", "read", "write", "list", "path"],
                    "patterns": [r".*file.*", r".*directory.*", r".*folder.*", r".*read.*file.*"],
                    "confidence_boost": 0.2
                }
            }
            
            # Analyze query for domain matches
            query_lower = query.lower()
            domain_scores = {}
            
            for domain, config in domain_patterns.items():
                score = 0.0
                
                # Check keywords
                keyword_matches = sum(1 for keyword in config["keywords"] if keyword in query_lower)
                if keyword_matches > 0:
                    score = min(0.3 + (keyword_matches * 0.1), 0.7)
                
                # Check patterns
                import re
                for pattern in config["patterns"]:
                    if re.search(pattern, query_lower):
                        score += config["confidence_boost"]
                        break
                
                domain_scores[domain] = min(score, 1.0)
            
            # Get basic routing decision
            available_servers = [server.name for server in active_servers]
            decision = await self.router.route_request(
                query,
                available_servers,
                {"request_id": f"routing-{hash(query)}"}
            )
            
            # Enhance with domain-specific logic
            enhanced_servers = []
            for server_name in available_servers:
                # Map server names to domains
                server_domain = None
                if "dispatch" in server_name.lower():
                    server_domain = "dispatch"
                elif "weather" in server_name.lower():
                    server_domain = "weather"
                elif "github" in server_name.lower():
                    server_domain = "github"
                elif "memory" in server_name.lower():
                    server_domain = "memory"
                elif "filesystem" in server_name.lower():
                    server_domain = "filesystem"
                
                if server_domain and domain_scores.get(server_domain, 0) > 0.5:
                    enhanced_servers.append((server_name, domain_scores[server_domain]))
            
            # Sort by score and merge with original decision
            enhanced_servers.sort(key=lambda x: x[1], reverse=True)
            
            # Prioritize domain-matched servers
            final_servers = []
            for server_name, score in enhanced_servers:
                if server_name not in final_servers:
                    final_servers.append(server_name)
            
            # Add remaining servers from original decision
            for server_name in decision.matched_servers:
                if server_name not in final_servers:
                    final_servers.append(server_name)
            
            # Collect all tools from suggested servers
            suggested_tools = []
            for server_name in final_servers[:max_suggestions]:
                instance = self.registry.get_server_by_name(server_name)
                if instance and instance.client.connected:
                    for tool in instance.client.tools:
                        # Score tools based on query relevance
                        tool_score = 0.0
                        tool_name_lower = tool.name.lower()
                        tool_desc_lower = tool.description.lower()
                        
                        # Check if query words appear in tool name/description
                        query_words = [w for w in query_lower.split() if len(w) > 2]
                        for word in query_words:
                            if word in tool_name_lower:
                                tool_score += 0.4
                            if word in tool_desc_lower:
                                tool_score += 0.2
                        
                        if tool_score > 0:
                            suggested_tools.append({
                                "server": server_name,
                                "tool": tool.name,
                                "description": tool.description,
                                "score": tool_score
                            })
            
            # Sort tools by relevance
            suggested_tools.sort(key=lambda x: x["score"], reverse=True)
            
            # Build enhanced response
            result_text = f"🔍 **Routing Analysis for:** '{query}'\n\n"
            
            # Domain analysis section
            if any(score > 0 for score in domain_scores.values()):
                result_text += "📊 **Domain Analysis:**\n"
                sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
                for domain, score in sorted_domains[:3]:
                    if score > 0:
                        bar = "█" * int(score * 10)
                        result_text += f"  • {domain.capitalize()}: {bar} ({score:.2f})\n"
                result_text += "\n"
            
            # Server recommendations
            result_text += "🎯 **Recommended Servers:**\n"
            for i, server_name in enumerate(final_servers[:max_suggestions], 1):
                instance = self.registry.get_server_by_name(server_name)
                if instance:
                    status = "🟢" if instance.client.connected else "🔴"
                    domain_tag = ""
                    for domain, score in domain_scores.items():
                        if domain in server_name.lower() and score > 0.5:
                            domain_tag = f" [{domain.upper()}]"
                            break
                    result_text += f"{i}. {status} **{server_name}**{domain_tag} ({len(instance.client.tools)} tools)\n"
            
            # Tool suggestions
            if suggested_tools:
                result_text += "\n🔧 **Relevant Tools:**\n"
                for i, tool_info in enumerate(suggested_tools[:5], 1):
                    result_text += f"{i}. `{tool_info['tool']}` from {tool_info['server']}\n"
                    result_text += f"   {tool_info['description'][:80]}{'...' if len(tool_info['description']) > 80 else ''}\n"
            
            # Quick execute hint
            if suggested_tools:
                best_tool = suggested_tools[0]
                result_text += f"\n💡 **Quick Execute:**\n"
                result_text += f"```json\n"
                result_text += f'{{\n'
                result_text += f'  "server_name": "{best_tool["server"]}",\n'
                result_text += f'  "tool_name": "{best_tool["tool"]}",\n'
                result_text += f'  "arguments": {{}}\n'
                result_text += f'}}\n'
                result_text += f"```"
            
            # Original routing info (collapsed)
            result_text += f"\n\n<details>\n<summary>📋 Original Routing Info</summary>\n\n"
            result_text += f"Strategy: {decision.strategy.value}\n"
            result_text += f"Confidence: {decision.confidence:.2f}\n"
            result_text += f"Reasoning: {decision.reasoning}\n"
            result_text += "</details>"
            
            return [{"type": "text", "text": result_text}]
            
        except Exception as e:
            logger.error(f"Failed routing analysis: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    async def get_server_health(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get server health status"""
        try:
            servers = self.registry.list_servers()
            
            health_text = "Server Health Report:\n\n"
            healthy_count = 0
            
            for instance in servers:
                is_healthy = instance.client.connected if hasattr(instance.client, 'connected') else False
                status = "🟢 HEALTHY" if is_healthy else "🔴 UNHEALTHY"
                
                health_text += f"{status} - {instance.name}\n"
                health_text += f"  Tools: {len(instance.tools)}\n"
                health_text += f"  Status: {instance.status.value}\n"
                
                if instance.last_health_check:
                    health_text += f"  Last Check: {instance.last_health_check.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                health_text += "\n"
                
                if is_healthy:
                    healthy_count += 1
            
            health_text += f"Summary: {healthy_count}/{len(servers)} servers healthy"
            
            return [{"type": "text", "text": health_text}]
            
        except Exception as e:
            logger.error(f"Failed health check: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    async def _register_example_servers(self):
        """Register example MCP servers for testing"""
        example_servers = [
            {
                "name": "weather-mcp",
                "description": "Weather information MCP server",
                "command": "npx",
                "args": ["-y", "@h1deya/mcp-server-weather"]
            },
            {
                "name": "memory-mcp", 
                "description": "Memory MCP server for knowledge storage",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"]
            },
            {
                "name": "filesystem-mcp",
                "description": "Filesystem MCP server", 
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            }
        ]
        
        # Add GitHub server if token available
        if settings.github_token:
            example_servers.append({
                "name": "github-mcp",
                "description": "GitHub MCP server",
                "command": "npx", 
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_token}
            })
        
        for server_config in example_servers:
            try:
                registration = McpServerRegistration(
                    name=server_config["name"],
                    description=server_config["description"],
                    transport_type=TransportType.STDIO,
                    transport_config={
                        "command": server_config["command"],
                        "args": server_config["args"],
                        "env": server_config.get("env", {})
                    }
                )
                
                server_id = await self.registry.register_server(registration)
                logger.info(f"Registered example server: {server_config['name']} ({server_id})")
                
            except Exception as e:
                logger.warning(f"Failed to register example server {server_config['name']}: {e}")
    
    async def run_stdio(self):
        """Run server with stdio transport"""
        await self.initialize()
        await self.manager.run_stdio()
    
    async def shutdown(self):
        """Shutdown the server"""
        if self.registry:
            await self.registry.shutdown()
        logger.info("Meta MCP Server shutdown complete")


async def main():
    """Main function"""
    meta_server = MetaMCPServer()
    
    try:
        await meta_server.run_stdio()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        await meta_server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())