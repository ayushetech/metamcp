"""
MCP Server Implementation for Meta MCP
Implements the server side of the MCP protocol
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime

from .protocol import McpMessage, McpError, McpTool, McpResource, McpPrompt

logger = logging.getLogger(__name__)


class McpServer:
    """
    MCP Server implementation for Meta MCP
    Handles MCP protocol server-side operations
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.capabilities = {
            "tools": True,
            "resources": True,
            "prompts": True,
            "sampling": False
        }
        
        # Tool/resource/prompt registries
        self.tools: Dict[str, McpTool] = {}
        self.resources: Dict[str, McpResource] = {}
        self.prompts: Dict[str, McpPrompt] = {}
        
        # Handler registries
        self.tool_handlers: Dict[str, Callable] = {}
        self.resource_handlers: Dict[str, Callable] = {}
        self.prompt_handlers: Dict[str, Callable] = {}
        
        # Client connection info
        self.client_info = None
        self.initialized = False
        
        # Message handling
        self.request_handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get
        }
    
    def add_tool(self, tool: McpTool, handler: Callable):
        """Add a tool and its handler"""
        self.tools[tool.name] = tool
        self.tool_handlers[tool.name] = handler
        logger.debug(f"Added tool: {tool.name}")
    
    def add_resource(self, resource: McpResource, handler: Callable):
        """Add a resource and its handler"""
        self.resources[resource.uri] = resource
        self.resource_handlers[resource.uri] = handler
        logger.debug(f"Added resource: {resource.uri}")
    
    def add_prompt(self, prompt: McpPrompt, handler: Callable):
        """Add a prompt and its handler"""
        self.prompts[prompt.name] = prompt
        self.prompt_handlers[prompt.name] = handler
        logger.debug(f"Added prompt: {prompt.name}")
    
    async def handle_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle incoming MCP message
        Returns response message if needed
        """
        try:
            message = McpMessage(**message_data)
            
            # Handle requests
            if message.method:
                return await self._handle_request(message)
            
            # Handle responses (for outgoing requests)
            elif message.id and (message.result is not None or message.error is not None):
                # This would be handled by the client making the request
                return None
            
            else:
                logger.warning(f"Unknown message type: {message_data}")
                return None
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
            # Return error response if we have a request ID
            if isinstance(message_data, dict) and "id" in message_data:
                return {
                    "jsonrpc": "2.0",
                    "id": message_data["id"],
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    }
                }
            
            return None
    
    async def _handle_request(self, message: McpMessage) -> Dict[str, Any]:
        """Handle MCP request message"""
        method = message.method
        params = message.params or {}
        
        try:
            # Check if method is supported
            if method not in self.request_handlers:
                raise McpError(-32601, f"Method not found: {method}")
            
            # Check initialization for most methods
            if method != "initialize" and method != "notifications/initialized" and not self.initialized:
                raise McpError(-32002, "Server not initialized")
            
            # Call handler
            handler = self.request_handlers[method]
            result = await handler(params)
            
            # Return success response
            return {
                "jsonrpc": "2.0",
                "id": message.id,
                "result": result
            }
            
        except McpError as e:
            # Return MCP error
            return {
                "jsonrpc": "2.0",
                "id": message.id,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "data": e.data
                }
            }
        except Exception as e:
            # Return generic error
            logger.error(f"Error handling request {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": message.id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        protocol_version = params.get("protocolVersion")
        client_capabilities = params.get("capabilities", {})
        self.client_info = params.get("clientInfo", {})
        
        # Validate protocol version
        if protocol_version != "2024-11-05":
            logger.warning(f"Unsupported protocol version: {protocol_version}")
        
        self.initialized = True
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
    
    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools_list = []
        for tool in self.tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        
        return {"tools": tools_list}
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise McpError(-32602, "Missing tool name")
        
        if tool_name not in self.tools:
            raise McpError(-32601, f"Tool not found: {tool_name}")
        
        if tool_name not in self.tool_handlers:
            raise McpError(-32603, f"No handler for tool: {tool_name}")
        
        try:
            handler = self.tool_handlers[tool_name]
            result = await handler(arguments)
            
            return {
                "content": result if isinstance(result, list) else [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            raise McpError(-32603, f"Tool execution failed: {str(e)}")
    
    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources_list = []
        for resource in self.resources.values():
            resources_list.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mimeType
            })
        
        return {"resources": resources_list}
    
    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        
        if not uri:
            raise McpError(-32602, "Missing resource URI")
        
        if uri not in self.resources:
            raise McpError(-32601, f"Resource not found: {uri}")
        
        if uri not in self.resource_handlers:
            raise McpError(-32603, f"No handler for resource: {uri}")
        
        try:
            handler = self.resource_handlers[uri]
            result = await handler(params)
            
            return {
                "contents": result if isinstance(result, list) else [
                    {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": str(result)
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Resource {uri} read failed: {e}")
            raise McpError(-32603, f"Resource read failed: {str(e)}")
    
    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts_list = []
        for prompt in self.prompts.values():
            prompts_list.append({
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments or []
            })
        
        return {"prompts": prompts_list}
    
    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not prompt_name:
            raise McpError(-32602, "Missing prompt name")
        
        if prompt_name not in self.prompts:
            raise McpError(-32601, f"Prompt not found: {prompt_name}")
        
        if prompt_name not in self.prompt_handlers:
            raise McpError(-32603, f"No handler for prompt: {prompt_name}")
        
        try:
            handler = self.prompt_handlers[prompt_name]
            result = await handler(arguments)
            
            return {
                "description": self.prompts[prompt_name].description,
                "messages": result if isinstance(result, list) else [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": str(result)
                        }
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Prompt {prompt_name} execution failed: {e}")
            raise McpError(-32603, f"Prompt execution failed: {str(e)}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities,
            "tools_count": len(self.tools),
            "resources_count": len(self.resources),
            "prompts_count": len(self.prompts),
            "initialized": self.initialized,
            "client_info": self.client_info
        }
    
    async def notify_client(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send notification to client"""
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
    
    async def send_progress(self, progress_id: str, progress: float, total: Optional[float] = None) -> Dict[str, Any]:
        """Send progress notification"""
        return await self.notify_client("notifications/progress", {
            "progressId": progress_id,
            "progress": progress,
            "total": total
        })
    
    async def send_log(self, level: str, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
        """Send log notification"""
        return await self.notify_client("notifications/message", {
            "level": level,
            "logger": self.name,
            "data": {
                "message": message,
                "data": data
            }
        })


class McpServerManager:
    """
    Manager for running MCP server with transport
    """
    
    def __init__(self, server: McpServer):
        self.server = server
        self.transport = None
        self.running = False
        
    async def run_stdio(self):
        """Run server with stdio transport"""
        import sys
        
        self.running = True
        logger.info(f"Starting MCP server {self.server.name} with stdio transport")
        
        try:
            # Read from stdin, write to stdout
            while self.running:
                try:
                    # Read line from stdin
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )
                    
                    if not line:
                        break
                    
                    # Parse message
                    message_data = json.loads(line.strip())
                    
                    # Handle message
                    response = await self.server.handle_message(message_data)
                    
                    # Send response if needed
                    if response:
                        response_json = json.dumps(response)
                        print(response_json, flush=True)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.running = False
            logger.info("MCP server stopped")
    
    async def run_http(self, host: str = "localhost", port: int = 8000):
        """Run server with HTTP transport"""
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        import uvicorn
        
        app = FastAPI(title=self.server.name)
        
        @app.post("/mcp")
        async def handle_mcp_request(request: Request):
            try:
                message_data = await request.json()
                response = await self.server.handle_message(message_data)
                return response or {}
            except Exception as e:
                logger.error(f"HTTP request error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"error": str(e)}
                )
        
        @app.get("/health")
        async def health_check():
            return self.server.get_server_info()
        
        logger.info(f"Starting MCP server {self.server.name} on {host}:{port}")
        
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def stop(self):
        """Stop the server"""
        self.running = False