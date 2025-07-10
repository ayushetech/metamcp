# docker/postgres/init.sql
-- Initialize Meta MCP Database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables if they don't exist
CREATE TABLE IF NOT EXISTS mcp_servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    transport_type VARCHAR(50) NOT NULL,
    transport_config JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'inactive',
    capabilities JSONB,
    tools_count INTEGER DEFAULT 0,
    resources_count INTEGER DEFAULT 0,
    prompts_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_health_check TIMESTAMP WITH TIME ZONE,
    health_check_failures INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_mcp_servers_name ON mcp_servers(name);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_status ON mcp_servers(status);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_transport_type ON mcp_servers(transport_type);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_created_at ON mcp_servers(created_at);

-- Create health check results table
CREATE TABLE IF NOT EXISTS health_check_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_name VARCHAR(255) NOT NULL,
    healthy BOOLEAN NOT NULL,
    response_time FLOAT NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_health_check_server_name ON health_check_results(server_name);
CREATE INDEX IF NOT EXISTS idx_health_check_timestamp ON health_check_results(timestamp);

-- Create routing decisions table for analytics
CREATE TABLE IF NOT EXISTS routing_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(255) NOT NULL,
    request_text TEXT NOT NULL,
    matched_servers TEXT[] NOT NULL,
    confidence FLOAT NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    reasoning TEXT NOT NULL,
    processing_time FLOAT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_routing_decisions_request_id ON routing_decisions(request_id);
CREATE INDEX IF NOT EXISTS idx_routing_decisions_timestamp ON routing_decisions(timestamp);

-- Create tool execution results table
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    server_name VARCHAR(255) NOT NULL,
    success BOOLEAN NOT NULL,
    execution_time FLOAT NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    result_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_tool_executions_request_id ON tool_executions(request_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool_name ON tool_executions(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_executions_server_name ON tool_executions(server_name);
CREATE INDEX IF NOT EXISTS idx_tool_executions_timestamp ON tool_executions(timestamp);

---