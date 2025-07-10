# Meta MCP Server 🚀

**Model Context Protocol Orchestration Server**

Meta MCP is a production-ready orchestration server that intelligently manages and routes requests to multiple real MCP servers. Built with the official MCP Python SDK and FastMCP framework.

## 🎯 What This Is

- **Real MCP Protocol**: Uses official MCP libraries, not just HTTP APIs
- **Intelligent Routing**: AI-powered request analysis and server selection  
- **Multi-Server Management**: Register, connect, and manage multiple MCP servers
- **Production Ready**: Health monitoring, error handling, database persistence
- **Extensible**: Easy to add new MCP servers and routing strategies

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  MCP Clients    │    │   Meta MCP       │    │   Domain MCP        │
│  (Claude, etc.) │───►│   Server V2      │───►│   Servers           │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                              │                         │
                              ▼                         ▼
                       ┌──────────────┐         ┌──────────────┐
                       │  Registry    │         │ • GitHub     │
                       │  Router      │         │ • Weather    │
                       │  Health      │         │ • Filesystem │
                       │  Monitor     │         │ • Memory     │
                       └──────────────┘         │ • Slack      │
                                               │ • PostgreSQL │
                                               └──────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for MCP servers)
- **Git**

### 1. Clone and Setup

```bash
git clone <your-repo>
cd meta-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Required API Keys:**
- `GITHUB_TOKEN` - GitHub Personal Access Token
- `SLACK_BOT_TOKEN` - Slack Bot Token (optional)
- `OPENWEATHER_API_KEY` - OpenWeather API Key (optional)

### 3. Register Real MCP Servers

```bash
# Register and connect to real MCP servers
python examples/register_real_servers.py
```

This will register:
- ✅ **Weather MCP** - Real weather data via Open-Meteo
- ✅ **Memory MCP** - Persistent knowledge storage  
- ✅ **Filesystem MCP** - Secure file operations
- ✅ **GitHub MCP** - Repository management (if token provided)
- ✅ **Slack MCP** - Workspace integration (if token provided)

### 4. Test with Postman

Import `Meta-MCP-V2-Testing.postman_collection.json` and run the test suite:

1. **Health Checks** - Verify server status
2. **Server Registration** - Register new MCP servers
3. **Tool Discovery** - List all available tools
4. **Intelligent Routing** - Test routing analysis
5. **Tool Execution** - Call tools on registered servers

### 5. Use with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "meta-mcp": {
      "command": "python",
      "args": ["path/to/meta-mcp/src/main.py"]
    }
  }
}
```

## 🔧 Usage Examples

### Register a New MCP Server

```python
import asyncio
from src.core.registry import get_registry, McpServerRegistration, TransportType

async def register_server():
    registry = get_registry()
    await registry.initialize()
    
    registration = McpServerRegistration(
        name="my-custom-server",
        description="My custom MCP server",
        transport_type=TransportType.STDIO,
        transport_config={
            "command": "npx",
            "args": ["-y", "@my-org/my-mcp-server"]
        }
    )
    
    server_id = await registry.register_server(registration)
    print(f"Registered server: {server_id}")
```

### Intelligent Request Routing

```python
# The Meta MCP automatically routes requests based on:
# 1. Request content analysis
# 2. Available server capabilities  
# 3. Tool compatibility
# 4. Server health status

# Example: "What's the weather in NYC?" 
# → Automatically routes to Weather MCP server

# Example: "Search for ML repositories"
# → Automatically routes to GitHub MCP server
```

### Call Tools Through Meta MCP

```python
from src.mcp.protocol import McpClient, TransportType

async def use_meta_mcp():
    # Connect to Meta MCP
    client = McpClient(
        transport_type=TransportType.STDIO,
        command="python",
        args=["src/main.py"]
    )
    
    await client.connect()
    
    # List all available tools
    tools = client.tools
    print(f"Available tools: {[tool.name for tool in tools]}")
    
    # Call a tool (Meta MCP routes to appropriate server)
    result = await client.call_tool("get-weather", {
        "city": "San Francisco", 
        "state": "CA"
    })
    
    print(f"Weather result: {result}")
```

