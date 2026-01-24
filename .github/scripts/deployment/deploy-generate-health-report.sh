#!/bin/bash
# Generate health check report
# Arguments: All variables should be set in environment

{
  echo "### Enhanced Service Health Report"
  if [ "$IS_ROLLBACK" = "true" ]; then
    echo "(Rollback)"
  else
    echo "(Deployment)"
  fi
  echo ""
  echo "#### Availability Test Results"
  echo "- **Max Retries**: $MAX_RETRIES"
  echo "- **Successful After**: $((RETRY_COUNT + 1)) attempts"
  echo "- **Total Wait Time**: ${TOTAL_WAIT_TIME}s"
  echo "- **Final HTTP Code**: $HTTP_CODE"
  echo "- **Average Response Time**: ${AVG_RESPONSE_TIME}ms"
  echo ""
  echo "#### Functionality Test Results"
  if [ -n "$PASTE_RESPONSE" ]; then
    echo "- **Paste Creation**: ✅ Success"
  else
    echo "- **Paste Creation**: ❌ Failed"
  fi
  echo "- **Paste Creation Time**: ${PASTE_CREATE_TIME}ms"
  if [ "$RETRIEVED_CONTENT" = "$TEST_CONTENT" ]; then
    echo "- **Paste Retrieval**: ✅ Success"
  else
    echo "- **Paste Retrieval**: ⚠️ Warning"
  fi
  echo "- **Paste Retrieval Time**: ${PASTE_RETRIEVE_TIME}ms"
  echo "- **Health Endpoint**: HTTP $HEALTH_ENDPOINT_RESPONSE"
  echo "- **Static Resources**: HTTP $STATIC_RESPONSE"
  echo ""
  echo "#### Overall Status"
  echo "- **Health Status**: $HEALTH_STATUS"
  echo "- **Details**: $HEALTH_DETAILS"
  echo "- **Test Timestamp**: $HEALTH_TIMESTAMP"
  if [ "$IS_ROLLBACK" = "true" ]; then
    echo "- **Test Type**: Rollback Health Check"
  else
    echo "- **Test Type**: Deployment Health Check"
  fi
} > /tmp/health_report.txt
