# tests/test_routing.py
"""
Unit tests for Intelligent Routing
"""

import pytest
from src.core.router import RequestRouter, RoutingStrategy, RoutingRule


class TestRequestRouter:
    """Test intelligent routing functionality"""

    @pytest.fixture
    def router(self):
        return RequestRouter()

    @pytest.fixture
    def available_servers(self):
        return ["weather-mcp", "github-mcp", "filesystem-mcp", "memory-mcp"]

    @pytest.mark.asyncio
    async def test_weather_query_routing(self, router, available_servers):
        """Test routing of weather queries"""
        request_text = "What's the weather like in New York today?"
        
        decision = await router.route_request(request_text, available_servers)
        
        assert "weather" in decision.matched_servers[0]
        assert decision.confidence > 0.5
        assert decision.strategy == RoutingStrategy.SINGLE

    @pytest.mark.asyncio
    async def test_github_query_routing(self, router, available_servers):
        """Test routing of GitHub queries"""
        request_text = "Search for machine learning repositories on GitHub"
        
        decision = await router.route_request(request_text, available_servers)
        
        assert "github" in decision.matched_servers[0]
        assert decision.confidence > 0.5

    @pytest.mark.asyncio
    async def test_file_operation_routing(self, router, available_servers):
        """Test routing of file operations"""
        request_text = "Read the contents of /tmp/config.txt"
        
        decision = await router.route_request(request_text, available_servers)
        
        assert "filesystem" in decision.matched_servers[0]
        assert decision.confidence > 0.5

    @pytest.mark.asyncio
    async def test_memory_operation_routing(self, router, available_servers):
        """Test routing of memory operations"""
        request_text = "Remember this important information for later"
        
        decision = await router.route_request(request_text, available_servers)
        
        assert "memory" in decision.matched_servers[0]
        assert decision.confidence > 0.5

    @pytest.mark.asyncio
    async def test_multi_domain_routing(self, router, available_servers):
        """Test routing that might involve multiple domains"""
        request_text = "Analyze weather data and generate a comprehensive report"
        
        decision = await router.route_request(request_text, available_servers)
        
        # Should route to multiple servers for analysis
        assert len(decision.matched_servers) >= 1
        assert decision.confidence > 0.3

    @pytest.mark.asyncio
    async def test_fallback_routing(self, router, available_servers):
        """Test fallback routing for unclear requests"""
        request_text = "Hello, how are you?"
        
        decision = await router.route_request(request_text, available_servers)
        
        # Should fallback to some server
        assert len(decision.matched_servers) >= 1
        assert decision.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_no_servers_available(self, router):
        """Test routing when no servers are available"""
        request_text = "What's the weather like?"
        
        decision = await router.route_request(request_text, [])
        
        assert len(decision.matched_servers) == 0
        assert decision.confidence == 0.0

    def test_add_custom_routing_rule(self, router):
        """Test adding custom routing rules"""
        custom_rule = RoutingRule(
            name="custom_rule",
            pattern=r"\bcustom\b",
            keywords=["custom"],
            server_names=["custom-server"],
            strategy=RoutingStrategy.SINGLE
        )
        
        router.add_routing_rule(custom_rule)
        
        # Check rule was added
        rule_names = [rule.name for rule in router.routing_rules]
        assert "custom_rule" in rule_names

    def test_remove_routing_rule(self, router):
        """Test removing routing rules"""
        initial_count = len(router.routing_rules)
        
        # Add a rule
        custom_rule = RoutingRule(
            name="temp_rule",
            pattern=r"\btemp\b",
            keywords=["temp"],
            server_names=["temp-server"],
            strategy=RoutingStrategy.SINGLE
        )
        router.add_routing_rule(custom_rule)
        
        # Remove the rule
        success = router.remove_routing_rule("temp_rule")
        assert success
        assert len(router.routing_rules) == initial_count

    @pytest.mark.asyncio
    async def test_request_analysis(self, router):
        """Test request analysis functionality"""
        request_text = "What's the current weather forecast for San Francisco?"
        
        analysis = await router.analyze_request(request_text)
        
        assert "weather" in analysis.keywords
        assert "forecast" in analysis.keywords
        assert analysis.domain == "weather"
        assert analysis.intent in ["query", "retrieval"]

    def test_performance_tracking(self, router):
        """Test performance tracking"""
        request_id = "test-request-123"
        
        # Record some performance data
        router.record_routing_performance(request_id, True, 0.5)
        
        stats = router.get_routing_stats()
        assert "performance_metrics" in stats