## 🧪 Real MCP Servers Included

### 1. Weather MCP Server
- **Package**: `@h1deya/mcp-server-weather`
- **API**: Open-Meteo (no key required)
- **Tools**: Get weather, forecasts, alerts
- **Test**: Get weather for any US city

### 2. GitHub MCP Server  
- **Package**: `@modelcontextprotocol/server-github`
- **API**: GitHub REST API
- **Tools**: Search repos, get files, issues, PRs
- **Requires**: GitHub Personal Access Token

### 3. Memory MCP Server
- **Package**: `@modelcontextprotocol/server-memory`
- **Storage**: Local knowledge graph
- **Tools**: Store/retrieve entities and relationships
- **Test**: Save and search project information

### 4. Filesystem MCP Server
- **Package**: `@modelcontextprotocol/server-filesystem`
- **Scope**: Sandboxed file operations
- **Tools**: Read, write, list files securely
- **Test**: File operations in `/tmp`

### 5. Slack MCP Server (Optional)
- **Package**: `@modelcontextprotocol/server-slack`
- **API**: Slack Web API
- **Tools**: Send messages, read channels
- **Requires**: Slack Bot Token

### 6. PostgreSQL MCP Server (Optional)
- **Package**: `@modelcontextprotocol/server-postgres`
- **Database**: PostgreSQL connection
- **Tools**: Query database, inspect schema
- **Requires**: PostgreSQL instance

## 📊 Testing Results

The Postman collection includes **60+ comprehensive tests**:

✅ **Server Registration** - Register real MCP servers  
✅ **Health Monitoring** - Continuous health checks  
✅ **Tool Discovery** - Auto-discover server capabilities  
✅ **Intelligent Routing** - Content-based routing analysis  
✅ **Tool Execution** - Call tools on real servers  
✅ **Error Handling** - Robust error scenarios  
✅ **Stress Testing** - Performance under load  

**Expected Success Rate**: 95%+

## 🔍 Intelligent Routing Features

### Content Analysis
- **Keyword Matching**: Weather queries → Weather server
- **Tool Compatibility**: Repository queries → GitHub server  
- **Context Understanding**: File operations → Filesystem server

### Confidence Scoring
- **High Confidence** (0.8+): Direct tool match
- **Medium Confidence** (0.5-0.8): Partial keyword match
- **Low Confidence** (<0.5): Fallback routing

### Multi-Server Workflows
- **Parallel Execution**: Run tools on multiple servers
- **Sequential Processing**: Chain tools across servers
- **Failover Logic**: Automatic fallback on errors

## 🏥 Health Monitoring

- **Continuous Monitoring**: Every 60 seconds
- **Automatic Reconnection**: On connection failures
- **Health Metrics**: Response times, success rates
- **Status Tracking**: Active, inactive, error states

## 📈 Production Features

### Database Persistence
- **SQLite** (development): `sqlite:///meta_mcp.db`
- **PostgreSQL** (production): Full async support
- **Migrations**: Automatic schema management

### Observability  
- **Structured Logging**: JSON format with request IDs
- **Metrics**: Prometheus-compatible metrics
- **Tracing**: OpenTelemetry integration (optional)
- **Health Endpoints**: `/health` for monitoring

### Security
- **Sandboxed Execution**: MCP servers run in isolation
- **API Key Management**: Secure credential handling
- **Request Validation**: Input sanitization
- **Error Handling**: No sensitive data exposure

## 🔧 Configuration

### Environment Variables

```bash
# Core Settings
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./meta_mcp.db
LOG_LEVEL=INFO

# MCP Settings  
MCP_CONNECTION_TIMEOUT=30
MCP_HEALTH_CHECK_INTERVAL=60
MCP_MAX_RETRIES=3

# API Keys
GITHUB_TOKEN=ghp_your_token_here
SLACK_BOT_TOKEN=xoxb_your_token_here
OPENWEATHER_API_KEY=your_key_here

# Performance
MAX_CONCURRENT_CONNECTIONS=100
CONNECTION_POOL_SIZE=20
```

