"""
Meta MCP Server Registry - Fixed SQLAlchemy model
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, Text, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Import with fallback
try:
    from ..mcp.protocol import McpClient, TransportType, McpCapabilities
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp.protocol import McpClient, TransportType, McpCapabilities

logger = logging.getLogger(__name__)

Base = declarative_base()


class ServerStatus(str, Enum):
    """MCP Server Status"""
    REGISTERING = "registering"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class McpServerModel(Base):
    """SQLAlchemy model for MCP servers"""
    __tablename__ = "mcp_servers"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    transport_type = Column(String, nullable=False)
    transport_config = Column(JSON, nullable=False)
    status = Column(String, default=ServerStatus.INACTIVE.value)
    capabilities = Column(JSON)
    tools_count = Column(Integer, default=0)
    resources_count = Column(Integer, default=0)
    prompts_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_health_check = Column(DateTime)
    health_check_failures = Column(Integer, default=0)
    server_metadata = Column(JSON, default=dict)  # Changed from 'metadata' to 'server_metadata'


class McpServerRegistration(BaseModel):
    """MCP Server Registration Request"""
    name: str = Field(..., description="Unique server name")
    description: Optional[str] = Field(None, description="Server description")
    transport_type: TransportType = Field(..., description="Transport type")
    transport_config: Dict[str, Any] = Field(..., description="Transport configuration")
    auto_connect: bool = Field(True, description="Auto-connect on registration")
    health_check_interval: int = Field(60, description="Health check interval in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


@dataclass
class McpServerInstance:
    """Runtime MCP Server Instance"""
    id: str
    name: str
    client: McpClient
    registration: McpServerRegistration
    status: ServerStatus = ServerStatus.INACTIVE
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    tools: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)


class McpServerRegistry:
    """
    MCP Server Registry
    Manages lifecycle of MCP servers including registration, connection, health monitoring
    """
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///./meta_mcp.db"):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        
        # Runtime instances
        self.servers: Dict[str, McpServerInstance] = {}
        self.active_clients: Dict[str, McpClient] = {}
        
        # Health monitoring
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self.health_check_interval = 60  # seconds
        
        # Known MCP server templates
        self.server_templates = self._load_server_templates()
    
    async def initialize(self):
        """Initialize the registry"""
        try:
            # Setup database
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                future=True
            )
            
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Load existing servers
            await self._load_existing_servers()
            
            logger.info("MCP Server Registry initialized")
        except Exception as e:
            logger.error(f"Failed to initialize registry: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the registry"""
        try:
            # Stop health monitoring
            for task in self.health_check_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.health_check_tasks:
                await asyncio.gather(*self.health_check_tasks.values(), return_exceptions=True)
            
            # Disconnect all clients
            for client in self.active_clients.values():
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")
            
            # Close database
            if self.engine:
                await self.engine.dispose()
            
            logger.info("MCP Server Registry shutdown complete")
        except Exception as e:
            logger.error(f"Error during registry shutdown: {e}")
    
    async def register_server(self, registration: McpServerRegistration) -> str:
        """Register a new MCP server"""
        server_id = str(uuid.uuid4())
        
        try:
            # Create database record
            async with self.session_factory() as session:
                server_model = McpServerModel(
                    id=server_id,
                    name=registration.name,
                    description=registration.description,
                    transport_type=registration.transport_type.value,
                    transport_config=registration.transport_config,
                    status=ServerStatus.REGISTERING.value,
                    server_metadata=registration.metadata  # Use server_metadata instead of metadata
                )
                session.add(server_model)
                await session.commit()
            
            # Create runtime instance
            client = McpClient(
                transport_type=registration.transport_type,
                **registration.transport_config
            )
            
            instance = McpServerInstance(
                id=server_id,
                name=registration.name,
                client=client,
                registration=registration,
                status=ServerStatus.REGISTERING
            )
            
            self.servers[server_id] = instance
            
            # Auto-connect if requested
            if registration.auto_connect:
                await self._connect_server(server_id)
            
            logger.info(f"Registered MCP server: {registration.name} ({server_id})")
            return server_id
            
        except Exception as e:
            logger.error(f"Failed to register server {registration.name}: {e}")
            # Cleanup on failure
            if server_id in self.servers:
                del self.servers[server_id]
            raise
    
    async def unregister_server(self, server_id: str) -> bool:
        """Unregister an MCP server"""
        try:
            # Disconnect if connected
            if server_id in self.active_clients:
                await self._disconnect_server(server_id)
            
            # Remove from runtime
            if server_id in self.servers:
                del self.servers[server_id]
            
            # Remove from database
            async with self.session_factory() as session:
                result = await session.execute(
                    select(McpServerModel).where(McpServerModel.id == server_id)
                )
                server_model = result.scalar_one_or_none()
                if server_model:
                    await session.delete(server_model)
                    await session.commit()
            
            logger.info(f"Unregistered MCP server: {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister server {server_id}: {e}")
            return False
    
    async def connect_server(self, server_id: str) -> bool:
        """Connect to an MCP server"""
        return await self._connect_server(server_id)
    
    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from an MCP server"""
        return await self._disconnect_server(server_id)
    
    async def _connect_server(self, server_id: str) -> bool:
        """Internal method to connect to a server"""
        if server_id not in self.servers:
            logger.error(f"Server not found: {server_id}")
            return False
        
        instance = self.servers[server_id]
        
        try:
            # Connect the client
            success = await instance.client.connect()
            
            if success:
                instance.status = ServerStatus.ACTIVE
                self.active_clients[server_id] = instance.client
                
                # Update capabilities
                await self._update_server_capabilities(server_id)
                
                # Start health monitoring
                await self._start_health_monitoring(server_id)
                
                # Update database
                await self._update_server_status(server_id, ServerStatus.ACTIVE)
                
                logger.info(f"Connected to MCP server: {instance.name}")
                return True
            else:
                instance.status = ServerStatus.ERROR
                await self._update_server_status(server_id, ServerStatus.ERROR)
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to server {instance.name}: {e}")
            instance.status = ServerStatus.ERROR
            await self._update_server_status(server_id, ServerStatus.ERROR)
            return False
    
    async def _disconnect_server(self, server_id: str) -> bool:
        """Internal method to disconnect from a server"""
        if server_id not in self.servers:
            return False
        
        instance = self.servers[server_id]
        
        try:
            # Stop health monitoring
            await self._stop_health_monitoring(server_id)
            
            # Disconnect client
            if instance.client:
                await instance.client.disconnect()
            
            # Update status
            instance.status = ServerStatus.INACTIVE
            
            # Remove from active clients
            if server_id in self.active_clients:
                del self.active_clients[server_id]
            
            # Update database
            await self._update_server_status(server_id, ServerStatus.INACTIVE)
            
            logger.info(f"Disconnected from MCP server: {instance.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect from server {instance.name}: {e}")
            return False
    
    async def _update_server_capabilities(self, server_id: str):
        """Update server capabilities after connection"""
        if server_id not in self.servers:
            return
        
        instance = self.servers[server_id]
        client = instance.client
        
        try:
            # Update tools, resources, prompts
            instance.tools = [tool.name for tool in client.tools]
            instance.resources = [resource.uri for resource in client.resources]
            instance.prompts = [prompt.name for prompt in client.prompts]
            
            # Update database
            async with self.session_factory() as session:
                result = await session.execute(
                    select(McpServerModel).where(McpServerModel.id == server_id)
                )
                server_model = result.scalar_one_or_none()
                if server_model:
                    server_model.capabilities = client.capabilities.__dict__
                    server_model.tools_count = len(client.tools)
                    server_model.resources_count = len(client.resources)
                    server_model.prompts_count = len(client.prompts)
                    server_model.updated_at = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update capabilities for {server_id}: {e}")
    
    async def _start_health_monitoring(self, server_id: str):
        """Start health monitoring for a server"""
        if server_id in self.health_check_tasks:
            self.health_check_tasks[server_id].cancel()
        
        instance = self.servers[server_id]
        interval = instance.registration.health_check_interval
        
        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self._perform_health_check(server_id)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health check error for {server_id}: {e}")
        
        task = asyncio.create_task(health_check_loop())
        self.health_check_tasks[server_id] = task
    
    async def _stop_health_monitoring(self, server_id: str):
        """Stop health monitoring for a server"""
        if server_id in self.health_check_tasks:
            self.health_check_tasks[server_id].cancel()
            try:
                await self.health_check_tasks[server_id]
            except asyncio.CancelledError:
                pass
            del self.health_check_tasks[server_id]
    
    async def _perform_health_check(self, server_id: str):
        """Perform health check on a server"""
        if server_id not in self.servers:
            return
        
        instance = self.servers[server_id]
        client = instance.client
        
        try:
            # Simple connectivity check
            if not client.connected:
                raise Exception("Client not connected")
            
            # Try to list tools (lightweight operation)
            await client.request("tools/list")
            
            # Health check passed
            instance.last_health_check = datetime.utcnow()
            instance.health_check_failures = 0
            
            if instance.status != ServerStatus.ACTIVE:
                instance.status = ServerStatus.ACTIVE
                await self._update_server_status(server_id, ServerStatus.ACTIVE)
            
            # Update database
            async with self.session_factory() as session:
                result = await session.execute(
                    select(McpServerModel).where(McpServerModel.id == server_id)
                )
                server_model = result.scalar_one_or_none()
                if server_model:
                    server_model.last_health_check = instance.last_health_check
                    server_model.health_check_failures = instance.health_check_failures
                    await session.commit()
            
        except Exception as e:
            # Health check failed
            instance.health_check_failures += 1
            logger.warning(f"Health check failed for {instance.name}: {e}")
            
            # Mark as error after multiple failures
            if instance.health_check_failures >= 3:
                instance.status = ServerStatus.ERROR
                await self._update_server_status(server_id, ServerStatus.ERROR)
    
    async def _update_server_status(self, server_id: str, status: ServerStatus):
        """Update server status in database"""
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(McpServerModel).where(McpServerModel.id == server_id)
                )
                server_model = result.scalar_one_or_none()
                if server_model:
                    server_model.status = status.value
                    server_model.updated_at = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update server status: {e}")
    
    async def _load_existing_servers(self):
        """Load existing servers from database"""
        try:
            async with self.session_factory() as session:
                result = await session.execute(select(McpServerModel))
                servers = result.scalars().all()
                
                for server_data in servers:
                    # Create registration
                    registration = McpServerRegistration(
                        name=server_data.name,
                        description=server_data.description,
                        transport_type=TransportType(server_data.transport_type),
                        transport_config=server_data.transport_config,
                        metadata=server_data.server_metadata or {}  # Use server_metadata
                    )
                    
                    # Create client
                    client = McpClient(
                        transport_type=registration.transport_type,
                        **registration.transport_config
                    )
                    
                    # Create instance
                    instance = McpServerInstance(
                        id=server_data.id,
                        name=server_data.name,
                        client=client,
                        registration=registration,
                        status=ServerStatus(server_data.status),
                        last_health_check=server_data.last_health_check,
                        health_check_failures=server_data.health_check_failures
                    )
                    
                    self.servers[server_data.id] = instance
                    
                    # Auto-connect if was active
                    if server_data.status == ServerStatus.ACTIVE.value:
                        asyncio.create_task(self._connect_server(server_data.id))
        except Exception as e:
            logger.error(f"Failed to load existing servers: {e}")
    
    def get_server(self, server_id: str) -> Optional[McpServerInstance]:
        """Get server instance by ID"""
        return self.servers.get(server_id)
    
    def get_server_by_name(self, name: str) -> Optional[McpServerInstance]:
        """Get server instance by name"""
        for instance in self.servers.values():
            if instance.name == name:
                return instance
        return None
    
    def list_servers(self) -> List[McpServerInstance]:
        """List all registered servers"""
        return list(self.servers.values())
    
    def list_active_servers(self) -> List[McpServerInstance]:
        """List only active servers"""
        return [instance for instance in self.servers.values() 
                if instance.status == ServerStatus.ACTIVE]
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_servers = len(self.servers)
        active_servers = len([s for s in self.servers.values() if s.status == ServerStatus.ACTIVE])
        
        total_tools = sum(len(s.tools) for s in self.servers.values())
        total_resources = sum(len(s.resources) for s in self.servers.values())
        total_prompts = sum(len(s.prompts) for s in self.servers.values())
        
        return {
            "total_servers": total_servers,
            "active_servers": active_servers,
            "inactive_servers": total_servers - active_servers,
            "total_tools": total_tools,
            "total_resources": total_resources,
            "total_prompts": total_prompts,
            "server_details": {
                server_id: {
                    "name": instance.name,
                    "status": instance.status.value,
                    "tools_count": len(instance.tools),
                    "resources_count": len(instance.resources),
                    "prompts_count": len(instance.prompts),
                    "last_health_check": instance.last_health_check.isoformat() if instance.last_health_check else None
                }
                for server_id, instance in self.servers.items()
            }
        }
    
    def _load_server_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load known MCP server templates for easy registration"""
        return {
            "github": {
                "name": "github-mcp",
                "description": "Official GitHub MCP server for repository management",
                "transport_type": "stdio",
                "transport_config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
                    }
                }
            },
            "filesystem": {
                "name": "filesystem-mcp",
                "description": "Official filesystem MCP server for file operations",
                "transport_type": "stdio",
                "transport_config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                }
            },
            "postgres": {
                "name": "postgres-mcp",
                "description": "Official PostgreSQL MCP server for database access",
                "transport_type": "stdio",
                "transport_config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/postgres"]
                }
            },
            "weather": {
                "name": "weather-mcp",
                "description": "Weather information MCP server",
                "transport_type": "stdio",
                "transport_config": {
                    "command": "npx",
                    "args": ["-y", "@h1deya/mcp-server-weather"]
                }
            },
            "memory": {
                "name": "memory-mcp",
                "description": "Official memory MCP server for persistent storage",
                "transport_type": "stdio",
                "transport_config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-memory"]
                }
            },
            "slack": {
                "name": "slack-mcp",
                "description": "Slack workspace integration MCP server",
                "transport_type": "stdio",
                "transport_config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-slack"],
                    "env": {
                        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
                        "SLACK_TEAM_ID": "${SLACK_TEAM_ID}"
                    }
                }
            }
        }
    
    async def register_template_server(self, template_name: str, env_vars: Dict[str, str] = None) -> str:
        """Register a server from template"""
        if template_name not in self.server_templates:
            raise ValueError(f"Unknown server template: {template_name}")
        
        template = self.server_templates[template_name].copy()
        
        # Replace environment variables
        if env_vars:
            transport_config = template["transport_config"].copy()
            if "env" in transport_config:
                for key, value in transport_config["env"].items():
                    if value.startswith("${") and value.endswith("}"):
                        env_key = value[2:-1]
                        if env_key in env_vars:
                            transport_config["env"][key] = env_vars[env_key]
            template["transport_config"] = transport_config
        
        # Create registration
        registration = McpServerRegistration(
            name=template["name"],
            description=template["description"],
            transport_type=TransportType(template["transport_type"]),
            transport_config=template["transport_config"]
        )
        
        return await self.register_server(registration)


# Global registry instance
_registry: Optional[McpServerRegistry] = None


def get_registry() -> McpServerRegistry:
    """Get the global registry instance"""
    global _registry
    if _registry is None:
        _registry = McpServerRegistry()
    return _registry