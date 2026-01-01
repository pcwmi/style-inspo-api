# Vercel Support Message - Arc Mobile SSL Error

## Message to Send to Vercel Support

---

**Subject:** SSL Error in Arc Mobile Browser - Known Issue with `.vercel.app` Domains

**Product:** Vercel Platform  
**Account:** pcwmi's projects (Hobby plan)  
**Project:** styleinspo  
**Domain:** `styleinspo.vercel.app`

---

### Issue Description

I'm experiencing an SSL error when accessing my Vercel-deployed site (`styleinspo.vercel.app`) from the Arc mobile browser on iOS. The error message is: **"An SSL error has occurred and a secure connection to the server cannot be made."**

However, the site works perfectly in:
- ✅ Safari mobile (same device)
- ✅ Chrome mobile (same device)
- ✅ All desktop browsers
- ✅ All other mobile browsers tested

This indicates the issue is **Arc browser-specific**, not a problem with my SSL configuration.

### Technical Verification

I've verified my SSL configuration is correct:

1. **SSL Labs Test**: A+ rating on both servers
   - Server 1: `216.198.79.195` - Grade: A+
   - Server 2: `64.29.17.195` - Grade: A+
   - Test URL: https://www.ssllabs.com/ssltest/analyze.html?d=styleinspo.vercel.app

2. **Certificate Chain**: Complete and valid
   - Verified via `openssl s_client` - all intermediate certificates present
   - Certificate chain: `*.vercel.app` → `WR1` → `GTS Root R1` → `GlobalSign Root CA`
   - OCSP stapling: Enabled and working
   - TLS version: 1.3

3. **Vercel SSL Settings**: Verified in dashboard
   - Domain properly configured
   - No SSL warnings or errors
   - Certificate valid until March 26, 2026

### Troubleshooting Steps Completed

I've tried the following without success:

1. ✅ **Redeployed** the project multiple times (to refresh certificate chain)
2. ✅ **Verified SSL settings** in Vercel dashboard
3. ✅ **Tested SSL certificate** via SSL Labs (A+ rating)
4. ✅ **Updated Arc browser** to latest version
5. ✅ **Tested on different networks** (WiFi and cellular data)
6. ✅ **Cleared Arc browser cache** and data
7. ✅ **Verified it works in Safari** on the same device (confirms Arc-specific issue)

### Known Issue Reference

I found a Vercel Community discussion about this exact issue:
- **Thread**: https://community.vercel.com/t/sites-deployed-to-vercel-app-not-reachable-via-arc-browser-latest-on-ios-26-2-iphone-15/30524
- This appears to be a **known compatibility issue** between Arc mobile browser (iOS) and Vercel's `.vercel.app` domains

### Technical Analysis

Based on my investigation, Arc mobile browser has stricter SSL validation than other browsers:

1. **Certificate Chain Validation**: Arc may not automatically fetch missing intermediate certificates via AIA (Authority Information Access) URLs, while Safari/Chrome do
2. **OCSP Validation**: Arc may validate OCSP responses more strictly
3. **iOS App Transport Security**: Arc may enforce ATS requirements more aggressively than Safari

However, my certificate chain is complete, OCSP stapling is enabled, and SSL Labs confirms everything is configured correctly. The issue appears to be Arc's validation of Vercel's certificate chain specifically.

### Impact

- **User Impact**: Users on Arc mobile browser cannot access the site
- **Workaround**: Users can use Safari or Chrome mobile browsers
- **Severity**: Medium - affects a subset of users (Arc mobile users)

### Request

Could you please:

1. **Confirm if this is a known issue** with Arc browser and `.vercel.app` domains
2. **Check if there's a Vercel-side fix** (e.g., certificate chain configuration, edge server SSL settings)
3. **Provide guidance** on whether using a custom domain would resolve this
4. **Update the community thread** if there's a resolution or workaround

### Additional Information

- **Device**: iPhone (iOS version: [YOUR iOS VERSION])
- **Arc Browser Version**: [YOUR ARC VERSION]
- **Network Tested**: Both WiFi and cellular data (same error on both)
- **Other Browsers Tested**: Safari ✅, Chrome ✅ (both work on same device)

### Certificate Details (for reference)

```
Certificate Chain:
- Subject: CN=*.vercel.app
- Issuer: C=US, O=Google Trust Services, CN=WR1
- Intermediate: CN=WR1 (Google Trust Services)
- Root: CN=GTS Root R1 (Google Trust Services LLC)
- Root CA: CN=GlobalSign Root CA

OCSP Stapling: Enabled
TLS Version: 1.3
Cipher: AEAD-CHACHA20-POLY1305-SHA256
```

Thank you for your assistance!

---

## Alternative Shorter Version (If Character Limit)

**Subject:** Arc Mobile SSL Error - Known Issue with `.vercel.app`

**Issue:** Arc mobile browser shows SSL error on `styleinspo.vercel.app`, but works in Safari/Chrome on same device.

**Verification:**
- SSL Labs: A+ rating
- Certificate chain: Complete
- Works in: Safari, Chrome, all desktop browsers
- Fails in: Arc mobile only

**Troubleshooting:**
- Redeployed multiple times
- Verified SSL settings
- Tested on different networks
- Updated Arc browser
- Cleared cache

**Known Issue:** https://community.vercel.com/t/sites-deployed-to-vercel-app-not-reachable-via-arc-browser-latest-on-ios-26-2-iphone-15/30524

**Request:** Is there a Vercel-side fix or should I use a custom domain?


