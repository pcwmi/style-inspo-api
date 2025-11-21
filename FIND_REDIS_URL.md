# How to Find Redis URL in Railway

After adding a Redis service to your Railway project, here's where to find the connection URL:

## Method 1: Variables Tab (Most Common)

1. **Click on the Redis service** in your Railway project
   - It will be listed alongside your backend service
   - Usually named "Redis" or similar

2. **Go to the "Variables" tab**
   - This is in the top navigation of the Redis service page

3. **Look for one of these variables:**
   - `REDIS_URL` (most common)
   - `DATABASE_URL` (sometimes Railway uses this name)
   - `REDISCLOUD_URL` (if using Redis Cloud)

4. **Reveal the value:**
   - Click the **👁️ eye icon** next to the variable
   - This will show the full URL
   - Copy the entire URL

5. **The URL format will be:**
   ```
   redis://default:password@hostname.railway.app:6379
   ```
   or
   ```
   redis://:password@hostname.railway.app:6379
   ```

## Method 2: Connect/Info Tab

Some Railway Redis services show the connection info in:
- **Connect** tab
- **Info** tab
- **Overview** tab

Look for connection strings or connection details.

## Method 3: Service Overview

Sometimes Railway displays the connection URL directly in the service overview page.

## What to Do With the URL

Once you have the Redis URL:

1. **Add it to your backend service environment variables:**
   - Go to your **backend service** (not Redis service)
   - Go to **Variables** tab
   - Add new variable:
     - Name: `REDIS_URL`
     - Value: (paste the Redis URL you copied)

2. **Also add it to your worker service** (if you create a separate worker):
   - Same process - add `REDIS_URL` to the worker's environment variables

## Example

If your Redis URL is:
```
redis://default:abc123xyz@redis-production.up.railway.app:6379
```

Add it to your backend service variables as:
```
REDIS_URL=redis://default:abc123xyz@redis-production.up.railway.app:6379
```

## Troubleshooting

**Can't find the URL?**
- Make sure the Redis service has finished provisioning (wait a minute)
- Try refreshing the page
- Check if there's a "Generate URL" or "Copy Connection String" button

**URL format looks different?**
- That's okay! Railway may use different formats
- Just copy the entire value as-is
- The RQ library will handle the connection

