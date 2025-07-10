# tests/test_mcp_client.py
"""
Unit tests for MCP Client functionality
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from src.mcp.protocol import McpClient, TransportType, McpError
from src.mcp.transport import TransportConfig


class TestMcpClient:
    """Test MCP Client functionality"""

    @pytest.fixture
    def transport_config(self):
        return TransportConfig(
            transport_type="stdio",
            timeout=30.0,
            max_retries=3
        )

    @pytest.fixture  
    def mcp_client(self, transport_config):
        return McpClient(
            transport_type=TransportType.STDIO,
            **{"command": "echo", "args": ["test"]}
        )

    @pytest.mark.asyncio
    async def test_client_initialization(self, mcp_client):
        """Test client initialization"""
        assert mcp_client.transport_type == TransportType.STDIO
        assert not mcp_client.connected
        assert len(mcp_client.tools) == 0

    @pytest.mark.asyncio
    async def test_connect_stdio_success(self, mcp_client):
        """Test successful stdio connection"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_subprocess.return_value = mock_process
            
            success = await mcp_client.connect()
            assert success
            assert mcp_client.connected

    @pytest.mark.asyncio 
    async def test_connect_stdio_failure(self, mcp_client):
        """Test failed stdio connection"""
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Connection failed")):
            success = await mcp_client.connect()
            assert not success
            assert not mcp_client.connected

    @pytest.mark.asyncio
    async def test_request_response_cycle(self, mcp_client):
        """Test request-response cycle"""
        mcp_client.connected = True
        mcp_client._process = AsyncMock()
        
        # Mock response handling
        async def mock_send_message(message):
            # Simulate response
            response_message = {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {"tools": []}
            }
            await mcp_client._handle_message(response_message)
        
        mcp_client._send_message = mock_send_message
        
        result = await mcp_client.request("tools/list")
        assert result == {"tools": []}

    @pytest.mark.asyncio
    async def test_request_timeout(self, mcp_client):
        """Test request timeout"""
        mcp_client.connected = True
        mcp_client._process = AsyncMock()
        
        # Mock that never responds
        async def mock_send_message(message):
            pass
        
        mcp_client._send_message = mock_send_message
        
        with pytest.raises(McpError) as exc_info:
            await mcp_client.request("tools/list")
        
        assert exc_info.value.code == -32001  # Timeout error

    @pytest.mark.asyncio
    async def test_tool_discovery(self, mcp_client):
        """Test tool discovery"""
        mcp_client.connected = True
        
        mock_tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {"type": "object"}
            }
        ]
        
        with patch.object(mcp_client, 'request', return_value={"tools": mock_tools}):
            await mcp_client._discover_capabilities()
            
            assert len(mcp_client.tools) == 1
            assert mcp_client.tools[0].name == "test_tool"

    @pytest.mark.asyncio
    async def test_disconnect(self, mcp_client):
        """Test client disconnection"""
        mcp_client.connected = True
        mcp_client._process = AsyncMock()
        
        await mcp_client.disconnect()
        
        assert not mcp_client.connected
        mcp_client._process.terminate.assert_called_once()
