"""
Meta MCP Configuration Settings
Environment-based configuration management
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Meta MCP Configuration Settings"""
    
    # Application Settings
    app_name: str = Field(default="Meta MCP Server", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./meta_mcp.db", 
        alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    
    # Redis Configuration (for caching and pub/sub)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_max_connections: int = Field(default=10, alias="REDIS_MAX_CONNECTIONS")
    
    # MCP Server Configuration
    mcp_protocol_version: str = Field(default="2024-11-05", alias="MCP_PROTOCOL_VERSION")
    mcp_connection_timeout: int = Field(default=30, alias="MCP_CONNECTION_TIMEOUT")
    mcp_health_check_interval: int = Field(default=60, alias="MCP_HEALTH_CHECK_INTERVAL")
    mcp_max_retries: int = Field(default=3, alias="MCP_MAX_RETRIES")
    mcp_retry_delay: int = Field(default=5, alias="MCP_RETRY_DELAY")
    
    # Transport Configuration
    default_transport: str = Field(default="stdio", alias="DEFAULT_TRANSPORT")
    sse_port: int = Field(default=3001, alias="SSE_PORT")
    http_port: int = Field(default=3002, alias="HTTP_PORT")
    websocket_port: int = Field(default=3003, alias="WEBSOCKET_PORT")
    
    # Security Configuration
    secret_key: str = Field(
        default="meta-mcp-secret-key-change-in-production", 
        alias="SECRET_KEY"
    )
    api_key_header: str = Field(default="X-API-Key", alias="API_KEY_HEADER")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_file: str = Field(default="meta_mcp.log", alias="LOG_FILE")
    
    # External API Keys (for MCP servers)
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    slack_bot_token: Optional[str] = Field(default=None, alias="SLACK_BOT_TOKEN")
    slack_team_id: Optional[str] = Field(default=None, alias="SLACK_TEAM_ID")
    openweather_api_key: Optional[str] = Field(default=None, alias="OPENWEATHER_API_KEY")
    brave_api_key: Optional[str] = Field(default=None, alias="BRAVE_API_KEY")
    
    # Performance Configuration
    max_concurrent_connections: int = Field(default=100, alias="MAX_CONCURRENT_CONNECTIONS")
    connection_pool_size: int = Field(default=20, alias="CONNECTION_POOL_SIZE")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")
    max_request_size: int = Field(default=10485760, alias="MAX_REQUEST_SIZE")  # 10MB
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")
    enable_tracing: bool = Field(default=False, alias="ENABLE_TRACING")
    jaeger_endpoint: Optional[str] = Field(default=None, alias="JAEGER_ENDPOINT")
    
    # Server Templates Configuration
    auto_register_examples: bool = Field(default=True, alias="AUTO_REGISTER_EXAMPLES")
    enable_server_templates: bool = Field(default=True, alias="ENABLE_SERVER_TEMPLATES")
    
    # Intelligent Routing Configuration
    routing_confidence_threshold: float = Field(default=0.3, alias="ROUTING_CONFIDENCE_THRESHOLD")
    max_routing_suggestions: int = Field(default=5, alias="MAX_ROUTING_SUGGESTIONS")
    enable_smart_routing: bool = Field(default=True, alias="ENABLE_SMART_ROUTING")
    
    # Health Check Configuration
    health_check_enabled: bool = Field(default=True, alias="HEALTH_CHECK_ENABLED")
    health_check_timeout: int = Field(default=10, alias="HEALTH_CHECK_TIMEOUT")
    max_health_check_failures: int = Field(default=3, alias="MAX_HEALTH_CHECK_FAILURES")
    
    # FastMCP Configuration
    fastmcp_server_name: str = Field(default="Meta MCP Server", alias="FASTMCP_SERVER_NAME")
    fastmcp_stdio_buffer_size: int = Field(default=65536, alias="FASTMCP_STDIO_BUFFER_SIZE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton pattern)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment (useful for testing)
    """
    global _settings
    _settings = Settings()
    return _settings


def get_mcp_server_config(server_type: str, **kwargs) -> Dict[str, Any]:
    """
    Get MCP server configuration for a specific server type
    
    Args:
        server_type: Type of server (github, slack, weather, etc.)
        **kwargs: Additional configuration overrides
    
    Returns:
        Configuration dictionary for the server
    """
    settings = get_settings()
    
    base_config = {
        "timeout": settings.mcp_connection_timeout,
        "max_retries": settings.mcp_max_retries,
        "retry_delay": settings.mcp_retry_delay,
        "health_check_interval": settings.mcp_health_check_interval,
        "protocol_version": settings.mcp_protocol_version
    }
    
    # Server-specific configurations
    server_configs = {
        "github": {
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_token
            } if settings.github_token else {}
        },
        "slack": {
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {
                "SLACK_BOT_TOKEN": settings.slack_bot_token,
                "SLACK_TEAM_ID": settings.slack_team_id
            } if settings.slack_bot_token else {}
        },
        "weather": {
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@h1deya/mcp-server-weather"],
            "env": {
                "OPENWEATHER_API_KEY": settings.openweather_api_key
            } if settings.openweather_api_key else {}
        },
        "filesystem": {
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "env": {}
        },
        "memory": {
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": {}
        },
        "postgres": {
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/postgres"],
            "env": {}
        }
    }
    
    if server_type not in server_configs:
        raise ValueError(f"Unknown server type: {server_type}")
    
    config = {**base_config, **server_configs[server_type]}
    config.update(kwargs)
    
    return config


def validate_environment() -> Dict[str, Any]:
    """
    Validate the current environment configuration
    
    Returns:
        Validation results with warnings and errors
    """
    settings = get_settings()
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "recommendations": []
    }
    
    # Check required Node.js for MCP servers
    import shutil
    if not shutil.which("npx"):
        results["errors"].append("npx (Node.js) not found. Required for running MCP servers.")
        results["valid"] = False
    
    # Check API keys
    api_key_warnings = []
    if not settings.github_token:
        api_key_warnings.append("GITHUB_TOKEN not set. GitHub MCP server will not be available.")
    
    if not settings.slack_bot_token:
        api_key_warnings.append("SLACK_BOT_TOKEN not set. Slack MCP server will not be available.")
    
    if not settings.openweather_api_key:
        api_key_warnings.append("OPENWEATHER_API_KEY not set. Enhanced weather features will be limited.")
    
    results["warnings"].extend(api_key_warnings)
    
    # Check database URL
    if "sqlite" in settings.database_url and settings.environment == "production":
        results["warnings"].append("Using SQLite in production. Consider PostgreSQL for better performance.")
    
    # Check debug mode in production
    if settings.debug and settings.environment == "production":
        results["warnings"].append("Debug mode enabled in production. This may expose sensitive information.")
    
    # Security checks
    if settings.secret_key == "meta-mcp-secret-key-change-in-production":
        results["errors"].append("Secret key not changed from default. This is a security risk.")
        results["valid"] = False
    
    # Performance recommendations
    if settings.max_concurrent_connections > 200:
        results["recommendations"].append("High concurrent connection limit. Monitor system resources.")
    
    return results


def get_environment_info() -> Dict[str, Any]:
    """
    Get information about the current environment
    
    Returns:
        Environment information dictionary
    """
    settings = get_settings()
    
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "platform": os.name,
        "database_type": "sqlite" if "sqlite" in settings.database_url else "postgresql",
        "redis_configured": "redis://" in settings.redis_url,
        "api_keys_available": {
            "github": bool(settings.github_token),
            "slack": bool(settings.slack_bot_token),
            "openweather": bool(settings.openweather_api_key),
            "brave": bool(settings.brave_api_key)
        },
        "features_enabled": {
            "metrics": settings.enable_metrics,
            "tracing": settings.enable_tracing,
            "health_checks": settings.health_check_enabled,
            "smart_routing": settings.enable_smart_routing,
            "server_templates": settings.enable_server_templates
        }
    }