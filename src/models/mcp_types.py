# src/models/mcp_types.py
"""
MCP Protocol Data Types
Defines all data structures for the Model Context Protocol
"""

from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import uuid


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


class McpCapabilities(BaseModel):
    """MCP Server/Client Capabilities"""
    tools: bool = True
    resources: bool = True
    prompts: bool = True
    sampling: bool = False
    experimental: Dict[str, bool] = Field(default_factory=dict)


class McpServerInfo(BaseModel):
    """MCP Server Information"""
    name: str
    version: str


class McpClientInfo(BaseModel):
    """MCP Client Information"""
    name: str
    version: str


class McpTool(BaseModel):
    """MCP Tool Definition"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: Dict[str, Any] = Field(..., description="JSON Schema for tool input")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()


class McpResource(BaseModel):
    """MCP Resource Definition"""
    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    mimeType: Optional[str] = Field(None, description="MIME type")
    
    @validator('uri')
    def validate_uri(cls, v):
        if not v or not v.strip():
            raise ValueError("Resource URI cannot be empty")
        return v.strip()


class McpPrompt(BaseModel):
    """MCP Prompt Definition"""
    name: str = Field(..., description="Prompt name")
    description: str = Field(..., description="Prompt description")
    arguments: Optional[List[Dict[str, Any]]] = Field(None, description="Prompt arguments schema")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Prompt name cannot be empty")
        return v.strip()


class McpMessage(BaseModel):
    """Base MCP Message"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(None, description="Message ID")
    method: Optional[str] = Field(None, description="Method name for requests")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")
    result: Optional[Any] = Field(None, description="Result for responses")
    error: Optional[Dict[str, Any]] = Field(None, description="Error for error responses")
    
    @validator('jsonrpc')
    def validate_jsonrpc(cls, v):
        if v != "2.0":
            raise ValueError("JSON-RPC version must be 2.0")
        return v


class McpError(BaseModel):
    """MCP Error Details"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")


class McpInitializeRequest(BaseModel):
    """MCP Initialize Request"""
    protocolVersion: str = Field(..., description="MCP protocol version")
    capabilities: McpCapabilities = Field(..., description="Client capabilities")
    clientInfo: McpClientInfo = Field(..., description="Client information")


class McpInitializeResponse(BaseModel):
    """MCP Initialize Response"""
    protocolVersion: str = Field(..., description="MCP protocol version")
    capabilities: McpCapabilities = Field(..., description="Server capabilities")
    serverInfo: McpServerInfo = Field(..., description="Server information")


class McpToolsListRequest(BaseModel):
    """MCP Tools List Request"""
    cursor: Optional[str] = Field(None, description="Pagination cursor")


class McpToolsListResponse(BaseModel):
    """MCP Tools List Response"""
    tools: List[McpTool] = Field(..., description="Available tools")
    nextCursor: Optional[str] = Field(None, description="Next pagination cursor")


class McpToolCallRequest(BaseModel):
    """MCP Tool Call Request"""
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class McpToolCallResponse(BaseModel):
    """MCP Tool Call Response"""
    content: List[Dict[str, Any]] = Field(..., description="Tool result content")
    isError: bool = Field(default=False, description="Whether the result is an error")


class McpResourcesListRequest(BaseModel):
    """MCP Resources List Request"""
    cursor: Optional[str] = Field(None, description="Pagination cursor")


class McpResourcesListResponse(BaseModel):
    """MCP Resources List Response"""
    resources: List[McpResource] = Field(..., description="Available resources")
    nextCursor: Optional[str] = Field(None, description="Next pagination cursor")


class McpResourceReadRequest(BaseModel):
    """MCP Resource Read Request"""
    uri: str = Field(..., description="Resource URI")


class McpResourceContent(BaseModel):
    """MCP Resource Content"""
    uri: str = Field(..., description="Resource URI")
    mimeType: Optional[str] = Field(None, description="Content MIME type")
    text: Optional[str] = Field(None, description="Text content")
    blob: Optional[str] = Field(None, description="Base64 encoded binary content")


class McpResourceReadResponse(BaseModel):
    """MCP Resource Read Response"""
    contents: List[McpResourceContent] = Field(..., description="Resource contents")


class McpPromptsListRequest(BaseModel):
    """MCP Prompts List Request"""
    cursor: Optional[str] = Field(None, description="Pagination cursor")


class McpPromptsListResponse(BaseModel):
    """MCP Prompts List Response"""
    prompts: List[McpPrompt] = Field(..., description="Available prompts")
    nextCursor: Optional[str] = Field(None, description="Next pagination cursor")


class McpPromptGetRequest(BaseModel):
    """MCP Prompt Get Request"""
    name: str = Field(..., description="Prompt name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Prompt arguments")


class McpPromptMessage(BaseModel):
    """MCP Prompt Message"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: Dict[str, Any] = Field(..., description="Message content")


class McpPromptGetResponse(BaseModel):
    """MCP Prompt Get Response"""
    description: Optional[str] = Field(None, description="Prompt description")
    messages: List[McpPromptMessage] = Field(..., description="Prompt messages")
