#!/usr/bin/env python3
"""
Meta MCP Project Cleanup
Clean up development files and prepare for production
"""

import os
import shutil
from pathlib import Path

def cleanup_project():
    """Clean up development files and organize for production"""
    
    print("🧹 Meta MCP Project Cleanup")
    print("=" * 40)
    
    # Files to KEEP (Core Production Files)
    keep_files = {
        "Essential Core": [
            "src/",
            "requirements.txt",
            "README.md",
            ".env.example",
            "pyproject.toml"
        ],
        "Docker & Deployment": [
            "docker-compose.yml",
            "docker/",
            "Dockerfile"  # if you have one
        ],
        "Documentation": [
            "README.md",
            "docs/"  # if you have one
        ]
    }
    
    # Files to DELETE (Development/Testing Files)
    delete_files = {
        "Test Scripts": [
            "test_stdio_server.py",
            "test_running_server.py", 
            "simple_stdio_test.py",
            "quick_tool_test.py"
        ],
        "Environment Setup": [
            "check_environment.py",
            "fix_windows_subprocess.py",
            "fix_windows_subprocess_v2.py"
        ],
        "Database Tools": [
            "cleanup_database.py"  # Keep as utility script if needed
        ],
        "Development Files": [
            "meta_mcp.log",  # Regenerated on each run
            "meta_mcp.db",   # Regenerated on each run
            "__pycache__/",
            "*.pyc",
            ".pytest_cache/"
        ]
    }
    
    # Files to KEEP AS UTILITIES (Optional)
    utility_files = {
        "Useful Utilities": [
            "examples/",  # Keep for reference
            "tests/",     # Keep for testing
            "run_http_server.py",  # Keep for HTTP mode
            "cleanup_database.py"  # Keep as utility
        ]
    }
    
    print("\n📁 PRODUCTION PROJECT STRUCTURE:")
    print("Keep these essential files:")
    for category, files in keep_files.items():
        print(f"\n  {category}:")
        for file in files:
            status = "✅" if Path(file).exists() else "❌"
            print(f"    {status} {file}")
    
    print("\n🗑️  DELETE THESE DEVELOPMENT FILES:")
    for category, files in delete_files.items():
        print(f"\n  {category}:")
        for file in files:
            if Path(file).exists():
                print(f"    🗑️  {file} - DELETE")
            else:
                print(f"    ⭕ {file} - Not found")
    
    print("\n🔧 KEEP AS UTILITIES (Optional):")
    for category, files in utility_files.items():
        print(f"\n  {category}:")
        for file in files:
            status = "✅" if Path(file).exists() else "❌"
            print(f"    {status} {file} - Keep as utility")
    
    print("\n" + "=" * 50)
    
    # Ask for confirmation
    choice = input("🤔 Do you want to auto-cleanup development files? (y/N): ").strip().lower()
    
    if choice in ['y', 'yes']:
        print("\n🧹 Cleaning up development files...")
        
        deleted_count = 0
        for category, files in delete_files.items():
            for file_path in files:
                path = Path(file_path)
                try:
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                            print(f"  🗑️  Deleted: {file_path}")
                            deleted_count += 1
                        elif path.is_dir():
                            shutil.rmtree(path)
                            print(f"  🗑️  Deleted directory: {file_path}")
                            deleted_count += 1
                except Exception as e:
                    print(f"  ❌ Could not delete {file_path}: {e}")
        
        print(f"\n✅ Cleanup complete! Deleted {deleted_count} development files.")
        
    else:
        print("\n⏸️  Cleanup cancelled - all files kept.")
    
    print("\n📋 FINAL PRODUCTION STRUCTURE:")
    print("Your clean Meta MCP should have:")
    print("  📁 src/                    # Core application code")
    print("  📁 docker/                 # Docker configuration")
    print("  📁 examples/               # Integration examples")
    print("  📁 tests/                  # Test suites")
    print("  📄 requirements.txt        # Python dependencies")
    print("  📄 docker-compose.yml      # Docker orchestration")
    print("  📄 README.md              # Documentation")
    print("  📄 .env.example           # Environment template")
    print("  📄 run_http_server.py     # HTTP mode (utility)")
    
    print("\n🚀 Ready for your ticket triage system!")

def create_production_env():
    """Create production environment template"""
    
    production_env = """# Meta MCP - Production Configuration
# Ticket Triage and Dispatch System

# === Core Settings ===
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO

# === Database ===
# Use PostgreSQL for production
DATABASE_URL=postgresql+asyncpg://meta_mcp:secure_password@localhost:5432/meta_mcp_prod

# === Redis Cache ===
REDIS_URL=redis://localhost:6379/0

# === Your Domain MCP Servers ===
# Configure your PSA, User, and Dispatch MCP servers

# PSA MCP Configuration
PSA_MCP_COMMAND=python
PSA_MCP_ARGS=/path/to/your/psa-mcp/server.py
PSA_MCP_AUTO_CONNECT=true

# User MCP Configuration  
USER_MCP_COMMAND=python
USER_MCP_ARGS=/path/to/your/user-mcp/server.py
USER_MCP_AUTO_CONNECT=true

# Dispatch MCP Configuration
DISPATCH_MCP_COMMAND=python
DISPATCH_MCP_ARGS=/path/to/your/dispatch-mcp/server.py
DISPATCH_MCP_AUTO_CONNECT=true

# === API Keys (if needed) ===
# Add any API keys your domain MCPs need
# THIRD_PARTY_API_KEY=your_key_here

# === Performance ===
MAX_CONCURRENT_CONNECTIONS=200
CONNECTION_POOL_SIZE=50
REQUEST_TIMEOUT=30

# === Monitoring ===
ENABLE_METRICS=true
ENABLE_HEALTH_MONITORING=true
HEALTH_CHECK_INTERVAL=30

# === Security ===
SECRET_KEY=your-production-secret-key-here
"""
    
    with open(".env.production", "w") as f:
        f.write(production_env)
    
    print("✅ Created .env.production template for your ticket system")

if __name__ == "__main__":
    cleanup_project()
    create_production_env()