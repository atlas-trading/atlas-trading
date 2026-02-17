#!/usr/bin/env bash
#
# Blue-Green Deployment Script for Atlas Trading
#
# Usage:
#   ./deploy-bluegreen.sh <component> <new-image-tag>
#
# Example:
#   ./deploy-bluegreen.sh api-server v1.2.3
#   ./deploy-bluegreen.sh web-dashboard v1.2.3

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="atlas-trading"
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=5   # 5 seconds

# Validate arguments
if [ $# -ne 2 ]; then
    echo -e "${RED}Usage: $0 <component> <new-image-tag>${NC}"
    echo "  component: api-server or web-dashboard"
    echo "  new-image-tag: Docker image tag (e.g., v1.2.3)"
    exit 1
fi

COMPONENT=$1
NEW_TAG=$2
IMAGE_REPO="atlas-trading/${COMPONENT}"

# Validate component
if [[ "$COMPONENT" != "api-server" && "$COMPONENT" != "web-dashboard" ]]; then
    echo -e "${RED}Invalid component: $COMPONENT${NC}"
    echo "Must be 'api-server' or 'web-dashboard'"
    exit 1
fi

echo -e "${GREEN}=== Atlas Trading Blue-Green Deployment ===${NC}"
echo "Component: $COMPONENT"
echo "New Image: $IMAGE_REPO:$NEW_TAG"
echo "Namespace: $NAMESPACE"
echo ""

# Get current active version
CURRENT_VERSION=$(kubectl get service "$COMPONENT" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}')
echo -e "Current active version: ${YELLOW}$CURRENT_VERSION${NC}"

# Determine new version (opposite of current)
if [ "$CURRENT_VERSION" == "blue" ]; then
    NEW_VERSION="green"
    OLD_VERSION="blue"
else
    NEW_VERSION="blue"
    OLD_VERSION="green"
fi

echo -e "Deploying to: ${GREEN}$NEW_VERSION${NC}"
echo ""

# Step 1: Update the new version deployment
echo -e "${YELLOW}[1/5] Updating $NEW_VERSION deployment...${NC}"
kubectl set image deployment/"${COMPONENT}-${NEW_VERSION}" \
    "$COMPONENT"="$IMAGE_REPO:$NEW_TAG" \
    -n "$NAMESPACE"

# Wait for rollout
kubectl rollout status deployment/"${COMPONENT}-${NEW_VERSION}" \
    -n "$NAMESPACE" \
    --timeout=300s

echo -e "${GREEN}✓ Deployment updated${NC}"
echo ""

# Step 2: Health check
echo -e "${YELLOW}[2/5] Running health checks...${NC}"
ELAPSED=0
HEALTHY=false

while [ $ELAPSED -lt $HEALTH_CHECK_TIMEOUT ]; do
    # Check if all pods are ready
    READY_REPLICAS=$(kubectl get deployment "${COMPONENT}-${NEW_VERSION}" \
        -n "$NAMESPACE" \
        -o jsonpath='{.status.readyReplicas}')

    DESIRED_REPLICAS=$(kubectl get deployment "${COMPONENT}-${NEW_VERSION}" \
        -n "$NAMESPACE" \
        -o jsonpath='{.spec.replicas}')

    if [ "$READY_REPLICAS" == "$DESIRED_REPLICAS" ]; then
        echo -e "${GREEN}✓ All $DESIRED_REPLICAS replicas are ready${NC}"
        HEALTHY=true
        break
    fi

    echo "Waiting for pods... ($READY_REPLICAS/$DESIRED_REPLICAS ready)"
    sleep $HEALTH_CHECK_INTERVAL
    ELAPSED=$((ELAPSED + HEALTH_CHECK_INTERVAL))
done

if [ "$HEALTHY" != "true" ]; then
    echo -e "${RED}✗ Health check failed after ${HEALTH_CHECK_TIMEOUT}s${NC}"
    echo "Rolling back..."
    kubectl rollout undo deployment/"${COMPONENT}-${NEW_VERSION}" -n "$NAMESPACE"
    exit 1
fi

echo ""

# Step 3: Switch traffic
echo -e "${YELLOW}[3/5] Switching traffic to $NEW_VERSION...${NC}"
kubectl patch service "$COMPONENT" \
    -n "$NAMESPACE" \
    -p "{\"spec\":{\"selector\":{\"version\":\"$NEW_VERSION\"}}}"

echo -e "${GREEN}✓ Traffic switched to $NEW_VERSION${NC}"
echo ""

# Step 4: Verify traffic switch
echo -e "${YELLOW}[4/5] Verifying traffic switch...${NC}"
sleep 5

ACTIVE_VERSION=$(kubectl get service "$COMPONENT" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}')
if [ "$ACTIVE_VERSION" == "$NEW_VERSION" ]; then
    echo -e "${GREEN}✓ Traffic is now routed to $NEW_VERSION${NC}"
else
    echo -e "${RED}✗ Traffic switch verification failed${NC}"
    exit 1
fi

echo ""

# Step 5: Scale down old version (optional)
echo -e "${YELLOW}[5/5] Scaling down old version ($OLD_VERSION)...${NC}"
read -p "Scale down $OLD_VERSION deployment to 0 replicas? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl scale deployment/"${COMPONENT}-${OLD_VERSION}" \
        --replicas=0 \
        -n "$NAMESPACE"
    echo -e "${GREEN}✓ Old version scaled down${NC}"
else
    echo "Keeping $OLD_VERSION running for rollback"
fi

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo "Component: $COMPONENT"
echo "Active Version: $NEW_VERSION"
echo "Image: $IMAGE_REPO:$NEW_TAG"
echo ""
echo "To rollback:"
echo "  kubectl patch service $COMPONENT -n $NAMESPACE -p '{\"spec\":{\"selector\":{\"version\":\"$OLD_VERSION\"}}}'"
