# src/models/registry_types.py
"""
Registry-specific Data Types
Data structures for server registration and management
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .mcp_types import TransportType


class ServerStatus(str, Enum):
    """Server Status Values"""
    REGISTERING = "registering"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    DISCONNECTED = "disconnected"


class HealthStatus(str, Enum):
    """Health Status Values"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class McpServerRegistration(BaseModel):
    """MCP Server Registration Request"""
    name: str = Field(..., description="Unique server name")
    description: Optional[str] = Field(None, description="Server description")
    transport_type: TransportType = Field(..., description="Transport type")
    transport_config: Dict[str, Any] = Field(..., description="Transport configuration")
    auto_connect: bool = Field(True, description="Auto-connect on registration")
    health_check_interval: int = Field(60, description="Health check interval in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Server name cannot be empty")
        # Convert to lowercase and replace spaces with hyphens
        return v.strip().lower().replace(' ', '-')
    
    @validator('health_check_interval')
    def validate_health_interval(cls, v):
        if v < 10 or v > 3600:
            raise ValueError("Health check interval must be between 10 and 3600 seconds")
        return v


class McpServerInfo(BaseModel):
    """Complete MCP Server Information"""
    id: str = Field(..., description="Server ID")
    name: str = Field(..., description="Server name")
    description: Optional[str] = Field(None, description="Server description")
    status: ServerStatus = Field(..., description="Current status")
    transport_type: TransportType = Field(..., description="Transport type")
    transport_config: Dict[str, Any] = Field(..., description="Transport configuration")
    
    # Capabilities
    tools_count: int = Field(default=0, description="Number of available tools")
    resources_count: int = Field(default=0, description="Number of available resources")
    prompts_count: int = Field(default=0, description="Number of available prompts")
    
    # Timestamps
    registered_at: datetime = Field(..., description="Registration timestamp")
    last_connected: Optional[datetime] = Field(None, description="Last connection timestamp")
    last_health_check: Optional[datetime] = Field(None, description="Last health check timestamp")
    
    # Health information
    health_status: HealthStatus = Field(default=HealthStatus.UNKNOWN, description="Health status")
    health_check_failures: int = Field(default=0, description="Consecutive health check failures")
    avg_response_time: float = Field(default=0.0, description="Average response time in seconds")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class McpServerUpdate(BaseModel):
    """MCP Server Update Request"""
    description: Optional[str] = Field(None, description="Updated description")
    transport_config: Optional[Dict[str, Any]] = Field(None, description="Updated transport config")
    health_check_interval: Optional[int] = Field(None, description="Updated health check interval")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    
    @validator('health_check_interval')
    def validate_health_interval(cls, v):
        if v is not None and (v < 10 or v > 3600):
            raise ValueError("Health check interval must be between 10 and 3600 seconds")
        return v


class McpServerListResponse(BaseModel):
    """Response for listing servers"""
    servers: List[McpServerInfo] = Field(..., description="List of servers")
    total_count: int = Field(..., description="Total number of servers")
    active_count: int = Field(..., description="Number of active servers")
    
    # Pagination
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    has_more: bool = Field(default=False, description="Whether there are more results")


