#!/bin/sh
# Daily analysis cron job - hits the backend endpoint
echo "Running daily analysis for $(date -u +%Y-%m-%d)..."
curl -X GET "${BACKEND_URL}/api/analysis/daily" -H "Content-Type: application/json"
echo ""
echo "Done!"
