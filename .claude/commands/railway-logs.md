# Railway Logs

View and search production logs from Railway backend services.

## Prerequisites
- Railway CLI must be linked to the project (run `railway link --project dazzling-enthusiasm` from backend/ directory if not linked)

## Commands

### List services
```bash
railway status --json | jq '.services.edges[].node.name'
```

Services available:
- `style-inspo-api` - Main FastAPI backend
- `RQ Worker` - Background job processor
- `Redis` - Job queue

### View recent logs (last N lines)
```bash
# Main API logs
railway logs --service style-inspo-api --lines 100

# RQ Worker logs (for background jobs)
railway logs --service "RQ Worker" --lines 100
```

### Search for errors
```bash
railway logs --service style-inspo-api --lines 200 --filter "@level:error"
```

### Search by keyword
```bash
railway logs --service style-inspo-api --lines 200 --since 7d 2>&1 | grep -i "keyword"
```

### Search by user
```bash
railway logs --service style-inspo-api --lines 500 --since 7d 2>&1 | grep -i "username"
```

### View logs from specific time range
```bash
# Last hour
railway logs --service style-inspo-api --lines 200 --since 1h

# Last day
railway logs --service style-inspo-api --lines 200 --since 1d

# Last week
railway logs --service style-inspo-api --lines 200 --since 7d
```

### Stream logs in real-time
```bash
railway logs --service style-inspo-api
```
(Note: This streams continuously, use Ctrl+C to stop)

## Common Debugging Patterns

### Product Link Extraction Errors
```bash
railway logs --service style-inspo-api --lines 200 --since 7d 2>&1 | grep -i -E "(extract|scrape|product|url)"
```

### Outfit Generation Errors
```bash
railway logs --service "RQ Worker" --lines 200 --since 1d 2>&1 | grep -i "error"
```

### User Activity
```bash
railway logs --service style-inspo-api --lines 300 --since 7d 2>&1 | grep -i "dimple"
```
