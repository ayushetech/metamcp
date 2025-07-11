"""
Meta MCP Protocol Implementation
Handles MCP JSON-RPC communication and protocol compliance
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
import httpx
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class TransportType(str, Enum):
    """MCP Transport Types"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WEBSOCKET = "websocket"


class McpMessageType(str, Enum):
    """MCP Message Types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class McpCapabilities:
    """MCP Server Capabilities"""
    tools: bool = True
    resources: bool = True
    prompts: bool = True
    sampling: bool = False
    roots: bool = False


class McpTool(BaseModel):
    """MCP Tool Definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class McpResource(BaseModel):
    """MCP Resource Definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class McpPrompt(BaseModel):
    """MCP Prompt Definition"""
    name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None


class McpMessage(BaseModel):
    """Base MCP Message"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class McpError(Exception):
    """MCP Protocol Error"""
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")


class McpClient:
    """
    MCP Client for connecting to external MCP servers
    Supports multiple transport types: stdio, SSE, HTTP, WebSocket
    """
    
    def __init__(self, transport_type: TransportType, **transport_config):
        self.transport_type = transport_type
        self.transport_config = transport_config
        self.capabilities = McpCapabilities()
        self.tools: List[McpTool] = []
        self.resources: List[McpResource] = []
        self.prompts: List[McpPrompt] = []
        self.connected = False
        self._request_id = 0
        self._pending_requests: Dict[str, asyncio.Future] = {}
        
        # Transport-specific attributes
        self._process = None
        self._websocket = None
        self._http_client = None
        self._sse_client = None
    
    async def connect(self) -> bool:
        """Connect to MCP server based on transport type"""
        try:
            if self.transport_type == TransportType.STDIO:
                await self._connect_stdio()
            elif self.transport_type == TransportType.SSE:
                await self._connect_sse()
            elif self.transport_type == TransportType.HTTP:
                await self._connect_http()
            elif self.transport_type == TransportType.WEBSOCKET:
                await self._connect_websocket()
            
            # Initialize connection
            await self._initialize_connection()
            self.connected = True
            logger.info(f"Connected to MCP server via {self.transport_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
            return False
    
    async def _connect_stdio(self):
        """Connect using stdio transport (subprocess) with increased buffer limit"""
        command = self.transport_config.get("command")
        args = self.transport_config.get("args", [])
        env = self.transport_config.get("env", {})
        
        # Prepare full environment
        import os
        full_env = os.environ.copy()
        full_env.update(env)
        
        # Windows compatibility fix
        import platform
        import shutil
        if platform.system() == "Windows":
            if command == "npx":
                npx_path = shutil.which("npx.cmd") or shutil.which("npx")
                if npx_path:
                    # Increase buffer limit to 10MB (10 * 1024 * 1024)
                    self._process = await asyncio.create_subprocess_exec(
                        npx_path, *args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=full_env,
                        limit=10 * 1024 * 1024  # 10MB buffer
                    )
                else:
                    raise FileNotFoundError("npx not found in PATH")
            else:
                self._process = await asyncio.create_subprocess_exec(
                    command, *args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=full_env,
                    limit=10 * 1024 * 1024  # 10MB buffer
                )
        else:
            self._process = await asyncio.create_subprocess_exec(
                command, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
                limit=10 * 1024 * 1024  # 10MB buffer
            )
        
        # Start reading responses
        asyncio.create_task(self._read_stdio_responses())
    
    async def _connect_sse(self):
        """Connect using Server-Sent Events transport"""
        url = self.transport_config.get("url")
        headers = self.transport_config.get("headers", {})
        
        self._http_client = httpx.AsyncClient()
        # SSE connection setup would go here
        # This is a simplified implementation
    
    async def _connect_http(self):
        """Connect using HTTP transport"""
        base_url = self.transport_config.get("base_url")
        headers = self.transport_config.get("headers", {})
        
        self._http_client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=30.0
        )
    
    async def _connect_websocket(self):
        """Connect using WebSocket transport"""
        uri = self.transport_config.get("uri")
        self._websocket = await websockets.connect(uri)
        
        # Start reading WebSocket messages
        asyncio.create_task(self._read_websocket_messages())
    
    async def _initialize_connection(self):
        """Initialize MCP connection with handshake"""
        # Send initialize request
        init_response = await self.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": self.capabilities.tools,
                "resources": self.capabilities.resources,
                "prompts": self.capabilities.prompts
            },
            "clientInfo": {
                "name": "Meta MCP Client",
                "version": "1.0.0"
            }
        })
        
        # Send initialized notification
        await self.notify("notifications/initialized")
        
        # Discover available tools, resources, and prompts
        await self._discover_capabilities()
    
    async def _discover_capabilities(self):
        """Discover server capabilities"""
        try:
            # List tools
            if self.capabilities.tools:
                tools_response = await self.request("tools/list")
                self.tools = [McpTool(**tool) for tool in tools_response.get("tools", [])]
                logger.info(f"Discovered {len(self.tools)} tools")
            
            # List resources
            if self.capabilities.resources:
                resources_response = await self.request("resources/list")
                self.resources = [McpResource(**resource) for resource in resources_response.get("resources", [])]
                logger.info(f"Discovered {len(self.resources)} resources")
            
            # List prompts
            if self.capabilities.prompts:
                prompts_response = await self.request("prompts/list")
                self.prompts = [McpPrompt(**prompt) for prompt in prompts_response.get("prompts", [])]
                logger.info(f"Discovered {len(self.prompts)} prompts")
                
        except Exception as e:
            logger.warning(f"Failed to discover some capabilities: {e}")
    
    async def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send MCP request and wait for response"""
        request_id = str(uuid.uuid4())
        message = McpMessage(
            id=request_id,
            method=method,
            params=params or {}
        )
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        # Send message
        await self._send_message(message)
        
        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise McpError(-32001, f"Request timeout for method {method}")
    
    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send MCP notification (no response expected)"""
        message = McpMessage(
            method=method,
            params=params or {}
        )
        await self._send_message(message)
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server"""
        return await self.request("tools/call", {
            "name": name,
            "arguments": arguments
        })
    
    async def get_resource(self, uri: str) -> Any:
        """Get a resource from the MCP server"""
        return await self.request("resources/read", {
            "uri": uri
        })
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Get a prompt from the MCP server"""
        return await self.request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })
    
    async def _send_message(self, message: McpMessage):
        """Send message via active transport"""
        message_json = message.model_dump_json(exclude_none=True)
        
        if self.transport_type == TransportType.STDIO and self._process:
            self._process.stdin.write(message_json.encode() + b'\n')
            await self._process.stdin.drain()
            
        elif self.transport_type == TransportType.HTTP and self._http_client:
            await self._http_client.post("/mcp", json=message.model_dump(exclude_none=True))
            
        elif self.transport_type == TransportType.WEBSOCKET and self._websocket:
            await self._websocket.send(message_json)
            
        logger.debug(f"Sent MCP message: {message.method}")
    
    async def _read_stdio_responses(self):
        """Read responses from stdio transport"""
        if not self._process:
            return
            
        async for line in self._process.stdout:
            try:
                message_data = json.loads(line.decode().strip())
                await self._handle_message(message_data)
            except Exception as e:
                logger.error(f"Failed to parse stdio message: {e}")
    
    async def _read_websocket_messages(self):
        """Read messages from WebSocket transport"""
        if not self._websocket:
            return
            
        try:
            async for message in self._websocket:
                try:
                    message_data = json.loads(message)
                    await self._handle_message(message_data)
                except Exception as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False
    
    async def _handle_message(self, message_data: Dict[str, Any]):
        """Handle incoming MCP message"""
        try:
            message = McpMessage(**message_data)
            
            if message.id and message.id in self._pending_requests:
                # Response to our request
                future = self._pending_requests.pop(message.id)
                if message.error:
                    error = McpError(
                        message.error.get("code", -32000),
                        message.error.get("message", "Unknown error"),
                        message.error.get("data")
                    )
                    future.set_exception(error)
                else:
                    future.set_result(message.result)
            
            elif message.method:
                # Notification or request from server
                await self._handle_server_message(message)
                
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")
    
    async def _handle_server_message(self, message: McpMessage):
        """Handle messages from server (notifications, requests)"""
        if message.method == "notifications/resources/updated":
            # Resource updated notification
            await self._discover_capabilities()
        elif message.method == "notifications/tools/list_changed":
            # Tools changed notification
            await self._discover_capabilities()
        # Add more server message handlers as needed
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        self.connected = False
        
        if self._process:
            self._process.terminate()
            await self._process.wait()
            
        if self._http_client:
            await self._http_client.aclose()
            
        if self._websocket:
            await self._websocket.close()
        
        logger.info(f"Disconnected from MCP server")
    
    def get_tool_by_name(self, name: str) -> Optional[McpTool]:
        """Get tool by name"""
        return next((tool for tool in self.tools if tool.name == name), None)
    
    def get_resource_by_uri(self, uri: str) -> Optional[McpResource]:
        """Get resource by URI"""
        return next((resource for resource in self.resources if resource.uri == uri), None)
    
    def get_prompt_by_name(self, name: str) -> Optional[McpPrompt]:
        """Get prompt by name"""
        return next((prompt for prompt in self.prompts if prompt.name == name), None)


class McpServer:
    """
    MCP Server for exposing Meta MCP as an MCP server
    Aggregates tools/resources/prompts from registered MCP servers
    """
    
    def __init__(self, name: str = "Meta MCP Server"):
        self.name = name
        self.version = "1.0.0"
        self.tools: Dict[str, McpTool] = {}
        self.resources: Dict[str, McpResource] = {}
        self.prompts: Dict[str, McpPrompt] = {}
        self.clients: Dict[str, McpClient] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        
    def register_client(self, name: str, client: McpClient):
        """Register an MCP client (connected to external server)"""
        self.clients[name] = client
        self._aggregate_capabilities()
        logger.info(f"Registered MCP client: {name}")
    
    def unregister_client(self, name: str):
        """Unregister an MCP client"""
        if name in self.clients:
            del self.clients[name]
            self._aggregate_capabilities()
            logger.info(f"Unregistered MCP client: {name}")
    
    def _aggregate_capabilities(self):
        """Aggregate capabilities from all registered clients"""
        # Clear current capabilities
        self.tools.clear()
        self.resources.clear()
        self.prompts.clear()
        
        # Aggregate from all clients
        for client_name, client in self.clients.items():
            # Namespace tools with client name
            for tool in client.tools:
                namespaced_name = f"{client_name}.{tool.name}"
                self.tools[namespaced_name] = tool
            
            # Namespace resources
            for resource in client.resources:
                namespaced_uri = f"{client_name}://{resource.uri}"
                namespaced_resource = McpResource(
                    uri=namespaced_uri,
                    name=f"{client_name}.{resource.name}",
                    description=resource.description,
                    mimeType=resource.mimeType
                )
                self.resources[namespaced_uri] = namespaced_resource
            
            # Namespace prompts
            for prompt in client.prompts:
                namespaced_name = f"{client_name}.{prompt.name}"
                self.prompts[namespaced_name] = prompt
        
        logger.info(f"Aggregated {len(self.tools)} tools, {len(self.resources)} resources, {len(self.prompts)} prompts")
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Handle tool call by routing to appropriate client"""
        if "." not in name:
            raise McpError(-32601, f"Tool not found: {name}")
        
        client_name, tool_name = name.split(".", 1)
        if client_name not in self.clients:
            raise McpError(-32601, f"Client not found: {client_name}")
        
        client = self.clients[client_name]
        if not client.connected:
            raise McpError(-32002, f"Client not connected: {client_name}")
        
        try:
            return await client.call_tool(tool_name, arguments)
        except Exception as e:
            raise McpError(-32603, f"Tool call failed: {str(e)}")
    
    async def handle_resource_read(self, uri: str) -> Any:
        """Handle resource read by routing to appropriate client"""
        if "://" not in uri:
            raise McpError(-32601, f"Resource not found: {uri}")
        
        client_name = uri.split("://")[0]
        original_uri = uri.split("://", 1)[1]
        
        if client_name not in self.clients:
            raise McpError(-32601, f"Client not found: {client_name}")
        
        client = self.clients[client_name]
        if not client.connected:
            raise McpError(-32002, f"Client not connected: {client_name}")
        
        try:
            return await client.get_resource(original_uri)
        except Exception as e:
            raise McpError(-32603, f"Resource read failed: {str(e)}")
    
    async def handle_prompt_get(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Handle prompt get by routing to appropriate client"""
        if "." not in name:
            raise McpError(-32601, f"Prompt not found: {name}")
        
        client_name, prompt_name = name.split(".", 1)
        if client_name not in self.clients:
            raise McpError(-32601, f"Client not found: {client_name}")
        
        client = self.clients[client_name]
        if not client.connected:
            raise McpError(-32002, f"Client not connected: {client_name}")
        
        try:
            return await client.get_prompt(prompt_name, arguments)
        except Exception as e:
            raise McpError(-32603, f"Prompt get failed: {str(e)}")
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all aggregated tools"""
        return [tool.model_dump() for tool in self.tools.values()]
    
    def list_resources(self) -> List[Dict[str, Any]]:
        """List all aggregated resources"""
        return [resource.model_dump() for resource in self.resources.values()]
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all aggregated prompts"""
        return [prompt.model_dump() for prompt in self.prompts.values()]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all registered clients"""
        health_status = {
            "server": self.name,
            "version": self.version,
            "clients": {},
            "overall_status": "healthy"
        }
        
        unhealthy_count = 0
        for client_name, client in self.clients.items():
            client_healthy = client.connected
            if not client_healthy:
                unhealthy_count += 1
            
            health_status["clients"][client_name] = {
                "connected": client_healthy,
                "tools_count": len(client.tools),
                "resources_count": len(client.resources),
                "prompts_count": len(client.prompts)
            }
        
        if unhealthy_count > 0:
            if unhealthy_count == len(self.clients):
                health_status["overall_status"] = "unhealthy"
            else:
                health_status["overall_status"] = "degraded"
        
        return health_status