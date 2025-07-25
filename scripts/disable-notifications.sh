#!/bin/bash
# Script to disable Azure DevOps pipeline email notifications
# Usage: ./scripts/disable-notifications.sh [organization] [project]

set -e

# Default values from environment/config
ORGANIZATION="${1:-RussellBoley}"
PROJECT_NAME="${2:-ado-mcp2}"

echo "🔧 Disabling pipeline notifications for organization '$ORGANIZATION', project '$PROJECT_NAME'"

# Get PAT from environment variable or .env file
PAT="$AZURE_DEVOPS_EXT_PAT"
if [[ -z "$PAT" && -f ".env" ]]; then
    echo "Reading PAT from .env file..."
    PAT=$(grep "AZURE_DEVOPS_EXT_PAT=" .env | cut -d'=' -f2 | tr -d '"')
fi

if [[ -z "$PAT" ]]; then
    echo "❌ AZURE_DEVOPS_EXT_PAT not found in environment variable or .env file"
    exit 1
fi

BASE_URL="https://dev.azure.com/$ORGANIZATION"
SUBSCRIPTIONS_URL="$BASE_URL/_apis/notification/subscriptions?api-version=7.1-preview.1"

echo "📡 Fetching notification subscriptions..."

# Get all notification subscriptions
RESPONSE=$(curl -s -u ":$PAT" \
    -H "Accept: application/json" \
    "$SUBSCRIPTIONS_URL")

# Check if the request was successful
if [[ $? -ne 0 ]]; then
    echo "❌ Failed to fetch notification subscriptions"
    exit 1
fi

# Extract pipeline-related subscriptions using jq
PIPELINE_SUBSCRIPTIONS=$(echo "$RESPONSE" | jq -r '.value[] | select(
    (.description // "" | test("build|pipeline|release|deployment"; "i")) or 
    (.eventType // "" | test("build|pipeline|release"; "i"))
) | @base64')

if [[ -z "$PIPELINE_SUBSCRIPTIONS" ]]; then
    echo "✅ No pipeline-related notification subscriptions found (already disabled or not configured)"
    exit 0
fi

DISABLED_COUNT=0
SKIPPED_COUNT=0
TOTAL_COUNT=0

echo "📋 Found pipeline-related notification subscriptions:"

# Process each subscription
while IFS= read -r subscription_b64; do
    [[ -z "$subscription_b64" ]] && continue
    
    SUBSCRIPTION=$(echo "$subscription_b64" | base64 --decode)
    SUBSCRIPTION_ID=$(echo "$SUBSCRIPTION" | jq -r '.id')
    DESCRIPTION=$(echo "$SUBSCRIPTION" | jq -r '.description // "Unknown"')
    STATUS=$(echo "$SUBSCRIPTION" | jq -r '.status // "unknown"')
    
    echo "   - $DESCRIPTION (Status: $STATUS)"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    
    if [[ "$STATUS" == "disabled" || "$STATUS" == "disabledByAdmin" ]]; then
        echo "⏭️  Skipping already disabled: $DESCRIPTION"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi
    
    echo "🔧 Disabling: $DESCRIPTION"
    
    # Update subscription to disable it
    UPDATE_URL="$BASE_URL/_apis/notification/subscriptions/$SUBSCRIPTION_ID?api-version=7.1-preview.1"
    UPDATE_BODY='{"id":"'$SUBSCRIPTION_ID'","status":"disabled"}'
    
    RESULT=$(curl -s -w "%{http_code}" -u ":$PAT" \
        -X PATCH \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$UPDATE_BODY" \
        "$UPDATE_URL")
    
    HTTP_CODE="${RESULT: -3}"
    
    if [[ "$HTTP_CODE" =~ ^2[0-9][0-9]$ ]]; then
        echo "✅ Disabled: $DESCRIPTION"
        DISABLED_COUNT=$((DISABLED_COUNT + 1))
    else
        echo "❌ Failed to disable: $DESCRIPTION (HTTP $HTTP_CODE)"
    fi
    
done <<< "$PIPELINE_SUBSCRIPTIONS"

echo ""
echo "🎉 Notification update complete!"
echo "   - Disabled: $DISABLED_COUNT subscriptions"
echo "   - Already disabled: $SKIPPED_COUNT subscriptions" 
echo "   - Total processed: $TOTAL_COUNT subscriptions"

if [[ $DISABLED_COUNT -gt 0 ]]; then
    echo ""
    echo "📧 You should now receive fewer email notifications for pipeline builds, deployments, and releases."
    echo "💡 You can re-enable notifications anytime through Azure DevOps web interface."
fi