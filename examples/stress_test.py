# examples/stress_test.py
#!/usr/bin/env python3
"""
Stress Test Example
Tests Meta MCP under load with multiple concurrent requests
"""

import asyncio
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.registry import get_registry, McpServerRegistration, TransportType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def stress_test_registry():
    """Stress test the server registry"""
    
    logger.info("🔥 Starting Registry Stress Test")
    
    registry = get_registry()
    await registry.initialize()
    
    # Test parameters
    num_servers = 50
    num_operations = 200
    
    try:
        # Register many servers quickly
        start_time = time.time()
        server_ids = []
        
        for i in range(num_servers):
            registration = McpServerRegistration(
                name=f"test-server-{i}",
                description=f"Test server {i}",
                transport_type=TransportType.STDIO,
                transport_config={
                    "command": "echo",
                    "args": [f"test-{i}"]
                }
            )
            
            server_id = await registry.register_server(registration)
            server_ids.append(server_id)
            
            if i % 10 == 0:
                logger.info(f"Registered {i+1}/{num_servers} servers")
        
        registration_time = time.time() - start_time
        logger.info(f"✅ Registered {num_servers} servers in {registration_time:.2f}s")
        
        # Perform concurrent operations
        start_time = time.time()
        
        async def random_operation():
            """Perform a random registry operation"""
            operation = random.choice(['list', 'get', 'stats'])
            
            if operation == 'list':
                servers = registry.list_servers()
                return len(servers)
            elif operation == 'get':
                server_id = random.choice(server_ids)
                server = registry.get_server(server_id)
                return server is not None
            elif operation == 'stats':
                stats = await registry.get_registry_stats()
                return stats['total_servers']
        
        # Run operations concurrently
        tasks = [random_operation() for _ in range(num_operations)]
        results = await asyncio.gather(*tasks)
        
        operations_time = time.time() - start_time
        logger.info(f"✅ Completed {num_operations} operations in {operations_time:.2f}s")
        logger.info(f"📊 Operations/second: {num_operations/operations_time:.1f}")
        
        # Cleanup
        for server_id in server_ids:
            await registry.unregister_server(server_id)
        
        logger.info("🧹 Cleaned up all test servers")
        
    finally:
        await registry.shutdown()


async def stress_test_routing():
    """Stress test the routing system"""
    
    logger.info("🎯 Starting Routing Stress Test")
    
    from core.router import get_router
    
    router = get_router()
    available_servers = ["weather-mcp", "github-mcp", "filesystem-mcp", "memory-mcp"]
    
    # Generate test queries
    test_queries = [
        "What's the weather like in {}?".format(city)
        for city in ["New York", "London", "Tokyo", "Sydney", "Paris"]
    ] + [
        "Find {} repositories on GitHub".format(topic)
        for topic in ["Python", "JavaScript", "Machine Learning", "Web Development", "AI"]
    ] + [
        "Read the file {}".format(filename)
        for filename in ["/tmp/config.json", "/home/user/data.csv", "/etc/hosts"]
    ] + [
        "Remember {}".format(info)
        for info in ["API key", "user preferences", "important note", "meeting details"]
    ]
    
    # Multiply queries for stress test
    all_queries = test_queries * 20  # 400 total queries
    
    logger.info(f"🚀 Testing {len(all_queries)} routing decisions")
    
    start_time = time.time()
    
    # Process all queries
    for i, query in enumerate(all_queries):
        decision = await router.route_request(
            query,
            available_servers,
            {"request_id": f"stress-{i}"}
        )
        
        if i % 50 == 0:
            logger.info(f"Processed {i+1}/{len(all_queries)} queries")
    
    total_time = time.time() - start_time
    queries_per_second = len(all_queries) / total_time
    
    logger.info(f"✅ Completed routing stress test")
    logger.info(f"📊 Total time: {total_time:.2f}s")
    logger.info(f"📊 Queries/second: {queries_per_second:.1f}")
    logger.info(f"📊 Avg time/query: {total_time/len(all_queries)*1000:.1f}ms")


async def concurrent_load_test():
    """Test concurrent load on the system"""
    
    logger.info("⚡ Starting Concurrent Load Test")
    
    async def simulate_user_session(user_id: int):
        """Simulate a user session with multiple requests"""
        
        from core.router import get_router
        
        router = get_router()
        available_servers = ["weather-mcp", "github-mcp", "filesystem-mcp"]
        
        session_queries = [
            f"User {user_id}: What's the weather forecast?",
            f"User {user_id}: Find Python projects",
            f"User {user_id}: Read configuration file",
            f"User {user_id}: Complex analysis request"
        ]
        
        for query in session_queries:
            decision = await router.route_request(
                query,
                available_servers,
                {"request_id": f"user-{user_id}-{hash(query)}"}
            )
            
            # Simulate some processing time
            await asyncio.sleep(random.uniform(0.01, 0.05))
        
        return user_id
    
    # Simulate 100 concurrent users
    num_users = 100
    
    logger.info(f"👥 Simulating {num_users} concurrent users")
    
    start_time = time.time()
    
    # Run all user sessions concurrently
    tasks = [simulate_user_session(i) for i in range(num_users)]
    completed_users = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    logger.info(f"✅ Completed concurrent load test")
    logger.info(f"📊 Users: {len(completed_users)}")
    logger.info(f"📊 Total time: {total_time:.2f}s")
    logger.info(f"📊 Users/second: {len(completed_users)/total_time:.1f}")


async def memory_stress_test():
    """Test memory usage under stress"""
    
    logger.info("🧠 Starting Memory Stress Test")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    logger.info(f"📊 Initial memory usage: {initial_memory:.1f} MB")
    
    # Create many objects to test memory management
    large_data = []
    
    for i in range(1000):
        # Simulate large routing decisions with metadata
        data = {
            "request_id": f"memory-test-{i}",
            "query": f"Test query {i} with lots of metadata and analysis data",
            "analysis": {
                "keywords": [f"keyword-{j}" for j in range(20)],
                "entities": [{"type": "test", "value": f"entity-{j}"} for j in range(10)],
                "metadata": {f"field-{j}": f"value-{j}" for j in range(50)}
            },
            "routing_history": [
                {"server": f"server-{j}", "confidence": random.random()}
                for j in range(10)
            ]
        }
        large_data.append(data)
        
        if i % 100 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024
            logger.info(f"Created {i+1}/1000 objects, memory: {current_memory:.1f} MB")
    
    peak_memory = process.memory_info().rss / 1024 / 1024
    
    # Clean up
    large_data.clear()
    
    final_memory = process.memory_info().rss / 1024 / 1024
    
    logger.info(f"📊 Peak memory usage: {peak_memory:.1f} MB")
    logger.info(f"📊 Final memory usage: {final_memory:.1f} MB")
    logger.info(f"📊 Memory increase: {peak_memory - initial_memory:.1f} MB")
    
    if final_memory < peak_memory * 0.8:
        logger.info("✅ Good memory cleanup")
    else:
        logger.warning("⚠️ Possible memory leak detected")


async def main():
    """Main stress test function"""
    
    print("🔥 Meta MCP Stress Test Suite")
    print("=" * 40)
    
    tests = [
        ("Registry Stress Test", stress_test_registry),
        ("Routing Stress Test", stress_test_routing),
        ("Concurrent Load Test", concurrent_load_test),
        ("Memory Stress Test", memory_stress_test)
    ]
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n🧪 Running {test_name}")
            await test_func()
            logger.info(f"✅ {test_name} completed successfully")
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {e}")
    
    logger.info("\n🏁 Stress test suite completed")


if __name__ == "__main__":
    asyncio.run(main())