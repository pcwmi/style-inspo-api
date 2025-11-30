# Diagnostic Script Instructions

## React Query Hook Diagnostic Page

I've created a diagnostic page at `/debug-considering` that will test the React Query hook and show you exactly what's happening.

### How to Use

1. **Start your frontend server** (if not already running):
   ```bash
   cd frontend
   npm run dev
   ```

2. **Navigate to the diagnostic page**:
   ```
   http://localhost:3000/debug-considering?user=peichin&status=considering
   ```

   Or in production:
   ```
   https://styleinspo.vercel.app/debug-considering?user=peichin&status=considering
   ```

3. **Check the diagnostic output**:
   - Query State: Shows if the query is loading, fetching, successful, or errored
   - Response Data: Shows the actual data structure returned
   - Expected vs Actual: Compares expected (34) vs actual count

### What to Look For

1. **Query Status**: Should be "success" if working correctly
2. **Items Count**: Should show 34 items
3. **Data Structure**: Should have `{items: [...]}` format
4. **Error Messages**: Any errors will be displayed in red

### Additional Testing

You can also test with different statuses:
- `?user=peichin&status=considering` - Should return 34 items
- `?user=peichin&status=passed` - Should return 2 items
- `?user=peichin&status=later` - Should return 3 items
- `?user=peichin` (no status) - Should return all 39 items

### Console Logging

The page will also log to browser console. Open DevTools Console to see:
- React Query cache state
- Network requests
- Any errors

### Next Steps After Diagnosis

Once you see the diagnostic output, we can:
1. Identify if the issue is with the query hook
2. Check if data structure is mismatched
3. Verify React Query cache behavior
4. Fix the root cause based on actual findings

