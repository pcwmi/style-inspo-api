# Custom Domain Setup Guide - Fix Arc Mobile SSL Issue

## Why Custom Domain Solves the Problem

**Vercel Support Confirmation:**
> "Custom domains on Vercel receive their own SSL certificates (also from Let's Encrypt or Google Trust Services) but with a different certificate chain structure that Arc browser handles correctly. Custom domains bypass whatever specific validation quirk Arc has with .vercel.app wildcard certificates."

**Technical Explanation:**
- `.vercel.app` domains use a **wildcard certificate** (`*.vercel.app`) shared across all Vercel projects
- Arc mobile browser has a compatibility issue with this specific wildcard certificate chain
- Custom domains get their **own dedicated certificate** with a different chain structure
- Arc's validation engine handles custom domain certificates correctly

## Step-by-Step Setup

### Prerequisites
- A domain name (e.g., `styleinspo.com`, `styleinspo.app`, etc.)
- Access to your domain's DNS settings (wherever you registered the domain)

### Step 1: Add Domain to Vercel

1. Go to your Vercel project: https://vercel.com/pcwmis-projects/styleinspo/settings/domains
2. Click **"Add Domain"** or **"Add"** button
3. Enter your custom domain (e.g., `styleinspo.com`)
4. Click **"Add"**

### Step 2: Configure DNS Records

Vercel will show you the DNS records you need to add. You'll typically need:

**Option A: Root Domain (e.g., `styleinspo.com`)**
- **Type**: `A` or `CNAME`
- **Name**: `@` or leave blank (depends on your DNS provider)
- **Value**: Vercel will provide this (usually a CNAME to `cname.vercel-dns.com`)

**Option B: Subdomain (e.g., `www.styleinspo.com`)**
- **Type**: `CNAME`
- **Name**: `www`
- **Value**: `cname.vercel-dns.com` (or what Vercel provides)

**Common DNS Providers:**
- **Cloudflare**: DNS → Records → Add record
- **Namecheap**: Advanced DNS → Add new record
- **GoDaddy**: DNS Management → Add
- **Google Domains**: DNS → Custom records

### Step 3: Wait for DNS Propagation

1. DNS changes can take a few minutes to 48 hours (usually 5-30 minutes)
2. Vercel will automatically detect when DNS is configured correctly
3. You'll see a green checkmark ✅ when the domain is ready

### Step 4: SSL Certificate Provisioning

1. Once DNS is configured, Vercel automatically provisions an SSL certificate
2. This usually takes 1-5 minutes
3. You'll see "Valid" status in the Domains settings

### Step 5: Test in Arc Mobile

1. Open Arc mobile browser
2. Navigate to your custom domain (e.g., `https://styleinspo.com`)
3. Should work without SSL errors! ✅

## Updating Your App Configuration

### Update Environment Variables (If Needed)

If your app references the domain in code, you may need to update:

```bash
# In Vercel project settings → Environment Variables
# Update any domain-specific variables if needed
```

### Update Backend CORS (If Applicable)

If your backend has CORS configured, add your custom domain:

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://styleinspo.vercel.app",  # Keep old domain for now
        "https://styleinspo.com",  # Add new custom domain
        "https://www.styleinspo.com",  # If using www subdomain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Update Frontend API URLs (If Hardcoded)

If you have any hardcoded URLs in your frontend, update them:

```typescript
// frontend code
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://styleinspo.com/api';
```

## Domain Options

### Option 1: Use Existing Domain
If you already own a domain:
- Add it directly to Vercel
- Configure DNS as shown above

### Option 2: Buy New Domain
Popular domain registrars:
- **Namecheap**: https://www.namecheap.com
- **Cloudflare Registrar**: https://www.cloudflare.com/products/registrar
- **Google Domains**: https://domains.google
- **GoDaddy**: https://www.godaddy.com

**Recommended**: Cloudflare Registrar (cheap, no markup, includes privacy)

### Option 3: Use Subdomain
If you have a main domain, you can use a subdomain:
- `styleinspo.yourdomain.com`
- `app.yourdomain.com`
- `styling.yourdomain.com`

## Cost

- **Vercel**: Free (custom domains included in Hobby plan)
- **Domain**: ~$10-15/year (varies by TLD)
- **SSL Certificate**: Free (automatically provisioned by Vercel)

## Verification Checklist

After setup, verify:
- [ ] Domain added to Vercel project
- [ ] DNS records configured correctly
- [ ] DNS propagated (Vercel shows green checkmark)
- [ ] SSL certificate provisioned (shows "Valid" in Vercel)
- [ ] Site loads at custom domain in Safari/Chrome
- [ ] **Site loads at custom domain in Arc mobile** ✅ (this is the test!)
- [ ] No SSL errors in Arc mobile browser

## Troubleshooting

### DNS Not Propagating
- Wait 24-48 hours (rare, usually 5-30 minutes)
- Check DNS propagation: https://www.whatsmydns.net
- Verify DNS records are correct in your DNS provider

### SSL Certificate Not Provisioning
- Ensure DNS is fully propagated
- Check Vercel logs for certificate errors
- Try removing and re-adding the domain

### Still Getting SSL Error in Arc
- Wait a few minutes after SSL certificate is provisioned
- Clear Arc browser cache
- Try in incognito/private mode
- Verify SSL certificate is valid: https://www.ssllabs.com/ssltest/

## Next Steps

1. **Choose your domain** (buy new or use existing)
2. **Add to Vercel** (Settings → Domains)
3. **Configure DNS** (as instructed by Vercel)
4. **Wait for SSL** (automatic, usually 1-5 minutes)
5. **Test in Arc mobile** (should work!)

## References

- [Vercel Custom Domains Documentation](https://vercel.com/docs/domains)
- [Vercel DNS Configuration](https://vercel.com/docs/domains/configure-dns)
- [Vercel Support Response](https://vercel.com/support) (confirmed custom domain solution)


