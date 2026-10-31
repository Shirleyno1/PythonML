
#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/aws-config.sh"

# AWS CLI wrapper
aws_cmd() {
    aws --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" "$@"
}

# Verify AWS CLI and account
verify_aws() {
    if ! command -v aws >/dev/null 2>&1; then
        echo "ERROR: AWS CLI is not installed."
        exit 1
    fi

    local account_id
    account_id=$(aws_cmd sts get-caller-identity \
        --query Account --output text)

    if [[ "$account_id" != "$EXPECTED_ACCOUNT_ID" ]]; then
        echo "ERROR: AWS account mismatch!"
        echo "Expected: $EXPECTED_ACCOUNT_ID"
        echo "Actual:   $account_id"
        exit 1
    fi

    echo "AWS account verified: $account_id"
    echo "Region: $AWS_REGION"
    echo "Cluster: $ECS_CLUSTER"
}

# Check whether Application Auto Scaling is configured
has_autoscaling() {
    local service="$1"

    local count
    count=$(aws_cmd application-autoscaling describe-scalable-targets \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id "service/$ECS_CLUSTER/$service" \
        --query 'length(ScalableTargets)' \
        --output text)

    [[ "$count" != "0" ]]
}

# Suspend or resume automatic scaling
set_autoscaling() {
    local service="$1"
    local suspended="$2"

    if has_autoscaling "$service"; then

        echo "Updating Auto Scaling: $service"

        aws_cmd application-autoscaling register-scalable-target \
            --service-namespace ecs \
            --scalable-dimension ecs:service:DesiredCount \
            --resource-id "service/$ECS_CLUSTER/$service" \
            --suspended-state \
            "DynamicScalingInSuspended=$suspended,DynamicScalingOutSuspended=$suspended,ScheduledScalingSuspended=$suspended" \
            >/dev/null
    else
        echo "No Auto Scaling target configured for $service"
    fi
}

# Start all ECS services
start_services() {
    echo ""
    echo "Starting AWS application..."
    echo "--------------------------"

    for service in "${ECS_SERVICES[@]}"; do

        echo "Starting: $service"

        # Resume automatic scaling first
        set_autoscaling "$service" false

        aws_cmd ecs update-service \
            --cluster "$ECS_CLUSTER" \
            --service "$service" \
            --desired-count "$START_TASK_COUNT" \
            >/dev/null

        echo "Waiting for $service to become stable..."

        aws_cmd ecs wait services-stable \
            --cluster "$ECS_CLUSTER" \
            --services "$service"

        echo "$service is running."
    done

    echo ""
    echo "AWS application started successfully."
}

# Stop all ECS services
stop_services() {
    echo ""
    echo "Stopping AWS application..."
    echo "---------------------------"

    for service in "${ECS_SERVICES[@]}"; do

        echo "Stopping: $service"

        # Prevent autoscaling from restarting tasks
        set_autoscaling "$service" true

        aws_cmd ecs update-service \
            --cluster "$ECS_CLUSTER" \
            --service "$service" \
            --desired-count 0 \
            >/dev/null

        echo "Waiting for $service to stop..."

        aws_cmd ecs wait services-stable \
            --cluster "$ECS_CLUSTER" \
            --services "$service"

        echo "$service stopped."
    done

    echo ""
    echo "AWS application stopped successfully."
}

# Show service status
show_status() {
    echo ""
    echo "AWS application status"
    echo "----------------------"

    aws_cmd ecs describe-services \
        --cluster "$ECS_CLUSTER" \
        --services "${ECS_SERVICES[@]}" \
        --query 'services[].{Service:serviceName,Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount}' \
        --output table
}

# Main entry point
verify_aws

case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: ./aws-app.sh {start|stop|status}"
        exit 1
        ;;
esac
