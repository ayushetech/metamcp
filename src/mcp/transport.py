"""
MCP Transport Layer Implementation
Handles different transport types for MCP communication
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass
import httpx
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


@dataclass
class TransportConfig:
    """Transport configuration"""
    transport_type: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


class Transport(ABC):
    """Base transport class for MCP communication"""
    
    def __init__(self, config: TransportConfig):
        self.config = config
        self.connected = False
        self.message_handler: Optional[Callable] = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the transport"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the transport"""
        pass
    
    @abstractmethod
    async def send_message(self, message: Dict[str, Any]):
        """Send a message"""
        pass
    
    def set_message_handler(self, handler: Callable):
        """Set message handler for incoming messages"""
        self.message_handler = handler


class StdioTransport(Transport):
    """Standard I/O transport for subprocess-based MCP servers"""
    
    def __init__(self, config: TransportConfig, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.command = command
        self.args = args
        self.env = env or {}
        self.process = None
        self._read_task = None
    
    async def connect(self) -> bool:
        """Start subprocess and connect via stdio"""
        try:
            # Prepare environment
            import os
            full_env = os.environ.copy()
            full_env.update(self.env)
            
            # Start subprocess
            # Windows compatibility fix
            import platform
            import shutil
            if platform.system() == "Windows":
                # On Windows, find the actual executable
                if self.command == "npx":
                    npx_path = shutil.which("npx.cmd") or shutil.which("npx")
                    if npx_path:
                        self.process = await asyncio.create_subprocess_exec(
                            npx_path, *self.args,
                            stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            env=full_env
                        )
                    else:
                        raise FileNotFoundError("npx not found in PATH")
                elif self.command == "npm":
                    npm_path = shutil.which("npm.cmd") or shutil.which("npm")
                    if npm_path:
                        self.process = await asyncio.create_subprocess_exec(
                            npm_path, *self.args,
                            stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            env=full_env
                        )
                    else:
                        raise FileNotFoundError("npm not found in PATH")
                else:
                    # Other commands, try as-is
                    self.process = await asyncio.create_subprocess_exec(
                        self.command, *self.args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=full_env
                    )
            else:
                # Unix/Linux
                self.process = await asyncio.create_subprocess_exec(
                    self.command, *self.args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=full_env
                )
            
            # Start reading messages
            self._read_task = asyncio.create_task(self._read_messages())
            
            self.connected = True
            logger.info(f"Connected via stdio: {self.command} {' '.join(self.args)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect via stdio: {e}")
            return False
    
    async def disconnect(self):
        """Terminate subprocess"""
        self.connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.warning(f"Error terminating process: {e}")
        
        logger.info("Disconnected from stdio transport")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to subprocess stdin"""
        if not self.connected or not self.process:
            raise RuntimeError("Transport not connected")
        
        try:
            message_json = json.dumps(message) + '\n'
            self.process.stdin.write(message_json.encode())
            await self.process.stdin.drain()
            logger.debug(f"Sent stdio message: {message.get('method', 'response')}")
        except Exception as e:
            logger.error(f"Failed to send stdio message: {e}")
            raise
    
    async def _read_messages(self):
        """Read messages from subprocess stdout"""
        if not self.process:
            return
        
        try:
            async for line in self.process.stdout:
                if not line.strip():
                    continue
                
                try:
                    message = json.loads(line.decode().strip())
                    if self.message_handler:
                        await self.message_handler(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse stdio message: {e}")
                except Exception as e:
                    logger.error(f"Error handling stdio message: {e}")
        except Exception as e:
            if self.connected:
                logger.error(f"Error reading stdio messages: {e}")


class SseTransport(Transport):
    """Server-Sent Events transport for remote MCP servers"""
    
    def __init__(self, config: TransportConfig, url: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.url = url
        self.headers = headers or {}
        self.client = None
        self._read_task = None
    
    async def connect(self) -> bool:
        """Connect to SSE endpoint"""
        try:
            self.client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers=self.headers
            )
            
            # Start SSE connection
            self._read_task = asyncio.create_task(self._read_sse_stream())
            
            self.connected = True
            logger.info(f"Connected via SSE: {self.url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect via SSE: {e}")
            return False
    
    async def disconnect(self):
        """Close SSE connection"""
        self.connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self.client:
            await self.client.aclose()
        
        logger.info("Disconnected from SSE transport")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message via HTTP POST"""
        if not self.connected or not self.client:
            raise RuntimeError("Transport not connected")
        
        try:
            # Determine endpoint for message posting
            post_url = self.url.replace('/sse', '/messages')
            response = await self.client.post(post_url, json=message)
            response.raise_for_status()
            logger.debug(f"Sent SSE message: {message.get('method', 'response')}")
        except Exception as e:
            logger.error(f"Failed to send SSE message: {e}")
            raise
    
    async def _read_sse_stream(self):
        """Read Server-Sent Events stream"""
        if not self.client:
            return
        
        try:
            async with self.client.stream("GET", self.url) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data = line[6:]  # Remove "data: " prefix
                    if not data.strip():
                        continue
                    
                    try:
                        message = json.loads(data)
                        if self.message_handler:
                            await self.message_handler(message)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse SSE message: {e}")
                    except Exception as e:
                        logger.error(f"Error handling SSE message: {e}")
                        
        except Exception as e:
            if self.connected:
                logger.error(f"Error reading SSE stream: {e}")


class HttpTransport(Transport):
    """HTTP transport for request/response MCP communication"""
    
    def __init__(self, config: TransportConfig, base_url: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.client = None
    
    async def connect(self) -> bool:
        """Initialize HTTP client"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.config.timeout,
                headers=self.headers
            )
            
            # Test connection
            response = await self.client.get("/health")
            if response.status_code == 200:
                self.connected = True
                logger.info(f"Connected via HTTP: {self.base_url}")
                return True
            else:
                logger.warning(f"HTTP health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect via HTTP: {e}")
            return False
    
    async def disconnect(self):
        """Close HTTP client"""
        self.connected = False
        
        if self.client:
            await self.client.aclose()
        
        logger.info("Disconnected from HTTP transport")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message via HTTP POST and return response"""
        if not self.connected or not self.client:
            raise RuntimeError("Transport not connected")
        
        try:
            response = await self.client.post("/mcp", json=message)
            response.raise_for_status()
            
            # Handle response immediately for HTTP transport
            response_data = response.json()
            if self.message_handler:
                await self.message_handler(response_data)
            
            logger.debug(f"Sent HTTP message: {message.get('method', 'response')}")
            
        except Exception as e:
            logger.error(f"Failed to send HTTP message: {e}")
            raise


class WebSocketTransport(Transport):
    """WebSocket transport for bidirectional MCP communication"""
    
    def __init__(self, config: TransportConfig, uri: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.uri = uri
        self.headers = headers or {}
        self.websocket = None
        self._read_task = None
    
    async def connect(self) -> bool:
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(
                self.uri,
                extra_headers=self.headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Start reading messages
            self._read_task = asyncio.create_task(self._read_messages())
            
            self.connected = True
            logger.info(f"Connected via WebSocket: {self.uri}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect via WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        self.connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        logger.info("Disconnected from WebSocket transport")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message via WebSocket"""
        if not self.connected or not self.websocket:
            raise RuntimeError("Transport not connected")
        
        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            logger.debug(f"Sent WebSocket message: {message.get('method', 'response')}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise
    
    async def _read_messages(self):
        """Read messages from WebSocket"""
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if self.message_handler:
                        await self.message_handler(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    
        except ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            if self.connected:
                logger.error(f"Error reading WebSocket messages: {e}")


def create_transport(transport_type: str, config: TransportConfig, **kwargs) -> Transport:
    """Factory function to create transport instances"""
    
    if transport_type == "stdio":
        return StdioTransport(
            config,
            command=kwargs.get("command", ""),
            args=kwargs.get("args", []),
            env=kwargs.get("env", {})
        )
    
    elif transport_type == "sse":
        return SseTransport(
            config,
            url=kwargs.get("url", ""),
            headers=kwargs.get("headers", {})
        )
    
    elif transport_type == "http":
        return HttpTransport(
            config,
            base_url=kwargs.get("base_url", ""),
            headers=kwargs.get("headers", {})
        )
    
    elif transport_type == "websocket":
        return WebSocketTransport(
            config,
            uri=kwargs.get("uri", ""),
            headers=kwargs.get("headers", {})
        )
    
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")