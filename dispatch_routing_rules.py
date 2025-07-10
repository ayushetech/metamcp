"""
Add this to your Meta MCP's routing configuration
"""

DISPATCH_ROUTING_RULES = {
    "keywords": {
        "dispatch": ["ticket", "queue", "technician", "assign", "workload", "tier", "psa", "hold", "requeue"],
        "actions": ["fetch", "pick", "complete", "assign", "update priority", "get activities"],
        "entities": ["tech", "technician", "msp", "ticket", "score", "workload"]
    },
    "patterns": [
        # Ticket queue operations
        r".*next ticket.*",
        r".*eligible ticket.*",
        r".*assign.*ticket.*",
        r".*complete.*ticket.*",
        r".*requeue.*ticket.*",
        r".*ticket.*priority.*",
        r".*ticket.*on hold.*",
        
        # Technician operations
        r".*technician.*workload.*",
        r".*tech.*activities.*",
        r".*current.*working.*",
        r".*assigned.*tickets.*",
        
        # Queue management
        r".*queue.*tickets.*",
        r".*recalculate.*scores.*",
        r".*ticket.*activities.*"
    ],
    "confidence_boost": 0.3  # Boost confidence when these patterns match
}

def should_route_to_dispatch(query: str) -> tuple[bool, float]:
    """
    Determine if a query should be routed to the Dispatch MCP server
    Returns (should_route, confidence_score)
    """
    query_lower = query.lower()
    confidence = 0.0
    
    # Check keywords
    keyword_matches = 0
    for keyword_list in DISPATCH_ROUTING_RULES["keywords"].values():
        for keyword in keyword_list:
            if keyword in query_lower:
                keyword_matches += 1
    
    if keyword_matches > 0:
        confidence = min(0.5 + (keyword_matches * 0.1), 0.9)
    
    # Check patterns
    import re
    for pattern in DISPATCH_ROUTING_RULES["patterns"]:
        if re.search(pattern, query_lower):
            confidence += DISPATCH_ROUTING_RULES["confidence_boost"]
            break
    
    # Cap confidence at 1.0
    confidence = min(confidence, 1.0)
    
    return confidence > 0.5, confidence