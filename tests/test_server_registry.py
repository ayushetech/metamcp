# tests/test_server_registry.py
"""
Unit tests for MCP Server Registry
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from src.core.registry import McpServerRegistry, McpServerRegistration, TransportType, ServerStatus


class TestMcpServerRegistry:
    """Test MCP Server Registry functionality"""

    @pytest.fixture
    async def registry(self):
        registry = McpServerRegistry("sqlite+aiosqlite:///:memory:")
        await registry.initialize()
        yield registry
        await registry.shutdown()

    @pytest.fixture
    def sample_registration(self):
        return McpServerRegistration(
            name="test-server",
            description="A test server",
            transport_type=TransportType.STDIO,
            transport_config={
                "command": "echo",
                "args": ["test"]
            }
        )

    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initialization"""
        assert registry.engine is not None
        assert registry.session_factory is not None

    @pytest.mark.asyncio
    async def test_register_server(self, registry, sample_registration):
        """Test server registration"""
        server_id = await registry.register_server(sample_registration)
        
        assert server_id is not None
        assert len(server_id) > 0
        
        # Check server is in registry
        server = registry.get_server(server_id)
        assert server is not None
        assert server.name == "test-server"

    @pytest.mark.asyncio
    async def test_register_duplicate_server(self, registry, sample_registration):
        """Test registering server with duplicate name"""
        # Register first server
        await registry.register_server(sample_registration)
        
        # Try to register with same name
        server_id2 = await registry.register_server(sample_registration)
        
        # Should update existing server
        assert server_id2 is not None

    @pytest.mark.asyncio
    async def test_unregister_server(self, registry, sample_registration):
        """Test server unregistration"""
        server_id = await registry.register_server(sample_registration)
        
        success = await registry.unregister_server(server_id)
        assert success
        
        # Server should be removed
        server = registry.get_server(server_id)
        assert server is None

    @pytest.mark.asyncio
    async def test_connect_server(self, registry, sample_registration):
        """Test server connection"""
        server_id = await registry.register_server(sample_registration)
        
        with patch.object(registry, '_connect_server', return_value=True) as mock_connect:
            success = await registry.connect_server(server_id)
            assert success
            mock_connect.assert_called_once_with(server_id)

    @pytest.mark.asyncio
    async def test_list_servers(self, registry, sample_registration):
        """Test listing servers"""
        # Register multiple servers
        await registry.register_server(sample_registration)
        
        sample_registration.name = "test-server-2"
        await registry.register_server(sample_registration)
        
        servers = registry.list_servers()
        assert len(servers) == 2

    @pytest.mark.asyncio
    async def test_get_server_by_name(self, registry, sample_registration):
        """Test getting server by name"""
        await registry.register_server(sample_registration)
        
        server = registry.get_server_by_name("test-server")
        assert server is not None
        assert server.name == "test-server"

    @pytest.mark.asyncio
    async def test_health_monitoring(self, registry, sample_registration):
        """Test health monitoring functionality"""
        server_id = await registry.register_server(sample_registration)
        
        with patch.object(registry, '_perform_health_check') as mock_health:
            await registry._start_health_monitoring(server_id)
            
            # Wait a bit for health check to run
            await asyncio.sleep(0.1)
            
            await registry._stop_health_monitoring(server_id)

