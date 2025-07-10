# src/services/tool_aggregator.py
"""
Tool Aggregator Service
Aggregates and manages tools from multiple MCP servers
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AggregatedTool:
    """Aggregated tool information"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str
    namespace: str
    full_name: str  # namespace.name
    last_updated: datetime


@dataclass
class ToolUsageStats:
    """Tool usage statistics"""
    tool_name: str
    call_count: int
    success_count: int
    error_count: int
    avg_response_time: float
    last_used: Optional[datetime] = None


class ToolAggregator:
    """Aggregates tools from multiple MCP servers"""
    
    def __init__(self):
        self.tools: Dict[str, AggregatedTool] = {}  # full_name -> tool
        self.tool_mappings: Dict[str, List[str]] = {}  # server_name -> tool_names
        self.usage_stats: Dict[str, ToolUsageStats] = {}
        self.tool_categories: Dict[str, Set[str]] = {}  # category -> tool_names
        
        # Tool categorization patterns
        self.category_patterns = {
            "data_retrieval": ["get", "fetch", "read", "list", "search", "find"],
            "data_modification": ["create", "update", "delete", "modify", "set", "write"],
            "communication": ["send", "notify", "message", "chat", "email"],
            "analysis": ["analyze", "calculate", "compute", "process", "evaluate"],
            "utility": ["convert", "transform", "format", "validate", "check"]
        }
    
    async def refresh_tools(self, server_name: str, tools: List[Dict[str, Any]]):
        """Refresh tools for a specific server"""
        # Remove existing tools for this server
        if server_name in self.tool_mappings:
            for tool_name in self.tool_mappings[server_name]:
                full_name = f"{server_name}.{tool_name}"
                if full_name in self.tools:
                    del self.tools[full_name]
        
        # Add new tools
        new_tool_names = []
        
        for tool_data in tools:
            tool_name = tool_data["name"]
            namespace = server_name
            full_name = f"{namespace}.{tool_name}"
            
            aggregated_tool = AggregatedTool(
                name=tool_name,
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_name=server_name,
                namespace=namespace,
                full_name=full_name,
                last_updated=datetime.utcnow()
            )
            
            self.tools[full_name] = aggregated_tool
            new_tool_names.append(tool_name)
            
            # Categorize tool
            self._categorize_tool(aggregated_tool)
        
        self.tool_mappings[server_name] = new_tool_names
        
        logger.info(f"Refreshed {len(new_tool_names)} tools for {server_name}")
    
    def _categorize_tool(self, tool: AggregatedTool):
        """Categorize tool based on name and description"""
        tool_text = (tool.name + " " + tool.description).lower()
        
        for category, patterns in self.category_patterns.items():
            if any(pattern in tool_text for pattern in patterns):
                if category not in self.tool_categories:
                    self.tool_categories[category] = set()
                self.tool_categories[category].add(tool.full_name)
    
    def get_all_tools(self) -> List[AggregatedTool]:
        """Get all aggregated tools"""
        return list(self.tools.values())
    
    def get_tools_by_server(self, server_name: str) -> List[AggregatedTool]:
        """Get tools for specific server"""
        return [
            tool for tool in self.tools.values()
            if tool.server_name == server_name
        ]
    
    def get_tools_by_category(self, category: str) -> List[AggregatedTool]:
        """Get tools by category"""
        if category not in self.tool_categories:
            return []
        
        return [
            self.tools[full_name]
            for full_name in self.tool_categories[category]
            if full_name in self.tools
        ]
    
    def search_tools(self, query: str, limit: int = 10) -> List[AggregatedTool]:
        """Search tools by name or description"""
        query_lower = query.lower()
        matches = []
        
        for tool in self.tools.values():
            score = 0
            
            # Name match (higher score)
            if query_lower in tool.name.lower():
                score += 10
            
            # Description match
            if query_lower in tool.description.lower():
                score += 5
            
            # Partial matches
            if any(word in tool.name.lower() for word in query_lower.split()):
                score += 3
            
            if any(word in tool.description.lower() for word in query_lower.split()):
                score += 2
            
            if score > 0:
                matches.append((tool, score))
        
        # Sort by score and return top results
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches[:limit]]
    
    def get_tool_by_name(self, full_name: str) -> Optional[AggregatedTool]:
        """Get tool by full name (namespace.name)"""
        return self.tools.get(full_name)
    
    def find_tools_for_intent(self, intent: str) -> List[AggregatedTool]:
        """Find tools that match a specific intent"""
        intent_mappings = {
            "query": ["data_retrieval"],
            "retrieval": ["data_retrieval"],
            "action": ["data_modification", "utility"],
            "modification": ["data_modification"],
            "communication": ["communication"],
            "analysis": ["analysis"]
        }
        
        relevant_categories = intent_mappings.get(intent.lower(), [])
        tools = []
        
        for category in relevant_categories:
            tools.extend(self.get_tools_by_category(category))
        
        return tools
    
    def record_tool_usage(self, full_name: str, success: bool, response_time: float):
        """Record tool usage statistics"""
        if full_name not in self.usage_stats:
            self.usage_stats[full_name] = ToolUsageStats(
                tool_name=full_name,
                call_count=0,
                success_count=0,
                error_count=0,
                avg_response_time=0.0
            )
        
        stats = self.usage_stats[full_name]
        stats.call_count += 1
        stats.last_used = datetime.utcnow()
        
        if success:
            stats.success_count += 1
        else:
            stats.error_count += 1
        
        # Update average response time
        total_time = stats.avg_response_time * (stats.call_count - 1) + response_time
        stats.avg_response_time = total_time / stats.call_count
    
    def get_tool_stats(self, full_name: str) -> Optional[ToolUsageStats]:
        """Get usage statistics for a tool"""
        return self.usage_stats.get(full_name)
    
    def get_popular_tools(self, limit: int = 10) -> List[tuple]:
        """Get most popular tools by usage"""
        sorted_stats = sorted(
            self.usage_stats.items(),
            key=lambda x: x[1].call_count,
            reverse=True
        )
        
        return [(name, stats) for name, stats in sorted_stats[:limit]]
    
    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics"""
        return {
            "total_tools": len(self.tools),
            "servers_count": len(self.tool_mappings),
            "categories": {
                category: len(tools)
                for category, tools in self.tool_categories.items()
            },
            "usage_stats_count": len(self.usage_stats),
            "tools_by_server": {
                server: len(tools)
                for server, tools in self.tool_mappings.items()
            }
        }
    
    def remove_server_tools(self, server_name: str):
        """Remove all tools for a server"""
        if server_name in self.tool_mappings:
            for tool_name in self.tool_mappings[server_name]:
                full_name = f"{server_name}.{tool_name}"
                
                # Remove from main tools dict
                if full_name in self.tools:
                    del self.tools[full_name]
                
                # Remove from categories
                for category, tool_set in self.tool_categories.items():
                    tool_set.discard(full_name)
                
                # Remove usage stats
                if full_name in self.usage_stats:
                    del self.usage_stats[full_name]
            
            del self.tool_mappings[server_name]
            logger.info(f"Removed all tools for {server_name}")


# Global tool aggregator instance
_tool_aggregator: Optional[ToolAggregator] = None


def get_tool_aggregator() -> ToolAggregator:
    """Get the global tool aggregator instance"""
    global _tool_aggregator
    if _tool_aggregator is None:
        _tool_aggregator = ToolAggregator()
    return _tool_aggregator