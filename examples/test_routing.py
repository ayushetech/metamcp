# examples/test_routing.py
#!/usr/bin/env python3
"""
Test Routing Logic Example
Demonstrates intelligent routing capabilities of Meta MCP
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.router import get_router, RoutingStrategy, RoutingRule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_routing_scenarios():
    """Test various routing scenarios"""
    
    router = get_router()
    
    # Mock available servers
    available_servers = [
        "weather-mcp",
        "github-mcp", 
        "filesystem-mcp",
        "memory-mcp",
        "slack-mcp",
        "postgres-mcp"
    ]
    
    # Test scenarios
    test_cases = [
        {
            "query": "What's the weather forecast for tomorrow in Seattle?",
            "expected_server": "weather-mcp",
            "description": "Weather query should route to weather server"
        },
        {
            "query": "Search for Python machine learning repositories on GitHub",
            "expected_server": "github-mcp",
            "description": "GitHub query should route to GitHub server"
        },
        {
            "query": "Read the contents of /home/user/config.json",
            "expected_server": "filesystem-mcp", 
            "description": "File operation should route to filesystem server"
        },
        {
            "query": "Remember this API key for later use",
            "expected_server": "memory-mcp",
            "description": "Memory operation should route to memory server"
        },
        {
            "query": "Send a message to the #general channel",
            "expected_server": "slack-mcp",
            "description": "Slack operation should route to Slack server"
        },
        {
            "query": "Query the users table for active accounts",
            "expected_server": "postgres-mcp",
            "description": "Database query should route to PostgreSQL server"
        },
        {
            "query": "Create a comprehensive analysis report with weather data and GitHub trends",
            "expected_servers": ["weather-mcp", "github-mcp", "memory-mcp"],
            "description": "Complex multi-domain query should route to multiple servers"
        },
        {
            "query": "Hello, how are you today?",
            "expected_server": None,  # Any server is fine for fallback
            "description": "Generic greeting should use fallback routing"
        }
    ]
    
    logger.info("🧪 Testing Meta MCP Intelligent Routing")
    logger.info("=" * 60)
    
    total_tests = len(test_cases)
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n📝 Test {i}/{total_tests}: {test_case['description']}")
        logger.info(f"Query: '{test_case['query']}'")
        
        try:
            # Analyze the request
            analysis = await router.analyze_request(test_case['query'])
            logger.info(f"Analysis - Domain: {analysis.domain}, Intent: {analysis.intent}")
            logger.info(f"Keywords: {', '.join(analysis.keywords[:5])}")
            
            # Get routing decision
            decision = await router.route_request(
                test_case['query'],
                available_servers,
                {"request_id": f"test-{i}"}
            )
            
            # Check results
            logger.info(f"🎯 Routing Decision:")
            logger.info(f"   Matched Servers: {decision.matched_servers}")
            logger.info(f"   Strategy: {decision.strategy.value}")
            logger.info(f"   Confidence: {decision.confidence:.2f}")
            logger.info(f"   Reasoning: {decision.reasoning}")
            
            # Validate result
            test_passed = False
            
            if "expected_servers" in test_case:
                # Multi-server test
                matched_count = sum(
                    1 for server in test_case["expected_servers"]
                    if any(server in matched for matched in decision.matched_servers)
                )
                test_passed = matched_count > 0
                
            elif test_case["expected_server"]:
                # Single server test
                test_passed = any(
                    test_case["expected_server"] in server 
                    for server in decision.matched_servers
                )
            else:
                # Fallback test - any result is fine
                test_passed = len(decision.matched_servers) > 0
            
            if test_passed:
                logger.info("✅ PASSED")
                passed_tests += 1
            else:
                logger.info("❌ FAILED")
                if test_case["expected_server"]:
                    logger.info(f"   Expected: {test_case['expected_server']}")
            
        except Exception as e:
            logger.error(f"❌ ERROR: {e}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Test Results: {passed_tests}/{total_tests} passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! Routing logic is working correctly.")
    else:
        logger.warning(f"⚠️ {total_tests - passed_tests} tests failed. Check routing rules.")
    
    return passed_tests == total_tests


async def test_custom_routing_rules():
    """Test custom routing rules"""
    
    logger.info("\n🔧 Testing Custom Routing Rules")
    logger.info("=" * 40)
    
    router = get_router()
    
    # Add a custom rule
    custom_rule = RoutingRule(
        name="data_science_workflow",
        pattern=r"\b(data science|analytics|machine learning|ml|ai)\b",
        keywords=["data", "science", "analytics", "ml", "ai"],
        server_names=["github-mcp", "memory-mcp", "postgres-mcp"],
        strategy=RoutingStrategy.PARALLEL,
        priority=95,
        confidence_threshold=0.6
    )
    
    router.add_routing_rule(custom_rule)
    logger.info("✅ Added custom data science routing rule")
    
    # Test the custom rule
    test_query = "Help me find data science projects and analyze the trends"
    
    decision = await router.route_request(
        test_query,
        ["weather-mcp", "github-mcp", "memory-mcp", "postgres-mcp"],
        {"request_id": "custom-rule-test"}
    )
    
    logger.info(f"Query: '{test_query}'")
    logger.info(f"Matched Servers: {decision.matched_servers}")
    logger.info(f"Strategy: {decision.strategy.value}")
    logger.info(f"Confidence: {decision.confidence:.2f}")
    logger.info(f"Matched Rules: {decision.matched_rules}")
    
    # Check if our custom rule was used
    if "data_science_workflow" in decision.matched_rules:
        logger.info("✅ Custom rule successfully triggered")
        return True
    else:
        logger.warning("⚠️ Custom rule was not triggered")
        return False


async def benchmark_routing_performance():
    """Benchmark routing performance"""
    
    logger.info("\n⚡ Benchmarking Routing Performance")
    logger.info("=" * 40)
    
    router = get_router()
    available_servers = ["weather-mcp", "github-mcp", "filesystem-mcp", "memory-mcp"]
    
    test_queries = [
        "What's the weather like?",
        "Find repositories about Python",
        "Read config file",
        "Remember this information",
        "Complex multi-step analysis workflow"
    ] * 20  # 100 total queries
    
    import time
    
    start_time = time.time()
    
    for i, query in enumerate(test_queries):
        await router.route_request(
            query,
            available_servers,
            {"request_id": f"benchmark-{i}"}
        )
    
    end_time = time.time()
    total_time = end_time - start_time
    queries_per_second = len(test_queries) / total_time
    avg_time_per_query = total_time / len(test_queries) * 1000  # milliseconds
    
    logger.info(f"📈 Performance Results:")
    logger.info(f"   Total Queries: {len(test_queries)}")
    logger.info(f"   Total Time: {total_time:.2f} seconds")
    logger.info(f"   Queries/Second: {queries_per_second:.1f}")
    logger.info(f"   Avg Time/Query: {avg_time_per_query:.1f} ms")
    
    if avg_time_per_query < 50:  # Less than 50ms is good
        logger.info("✅ Excellent performance!")
    elif avg_time_per_query < 100:
        logger.info("✅ Good performance")
    else:
        logger.warning("⚠️ Performance could be improved")
    
    return avg_time_per_query


async def main():
    """Main test function"""
    
    print("🌟 Meta MCP - Intelligent Routing Test Suite")
    print("=" * 50)
    
    try:
        # Run basic routing tests
        basic_tests_passed = await test_routing_scenarios()
        
        # Test custom routing rules
        custom_rules_passed = await test_custom_routing_rules()
        
        # Benchmark performance
        avg_time = await benchmark_routing_performance()
        
        # Final summary
        print("\n" + "=" * 50)
        print("📋 Final Results:")
        print(f"   ✅ Basic Routing Tests: {'PASSED' if basic_tests_passed else 'FAILED'}")
        print(f"   ✅ Custom Rules Test: {'PASSED' if custom_rules_passed else 'FAILED'}")
        print(f"   ⚡ Performance: {avg_time:.1f} ms/query")
        
        if basic_tests_passed and custom_rules_passed:
            print("\n🎊 All tests passed! Meta MCP routing is working perfectly.")
            return True
        else:
            print("\n⚠️ Some tests failed. Check the logs above for details.")
            return False
            
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)