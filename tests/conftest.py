import os

# Set before settings/config.py loads .env, which doesn't override existing
# values, so test runs never send traces to LangSmith.
os.environ["LANGSMITH_TRACING"] = "false"

# posts.images creates its client on import, which fails without a key. A fake
# one also means test runs can never upload with real credentials.
os.environ["IMAGEKIT_PRIVATE_KEY"] = "test-key"

# Blank rather than unset, so .env can't fill it in: local runs then match CI,
# which has no OpenAI key, and tests can never call OpenAI with a real one.
os.environ["OPENAI_API_KEY"] = ""