### Server Templates

Pre-configured templates for easy registration:

```python
# Register using templates
await registry.register_template_server("weather")
await registry.register_template_server("github", {"GITHUB_TOKEN": "your_token"})
await registry.register_template_server("memory")
```

## 🚀 Advanced Usage

### Custom MCP Servers

Register your own MCP servers:

```python
registration = McpServerRegistration(
    name="my-domain-server",
    description="Custom domain-specific MCP server",
    transport_type=TransportType.STDIO,
    transport_config={
        "command": "python",
        "args": ["my_custom_server.py"],
        "env": {"API_KEY": "secret"}
    },
    auto_connect=True
)

server_id = await registry.register_server(registration)
```

### Custom Routing Rules

Extend intelligent routing:

```python
from src.core.router import RouteAnalyzer

# Add custom routing logic
analyzer = RouteAnalyzer()
analyzer.add_rule("custom_pattern", ["keyword1", "keyword2"], "my-server")
```

### Webhook Integration

Receive notifications on server events:

```python
@mcp.notification("server_connected")
async def on_server_connected(params):
    print(f"Server connected: {params['server_name']}")
    # Trigger workflow, send notification, etc.
```

## 🔄 Development Workflow

### 1. Local Development

```bash
# Start Meta MCP in development mode
python src/main.py

# In another terminal, register test servers
python examples/register_real_servers.py

# Test with Postman or Claude Desktop
```

### 2. Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests with real servers
python tests/test_integration.py

# Load test with Postman collection
newman run Meta-MCP-V2-Testing.postman_collection.json
```

### 3. Deployment

```bash
# Production deployment
docker-compose up -d

# Or deploy to cloud
# Configure DATABASE_URL for PostgreSQL
# Set production environment variables
# Use process manager (systemd, supervisor)
```

## 🤝 Integration Examples

### Claude Desktop Integration

```json
{
  "mcpServers": {
    "meta-mcp": {
      "command": "python",
      "args": ["/path/to/meta-mcp/src/main.py"],
      "env": {
        "DEBUG": "false",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Cursor IDE Integration

```json
{
  "mcpServers": {
    "meta-mcp": {
      "command": "python",
      "args": ["/path/to/meta-mcp/src/main.py"]
    }
  }
}
```

### API Integration

```python
import httpx

# Use Meta MCP via HTTP transport
async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8000/mcp", json={
        "jsonrpc": "2.0",
        "id": "test",
        "method": "tools/call",
        "params": {
            "name": "intelligent_tool_routing",
            "arguments": {"query": "What's the weather in Boston?"}
        }
    })
    
    result = response.json()
    print(f"Routing suggestion: {result}")
```

## 🔧 Troubleshooting

### Common Issues

**1. "npx not found"**
```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**2. "MCP server connection failed"**
```bash
# Check if server packages are available
npx @h1deya/mcp-server-weather --help

# Check network connectivity
ping api.open-meteo.com
```

**3. "GitHub API rate limit"**
```bash
# Verify token has correct permissions
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

### Debug Mode

Enable detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python src/main.py
```

### Health Diagnostics

```bash
# Check server health
curl http://localhost:8000/health

# Run environment validation
python -c "from src.core.config import validate_environment; print(validate_environment())"
```

## 📚 Documentation

- **MCP Specification**: https://modelcontextprotocol.io/
- **FastMCP Framework**: https://github.com/modelcontextprotocol/python-sdk
- **Official MCP Servers**: https://github.com/modelcontextprotocol/servers

## 🎉 What's Next?

After testing the Meta MCP:

1. **Domain MCP Integration**: Connect your team's PSA, User, and Dispatch MCPs
2. **Custom Routing**: Add business-specific routing logic
3. **Advanced Workflows**: Build multi-step automation
4. **Production Deployment**: Scale with PostgreSQL and Redis
5. **Monitoring**: Add Grafana dashboards and alerts

## 📄 License

MIT License - See LICENSE file for details.

---

**🌟 Ready to orchestrate the future of AI integration? Start with Meta MCP!**