class HealthCheckResult(BaseModel):
    """Health Check Result"""
    server_name: str = Field(..., description="Server name")
    healthy: bool = Field(..., description="Whether server is healthy")
    response_time: float = Field(..., description="Response time in seconds")
    timestamp: datetime = Field(..., description="Check timestamp")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemHealthReport(BaseModel):
    """System Health Report"""
    overall_status: HealthStatus = Field(..., description="Overall system health")
    total_servers: int = Field(..., description="Total number of servers")
    healthy_servers: int = Field(..., description="Number of healthy servers")
    unhealthy_servers: int = Field(..., description="Number of unhealthy servers")
    
    server_health: List[HealthCheckResult] = Field(..., description="Individual server health results")
    system_metrics: Dict[str, float] = Field(default_factory=dict, description="System-level metrics")
    timestamp: datetime = Field(..., description="Report timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RoutingDecisionInfo(BaseModel):
    """Routing Decision Information"""
    request_id: str = Field(..., description="Request ID")
    request_text: str = Field(..., description="Original request text")
    matched_servers: List[str] = Field(..., description="Selected servers")
    confidence: float = Field(..., description="Routing confidence score")
    reasoning: str = Field(..., description="Human-readable reasoning")
    strategy: str = Field(..., description="Routing strategy used")
    fallback_servers: List[str] = Field(default_factory=list, description="Fallback servers")
    processing_time: float = Field(..., description="Time taken to make decision")
    timestamp: datetime = Field(..., description="Decision timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolExecutionResult(BaseModel):
    """Tool Execution Result"""
    tool_name: str = Field(..., description="Tool name")
    server_name: str = Field(..., description="Server that executed the tool")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Any = Field(None, description="Tool execution result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(..., description="Execution timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ServerPerformanceMetrics(BaseModel):
    """Server Performance Metrics"""
    server_name: str = Field(..., description="Server name")
    total_requests: int = Field(default=0, description="Total number of requests")
    successful_requests: int = Field(default=0, description="Number of successful requests")
    failed_requests: int = Field(default=0, description="Number of failed requests")
    avg_response_time: float = Field(default=0.0, description="Average response time")
    min_response_time: float = Field(default=0.0, description="Minimum response time")
    max_response_time: float = Field(default=0.0, description="Maximum response time")
    uptime_percentage: float = Field(default=0.0, description="Uptime percentage")
    last_request: Optional[datetime] = Field(None, description="Last request timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemConfiguration(BaseModel):
    """System Configuration"""
    max_servers: int = Field(default=100, description="Maximum number of servers")
    default_health_check_interval: int = Field(default=60, description="Default health check interval")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    enable_auto_registration: bool = Field(default=True, description="Enable automatic server registration")
    enable_health_monitoring: bool = Field(default=True, description="Enable health monitoring")
    enable_performance_tracking: bool = Field(default=True, description="Enable performance tracking")
    log_level: str = Field(default="INFO", description="Logging level")


class ApiResponse(BaseModel):
    """Standard API Response"""
    status: str = Field(..., description="Response status (success/error)")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    error_code: Optional[str] = Field(None, description="Error code if status is error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationParams(BaseModel):
    """Pagination Parameters"""
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    limit: int = Field(default=50, description="Maximum number of items to return")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        return v


class FilterParams(BaseModel):
    """Filter Parameters"""
    status: Optional[ServerStatus] = Field(None, description="Filter by server status")
    transport_type: Optional[TransportType] = Field(None, description="Filter by transport type")
    health_status: Optional[HealthStatus] = Field(None, description="Filter by health status")
    name_pattern: Optional[str] = Field(None, description="Filter by name pattern")
    has_tools: Optional[bool] = Field(None, description="Filter servers that have tools")
    registered_after: Optional[datetime] = Field(None, description="Filter servers registered after date")
    registered_before: Optional[datetime] = Field(None, description="Filter servers registered before date")


class BulkOperationRequest(BaseModel):
    """Bulk Operation Request"""
    server_ids: List[str] = Field(..., description="List of server IDs")
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    
    @validator('server_ids')
    def validate_server_ids(cls, v):
        if not v:
            raise ValueError("At least one server ID must be provided")
        if len(v) > 100:
            raise ValueError("Cannot operate on more than 100 servers at once")
        return v


class BulkOperationResult(BaseModel):
    """Bulk Operation Result"""
    operation: str = Field(..., description="Operation performed")
    total_requested: int = Field(..., description="Total number of servers requested")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    results: List[Dict[str, Any]] = Field(..., description="Individual operation results")
    timestamp: datetime = Field(..., description="Operation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }