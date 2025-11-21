# How to Find Your Backend URL in Railway

After deploying your backend service, here's where to find the public URL:

## Method 1: Settings → Networking (Most Common)

1. **Click on your backend service** (`style-inspo-api` in the architecture diagram)
2. **Go to "Settings" tab**
3. **Scroll down to "Networking" or "Domains" section**
4. **Look for:**
   - A domain like: `https://style-inspo-api-production.up.railway.app`
   - Or a **"Generate Domain"** button
5. **If you see "Generate Domain":**
   - Click it
   - Railway will create a public URL
   - Copy the URL

## Method 2: Service Overview

1. **Click on your backend service**
2. **Check the main overview/Deployments tab**
3. **The URL might be displayed at the top** of the service page
4. **Look for a link** that says "Open" or shows the domain

## Method 3: Service Settings → Networking

1. **Click on your backend service**
2. **Go to "Settings" tab**
3. **Look for sections like:**
   - "Networking"
   - "Domains"
   - "Public URL"
   - "Service URL"

## What the URL Looks Like

Railway URLs typically look like:
```
https://style-inspo-api-production.up.railway.app
```
or
```
https://style-inspo-api.railway.app
```

## Test the URL

Once you have the URL, test it:
```
https://your-backend-url.railway.app/health
```

Should return: `{"status":"healthy","version":"1.0.0"}`

## If You Can't Find It

1. Make sure your service has finished deploying (green checkmark)
2. Check the "Deployments" tab - the URL might be in deployment logs
3. Railway might need you to generate a domain first
4. Some Railway plans require you to explicitly generate a public domain

## Next Step

Once you have the backend URL, you'll use it in Vercel:
- Environment variable: `NEXT_PUBLIC_API_URL`
- Value: `https://your-backend-url.railway.app`

