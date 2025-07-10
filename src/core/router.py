"""
Intelligent Request Router
Analyzes requests and routes them to appropriate MCP servers
"""

import asyncio
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategy options"""
    SINGLE = "single"           # Route to best matching server
    PARALLEL = "parallel"       # Route to multiple servers simultaneously  
    SEQUENTIAL = "sequential"   # Try servers in order of confidence
    FAILOVER = "failover"      # Fallback to next server on failure
    BROADCAST = "broadcast"     # Send to all matching servers


@dataclass
class RoutingRule:
    """Routing rule definition"""
    name: str
    pattern: str                # Regex or keyword pattern
    keywords: List[str]         # Keywords to match
    server_names: List[str]     # Target server names
    strategy: RoutingStrategy   # How to route
    priority: int = 50          # Rule priority (higher = checked first)
    confidence_threshold: float = 0.5  # Minimum confidence to trigger
    enabled: bool = True        # Whether rule is active


@dataclass 
class RoutingDecision:
    """Routing decision result"""
    request_id: str
    matched_servers: List[str]
    strategy: RoutingStrategy
    confidence: float
    reasoning: str
    matched_rules: List[str]
    fallback_servers: List[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class RequestAnalysis:
    """Request analysis result"""
    keywords: List[str]
    intent: str
    domain: str
    complexity: float
    urgency: str
    entities: List[Dict[str, Any]]


class RequestRouter:
    """
    Intelligent request router that analyzes requests and determines
    the best MCP server(s) to handle them
    """
    
    def __init__(self):
        self.routing_rules: List[RoutingRule] = []
        self.server_capabilities: Dict[str, Dict[str, Any]] = {}
        self.routing_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        
        # Load default routing rules
        self._load_default_rules()
        
        # Domain-specific keyword mappings
        self.domain_keywords = {
            "weather": [
                "weather", "temperature", "forecast", "climate", "rain", "snow", 
                "humidity", "wind", "storm", "sunny", "cloudy", "precipitation"
            ],
            "github": [
                "repository", "repo", "git", "commit", "pull request", "pr", 
                "issue", "code", "branch", "merge", "clone", "fork", "star"
            ],
            "filesystem": [
                "file", "folder", "directory", "path", "read", "write", "save",
                "load", "document", "text", "binary", "upload", "download"
            ],
            "memory": [
                "remember", "recall", "save", "store", "memory", "knowledge",
                "learn", "note", "information", "data", "retrieve", "search"
            ],
            "slack": [
                "message", "chat", "channel", "team", "notification", "send",
                "communicate", "workspace", "thread", "mention", "emoji"
            ],
            "database": [
                "database", "db", "sql", "query", "table", "select", "insert",
                "update", "delete", "postgres", "mysql", "sqlite", "schema"
            ]
        }
        
        # Intent patterns
        self.intent_patterns = {
            "query": [r"\b(what|how|when|where|who|which)\b", r"\?"],
            "action": [r"\b(create|make|build|generate|do)\b"],
            "modification": [r"\b(update|change|modify|edit|fix)\b"],
            "retrieval": [r"\b(get|fetch|find|search|look)\b"],
            "storage": [r"\b(save|store|remember|keep)\b"]
        }
    
    def _load_default_rules(self):
        """Load default routing rules"""
        default_rules = [
            RoutingRule(
                name="weather_queries",
                pattern=r"\b(weather|temperature|forecast|climate)\b",
                keywords=["weather", "temperature", "forecast"],
                server_names=["weather-mcp", "weather-server"],
                strategy=RoutingStrategy.SINGLE,
                priority=90,
                confidence_threshold=0.7
            ),
            RoutingRule(
                name="github_operations", 
                pattern=r"\b(repository|repo|git|github|code)\b",
                keywords=["repository", "repo", "git", "code"],
                server_names=["github-mcp", "github-server"],
                strategy=RoutingStrategy.SINGLE,
                priority=85,
                confidence_threshold=0.6
            ),
            RoutingRule(
                name="file_operations",
                pattern=r"\b(file|folder|directory|read|write)\b", 
                keywords=["file", "folder", "directory"],
                server_names=["filesystem-mcp", "filesystem-server"],
                strategy=RoutingStrategy.SINGLE,
                priority=80,
                confidence_threshold=0.6
            ),
            RoutingRule(
                name="memory_operations",
                pattern=r"\b(remember|recall|save|store|memory)\b",
                keywords=["remember", "memory", "store"],
                server_names=["memory-mcp", "memory-server"], 
                strategy=RoutingStrategy.SINGLE,
                priority=75,
                confidence_threshold=0.6
            ),
            RoutingRule(
                name="communication",
                pattern=r"\b(message|chat|send|notify|slack)\b",
                keywords=["message", "chat", "send", "slack"],
                server_names=["slack-mcp", "slack-server"],
                strategy=RoutingStrategy.SINGLE,
                priority=70,
                confidence_threshold=0.6
            ),
            RoutingRule(
                name="database_queries",
                pattern=r"\b(database|sql|query|table|select)\b",
                keywords=["database", "sql", "query"],
                server_names=["postgres-mcp", "database-server"],
                strategy=RoutingStrategy.SINGLE,
                priority=65,
                confidence_threshold=0.6
            ),
            RoutingRule(
                name="multi_domain_analysis",
                pattern=r"\b(analyze|report|dashboard|summary)\b",
                keywords=["analyze", "report", "dashboard"],
                server_names=["github-mcp", "memory-mcp", "filesystem-mcp"],
                strategy=RoutingStrategy.PARALLEL,
                priority=60,
                confidence_threshold=0.4
            )
        ]
        
        self.routing_rules.extend(default_rules)
        logger.info(f"Loaded {len(default_rules)} default routing rules")
    
    async def analyze_request(self, request_text: str, context: Optional[Dict[str, Any]] = None) -> RequestAnalysis:
        """
        Analyze request to extract intent, keywords, and routing hints
        """
        request_text_lower = request_text.lower()
        
        # Extract keywords
        keywords = self._extract_keywords(request_text_lower)
        
        # Determine intent
        intent = self._determine_intent(request_text_lower)
        
        # Identify domain
        domain = self._identify_domain(keywords, request_text_lower)
        
        # Calculate complexity
        complexity = self._calculate_complexity(request_text, keywords)
        
        # Determine urgency
        urgency = self._determine_urgency(request_text_lower, context)
        
        # Extract entities
        entities = self._extract_entities(request_text)
        
        return RequestAnalysis(
            keywords=keywords,
            intent=intent,
            domain=domain,
            complexity=complexity,
            urgency=urgency,
            entities=entities
        )
    
    async def route_request(
        self, 
        request_text: str, 
        available_servers: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """
        Main routing method - analyzes request and returns routing decision
        """
        request_id = context.get("request_id", "unknown") if context else "unknown"
        
        # Analyze the request
        analysis = await self.analyze_request(request_text, context)
        
        # Find matching rules
        matched_rules = []
        rule_scores = []
        
        for rule in sorted(self.routing_rules, key=lambda r: r.priority, reverse=True):
            if not rule.enabled:
                continue
                
            confidence = self._calculate_rule_confidence(rule, analysis, request_text)
            
            if confidence >= rule.confidence_threshold:
                # Check if target servers are available
                available_targets = [s for s in rule.server_names if s in available_servers]
                
                if available_targets:
                    matched_rules.append(rule.name)
                    rule_scores.append({
                        "rule": rule,
                        "confidence": confidence,
                        "available_servers": available_targets
                    })
        
        # If no rules matched, use fallback routing
        if not rule_scores:
            return await self._fallback_routing(analysis, available_servers, request_id)
        
        # Select best matching rule
        best_rule_score = max(rule_scores, key=lambda x: x["confidence"])
        best_rule = best_rule_score["rule"]
        best_confidence = best_rule_score["confidence"]
        target_servers = best_rule_score["available_servers"]
        
        # Build reasoning
        reasoning = self._build_reasoning(analysis, best_rule, best_confidence, target_servers)
        
        # Determine fallback servers
        fallback_servers = self._get_fallback_servers(
            target_servers, available_servers, analysis
        )
        
        # Record routing decision
        routing_decision = RoutingDecision(
            request_id=request_id,
            matched_servers=target_servers,
            strategy=best_rule.strategy,
            confidence=best_confidence,
            reasoning=reasoning,
            matched_rules=matched_rules,
            fallback_servers=fallback_servers,
            metadata={
                "analysis": analysis.__dict__,
                "rule_name": best_rule.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Store for learning
        self._record_routing_decision(routing_decision)
        
        return routing_decision
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from request text"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'about', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
            'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should',
            'now', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
            'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'doing', 'done'
        }
        
        # Extract words (alphanumeric + underscore)
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and short words
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return list(set(keywords))  # Remove duplicates
    
    def _determine_intent(self, text: str) -> str:
        """Determine the intent of the request"""
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return intent
        
        return "unknown"
    
    def _identify_domain(self, keywords: List[str], text: str) -> str:
        """Identify the domain of the request"""
        domain_scores = {}
        
        for domain, domain_keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in domain_keywords:
                    score += 2
                elif any(dk in keyword for dk in domain_keywords):
                    score += 1
            
            domain_scores[domain] = score
        
        if domain_scores:
            best_domain = max(domain_scores, key=domain_scores.get)
            if domain_scores[best_domain] > 0:
                return best_domain
        
        return "general"
    
    def _calculate_complexity(self, text: str, keywords: List[str]) -> float:
        """Calculate request complexity (0.0 to 1.0)"""
        factors = []
        
        # Length factor
        factors.append(min(len(text) / 1000, 1.0))
        
        # Keyword count factor
        factors.append(min(len(keywords) / 20, 1.0))
        
        # Question complexity
        question_words = len(re.findall(r'\b(what|how|when|where|who|which|why)\b', text.lower()))
        factors.append(min(question_words / 5, 1.0))
        
        # Multi-step indicators
        multi_step_indicators = ['then', 'after', 'next', 'also', 'and then', 'followed by']
        multi_step_count = sum(1 for indicator in multi_step_indicators if indicator in text.lower())
        factors.append(min(multi_step_count / 3, 1.0))
        
        return sum(factors) / len(factors)
    
    def _determine_urgency(self, text: str, context: Optional[Dict[str, Any]]) -> str:
        """Determine request urgency"""
        urgent_indicators = ['urgent', 'asap', 'immediately', 'emergency', 'critical', 'now']
        
        if any(indicator in text for indicator in urgent_indicators):
            return "high"
        elif any(word in text for word in ['quick', 'fast', 'soon']):
            return "medium"
        else:
            return "normal"
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from request text"""
        entities = []
        
        # Extract URLs
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        entities.extend([{"type": "url", "value": url} for url in urls])
        
        # Extract file paths
        file_paths = re.findall(r'[./][\w./\-]+\.\w+', text)
        entities.extend([{"type": "file_path", "value": path} for path in file_paths])
        
        # Extract email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entities.extend([{"type": "email", "value": email} for email in emails])
        
        # Extract GitHub repository references
        github_repos = re.findall(r'\b[\w-]+/[\w-]+(?:\.git)?\b', text)
        entities.extend([{"type": "github_repo", "value": repo} for repo in github_repos])
        
        return entities
    
    def _calculate_rule_confidence(self, rule: RoutingRule, analysis: RequestAnalysis, text: str) -> float:
        """Calculate confidence for a specific rule"""
        confidence_factors = []
        
        # Pattern matching
        if re.search(rule.pattern, text, re.IGNORECASE):
            confidence_factors.append(0.8)
        
        # Keyword matching
        keyword_matches = sum(1 for keyword in rule.keywords if keyword in analysis.keywords)
        if rule.keywords:
            keyword_confidence = keyword_matches / len(rule.keywords)
            confidence_factors.append(keyword_confidence)
        
        # Domain matching
        if analysis.domain in [name.split('-')[0] for name in rule.server_names]:
            confidence_factors.append(0.6)
        
        # Intent matching (basic)
        if analysis.intent in ["query", "retrieval"] and "weather" in rule.name:
            confidence_factors.append(0.5)
        elif analysis.intent in ["action", "modification"] and "github" in rule.name:
            confidence_factors.append(0.5)
        
        # Performance history boost
        avg_performance = self.performance_metrics.get(rule.name, {}).get("avg_success_rate", 0.5)
        confidence_factors.append(avg_performance * 0.3)  # Small boost for good performance
        
        if not confidence_factors:
            return 0.0
        
        return sum(confidence_factors) / len(confidence_factors)
    
    async def _fallback_routing(self, analysis: RequestAnalysis, available_servers: List[str], request_id: str) -> RoutingDecision:
        """Fallback routing when no rules match"""
        # Try domain-based routing
        domain_server_map = {
            "weather": ["weather-mcp", "weather-server"],
            "github": ["github-mcp", "github-server"],
            "filesystem": ["filesystem-mcp", "filesystem-server"],
            "memory": ["memory-mcp", "memory-server"],
            "slack": ["slack-mcp", "slack-server"],
            "database": ["postgres-mcp", "database-server"]
        }
        
        if analysis.domain in domain_server_map:
            candidate_servers = domain_server_map[analysis.domain]
            available_candidates = [s for s in candidate_servers if s in available_servers]
            
            if available_candidates:
                return RoutingDecision(
                    request_id=request_id,
                    matched_servers=available_candidates[:1],  # Take first available
                    strategy=RoutingStrategy.SINGLE,
                    confidence=0.4,
                    reasoning=f"Fallback routing based on domain: {analysis.domain}",
                    matched_rules=["fallback_domain"],
                    fallback_servers=available_candidates[1:] if len(available_candidates) > 1 else []
                )
        
        # Ultimate fallback - route to first available server
        if available_servers:
            return RoutingDecision(
                request_id=request_id,
                matched_servers=[available_servers[0]],
                strategy=RoutingStrategy.SINGLE,
                confidence=0.2,
                reasoning="Ultimate fallback to first available server",
                matched_rules=["ultimate_fallback"],
                fallback_servers=available_servers[1:] if len(available_servers) > 1 else []
            )
        
        # No servers available
        return RoutingDecision(
            request_id=request_id,
            matched_servers=[],
            strategy=RoutingStrategy.SINGLE,
            confidence=0.0,
            reasoning="No available servers found",
            matched_rules=["no_route"],
            fallback_servers=[]
        )
    
    def _build_reasoning(self, analysis: RequestAnalysis, rule: RoutingRule, confidence: float, servers: List[str]) -> str:
        """Build human-readable reasoning for routing decision"""
        reasoning_parts = []
        
        reasoning_parts.append(f"Matched rule '{rule.name}' with {confidence:.2f} confidence")
        reasoning_parts.append(f"Detected domain: {analysis.domain}")
        reasoning_parts.append(f"Identified intent: {analysis.intent}")
        
        if analysis.keywords:
            key_keywords = analysis.keywords[:3]  # Show top 3 keywords
            reasoning_parts.append(f"Key keywords: {', '.join(key_keywords)}")
        
        reasoning_parts.append(f"Routing to server(s): {', '.join(servers)}")
        reasoning_parts.append(f"Strategy: {rule.strategy.value}")
        
        return " | ".join(reasoning_parts)
    
    def _get_fallback_servers(self, primary_servers: List[str], available_servers: List[str], analysis: RequestAnalysis) -> List[str]:
        """Get fallback servers for the request"""
        fallback_servers = []
        
        # Remove primary servers from available list
        remaining_servers = [s for s in available_servers if s not in primary_servers]
        
        # Add domain-related servers as fallbacks
        if analysis.domain != "general":
            domain_servers = [s for s in remaining_servers if analysis.domain in s.lower()]
            fallback_servers.extend(domain_servers)
        
        # Add general-purpose servers
        general_servers = [s for s in remaining_servers if s not in fallback_servers]
        fallback_servers.extend(general_servers[:2])  # Limit to 2 fallback servers
        
        return fallback_servers
    
    def _record_routing_decision(self, decision: RoutingDecision):
        """Record routing decision for learning"""
        self.routing_history.append({
            "request_id": decision.request_id,
            "matched_servers": decision.matched_servers,
            "strategy": decision.strategy.value,
            "confidence": decision.confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "matched_rules": decision.matched_rules
        })
        
        # Keep only last 1000 decisions
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add a custom routing rule"""
        # Remove existing rule with same name
        self.routing_rules = [r for r in self.routing_rules if r.name != rule.name]
        self.routing_rules.append(rule)
        logger.info(f"Added routing rule: {rule.name}")
    
    def remove_routing_rule(self, rule_name: str) -> bool:
        """Remove a routing rule"""
        initial_count = len(self.routing_rules)
        self.routing_rules = [r for r in self.routing_rules if r.name != rule_name]
        removed = len(self.routing_rules) < initial_count
        
        if removed:
            logger.info(f"Removed routing rule: {rule_name}")
        
        return removed
    
    def update_server_capabilities(self, server_name: str, capabilities: Dict[str, Any]):
        """Update server capabilities for better routing"""
        self.server_capabilities[server_name] = capabilities
        logger.debug(f"Updated capabilities for {server_name}")
    
    def record_routing_performance(self, request_id: str, success: bool, response_time: float):
        """Record performance metrics for learning"""
        # Find the routing decision
        decision = next(
            (d for d in self.routing_history if d["request_id"] == request_id),
            None
        )
        
        if decision and decision["matched_rules"]:
            for rule_name in decision["matched_rules"]:
                if rule_name not in self.performance_metrics:
                    self.performance_metrics[rule_name] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "total_response_time": 0.0,
                        "avg_success_rate": 0.5,
                        "avg_response_time": 0.0
                    }
                
                metrics = self.performance_metrics[rule_name]
                metrics["total_requests"] += 1
                
                if success:
                    metrics["successful_requests"] += 1
                
                metrics["total_response_time"] += response_time
                
                # Update averages
                metrics["avg_success_rate"] = metrics["successful_requests"] / metrics["total_requests"]
                metrics["avg_response_time"] = metrics["total_response_time"] / metrics["total_requests"]
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "total_rules": len(self.routing_rules),
            "enabled_rules": len([r for r in self.routing_rules if r.enabled]),
            "routing_history_size": len(self.routing_history),
            "performance_metrics": self.performance_metrics,
            "server_capabilities": self.server_capabilities
        }


# Global router instance
_router: Optional[RequestRouter] = None


def get_router() -> RequestRouter:
    """Get the global router instance"""
    global _router
    if _router is None:
        _router = RequestRouter()
    return _router