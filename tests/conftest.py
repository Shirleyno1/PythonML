import os

# Set before settings/config.py loads .env, which doesn't override existing
# values, so test runs never send traces to LangSmith.
os.environ["LANGSMITH_TRACING"] = "false"
