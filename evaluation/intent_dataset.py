


TEST_CASES = [
    {
        "message": "Find my posts about Android",
        "expected_intent": "search",
        "expected_query": "Android"
    },

    {
        "message": "Show me posts about FastAPI",
        "expected_intent": "search",
        "expected_query": "FastAPI"
    },

    {
        "message": "Search for posts mentioning Python",
        "expected_intent": "search",
        "expected_query": "Python"
    },

    {
        "message": "Delete post 15",
        "expected_intent": "delete",
        "expected_post_id": 15
    },

    {
        "message": "Remove post 42",
        "expected_intent": "delete",
        "expected_post_id": 42
    },

    {
        "message": "I don't want post 42 anymore",
        "expected_intent": "delete"
    },

    {
        "message": "What is FastAPI?",
        "expected_intent": "general"
    },

    {
        "message": "Explain SQLAlchemy",
        "expected_intent": "general"
    },

    {
        "message": "show me my Android stuff",
        "expected_intent": "search"
    },

    {
        "message": "remove my latest",
        "expected_intent": "delete"
    },

    {
        "message": "find",
        "expected_intent": "search"
    },

    {
        "message": "show me that",
        "expected_intent": "search"
    },

    {
        "message": "delete",
        "expected_intent": "delete"
    },
]