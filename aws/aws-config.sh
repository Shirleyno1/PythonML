
#!/bin/bash

# AWS configuration. Defaults match the deploy-aws workflow's region.
AWS_REGION="${AWS_REGION:-ap-southeast-2}"
AWS_PROFILE="${AWS_PROFILE:-ai-learning}"

# Set to your AWS account ID before using aws-app.sh.
EXPECTED_ACCOUNT_ID="${EXPECTED_ACCOUNT_ID:-YOUR_ACCOUNT_ID}"

# These names correspond to the deploy-aws workflow configuration.
ECS_CLUSTER="${ECS_CLUSTER:-YOUR_ECS_CLUSTER}"
API_ECS_SERVICE="${API_ECS_SERVICE:-YOUR_API_ECS_SERVICE}"
MCP_ECS_SERVICE="${MCP_ECS_SERVICE:-YOUR_MCP_ECS_SERVICE}"

# Actual ECS service names, not Docker Compose service names
ECS_SERVICES=(
    "$API_ECS_SERVICE"
    "$MCP_ECS_SERVICE"
)

# Number of tasks to run when starting
START_TASK_COUNT=1
