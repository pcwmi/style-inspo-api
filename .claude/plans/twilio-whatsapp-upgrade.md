# Twilio WhatsApp Sandbox to Production Upgrade Plan

**Created**: 2026-02-10
**Status**: Ready to Execute
**Estimated Total Time**: 1-3 weeks (mostly waiting for Meta verification)

## Current Setup

Your current implementation uses the Twilio WhatsApp Sandbox:
- Sandbox number: `+14155238886` (hardcoded in `backend/services/twilio_service.py`)
- Limitation: 50 messages/day for sandbox
- Requires users to send "join" code to activate (friction)

## Overview: What Changes

| Aspect | Sandbox | Production |
|--------|---------|------------|
| Phone number | Shared sandbox number | Your own dedicated number |
| Daily limit | 50 messages | 250 (unverified) to unlimited (verified) |
| User activation | "join <code>" required | Users can message directly |
| Templates | Not required | Required for outbound notifications |
| Meta verification | Not required | Required for higher limits |

## Prerequisites Checklist

Before starting, gather these items:

- [ ] **Twilio account upgraded** (not free trial) - required for WhatsApp production
- [ ] **Phone number** - can use existing Twilio number OR buy new one
- [ ] **Meta/Facebook account** - personal account to log in
- [ ] **Business documents** (for Meta verification) - see Document Requirements below
- [ ] **Business website** - `styleinspo.vercel.app` should work

### Document Requirements for Meta Business Verification

Meta requires 2-3 documents that verify your legal business name AND address. All documents must match exactly (name, address spelling).

**Acceptable documents (choose 2-3):**
- Business license or registration certificate
- Articles of incorporation
- Tax registration document (e.g., IRS EIN letter, Schedule C)
- Utility bill in business name (phone, electric, internet)
- Bank statement showing business name and address
- DBA/Doing Business As certificate

**For Solo Developers / Sole Proprietors:**
- If operating under your personal name, use documents that show your name and address
- Schedule C (if you file US taxes as self-employed)
- State business registration
- Bank statements from a business account OR personal account if that's what you use

## Step-by-Step Execution Plan

---

### Phase 1: Twilio Console Setup (15-30 minutes)

**Who does it:** You (manual)
**Dependency:** None

#### Step 1.1: Verify Twilio Account is Upgraded

1. Go to [Twilio Console](https://console.twilio.com/)
2. Look at the top banner - if it says "Upgrade", you need to add billing
3. If needed: Go to **Admin > Account Billing > Upgrade Account**
4. Add payment method

**Verification:** No "Upgrade" banner visible

#### Step 1.2: Get or Confirm Phone Number

1. Go to **Phone Numbers > Manage > Active Numbers**
2. You likely already have a number (`TWILIO_PHONE_NUMBER` in your `.env`)
3. Confirm it's an SMS-capable number in the US

**Note:** WhatsApp can use your existing Twilio number. You don't need a separate number.

**Verification:** You have at least one active Twilio phone number

---

### Phase 2: WhatsApp Sender Registration (30-60 minutes)

**Who does it:** You (manual, with Meta login)
**Dependency:** Phase 1 complete

#### Step 2.1: Create WhatsApp Sender

1. Go to [Twilio Console > Messaging > Senders > WhatsApp Senders](https://console.twilio.com/us1/develop/sms/senders/whatsapp-senders)
2. Click **"Create new sender"**
3. Select your Twilio phone number
4. Click **Continue**

#### Step 2.2: Connect Meta Business Account

1. Click **"Continue with Facebook"**
2. Log in with your personal Facebook account
3. Grant Twilio permissions when prompted

**Important:** Keep both browser windows open (Twilio Console AND the Facebook popup)

#### Step 2.3: Set Up Meta Business Portfolio

In the Facebook popup:

1. **Create new** Meta Business Portfolio (recommended) OR select existing
   - Name it something like "Style Inspo" or your business name
   - Fill in business details (address, phone, website)
2. Click **Continue**

#### Step 2.4: Create WhatsApp Business Account (WABA)

1. **Create new** WABA (don't select one created outside Twilio)
2. Name it (e.g., "Style Inspo")
3. Click **Continue**

#### Step 2.5: Create Business Profile

Fill in these customer-facing details:

| Field | Value | Required |
|-------|-------|----------|
| Display name | "Style Inspo" (or your brand) | Yes |
| Category | "Shopping & Retail" or "Fashion" | Yes |
| Description | "Your AI styling assistant" | No |
| Website | styleinspo.vercel.app | No |

**Note:** Display name must follow [Meta's naming guidelines](https://www.facebook.com/business/help/338047025165344)

#### Step 2.6: Verify Phone Number

1. Choose verification method:
   - **SMS** (recommended if your Twilio number can receive SMS)
   - **Voice call** (if toll-free or SMS not available)
2. Enter the OTP code you receive
3. Click **Verify**

**For SMS:** The code appears in your Twilio Console logs or your configured webhook

#### Step 2.7: Complete Registration

1. Review Twilio's access permissions in the popup
2. Click **Approve**
3. The popup closes automatically
4. Wait a few minutes for the Console to refresh

**Verification:** Your WhatsApp sender appears in the Console with status "Ready" or "Connected"

---

### Phase 3: Update Your Code (30 minutes)

**Who does it:** You or Claude
**Dependency:** Phase 2 complete

#### Step 3.1: Update Environment Variables

Add to your `.env` file:

```bash
# Your WhatsApp-enabled Twilio number (same as TWILIO_PHONE_NUMBER typically)
TWILIO_WHATSAPP_NUMBER=+1XXXXXXXXXX
```

#### Step 3.2: Update TwilioService

Edit `/Users/peichin/Projects/style-inspo-api/backend/services/twilio_service.py`:

**Current code (sandbox):**
```python
# WhatsApp sandbox number (shared by all Twilio sandbox users)
WHATSAPP_SANDBOX_NUMBER = "+14155238886"

# In send_sms/send_mms:
if is_whatsapp:
    from_number = f"whatsapp:{self.WHATSAPP_SANDBOX_NUMBER}"
```

**New code (production):**
```python
def __init__(self):
    self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
    self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", self.from_number)
    # ... rest of init

# In send_sms/send_mms:
if is_whatsapp:
    from_number = f"whatsapp:{self.whatsapp_number}"
```

#### Step 3.3: Update Webhook URL in Twilio Console

1. Go to **Messaging > Senders > WhatsApp Senders**
2. Click on your sender
3. Click **Edit sender**
4. Set webhook URL: `https://your-api-domain.com/api/sms/incoming`
5. Set HTTP method: POST

**Verification:** Send a WhatsApp message to your new number and verify webhook fires

---

### Phase 4: Meta Business Verification (1-14 days)

**Who does it:** You (manual)
**Dependency:** Phase 2 complete (can run in parallel with Phase 3)

**Why this matters:**
- Unverified: 250 unique conversations/day
- Verified: 1,000+ and scales up automatically

#### Step 4.1: Start Verification

1. Go to [Meta Business Settings > Security Center](https://business.facebook.com/settings/security)
2. Find your Business Portfolio
3. Click **Start Verification**

#### Step 4.2: Enter Business Information

Fill in accurately (must match documents):
- Legal business name
- Business address
- Business phone number
- Business website

#### Step 4.3: Upload Documents

Upload 2-3 documents from the list above.

**Tips:**
- PDF format preferred
- Clear, readable scans
- All names and addresses must match exactly
- If sole proprietor, your personal name is fine

#### Step 4.4: Wait for Review

- Typical timeline: 2-14 business days
- You'll receive email and in-app notification
- May be asked for additional documents

**If rejected:** Review the rejection reason, correct documents, and resubmit

---

### Phase 5: Create Message Templates (Optional but Recommended)

**Who does it:** You or Claude
**Dependency:** Phase 2 complete

Templates are required for:
- First message to users (before they message you)
- Messages outside the 24-hour customer service window

For Style Inspo, you mainly respond to user messages (within 24hr window), so templates are optional initially.

#### Step 5.1: Create Templates in Twilio Console

1. Go to **Messaging > Content Template Builder**
2. Click **Create new template**
3. Fill in:
   - Name: e.g., "outfit_ready"
   - Category: "Utility" (cheaper than Marketing)
   - Language: English
   - Content: Your message with variables

Example template:
```
Hey {{1}}! Your outfit is ready:

{{2}}

Reply with any questions!
```

#### Step 5.2: Submit for Approval

- Templates are auto-reviewed (usually minutes)
- May take up to 24 hours for complex templates

---

## Post-Upgrade Verification

### Test Checklist

- [ ] Send WhatsApp message TO your production number (not sandbox)
- [ ] Verify webhook receives the message (check logs)
- [ ] Verify response is sent successfully
- [ ] Verify MMS/images work
- [ ] Test with a second phone number (someone not you)

### Monitor Messaging Limits

1. Go to [Meta WhatsApp Manager](https://business.facebook.com/wa/manage/home/)
2. Check "Phone numbers" for your current tier
3. Monitor quality rating (Medium/High needed for tier upgrades)

---

## Cost Summary

| Item | Cost |
|------|------|
| Twilio per-message fee | $0.005 per message (in or out) |
| Meta utility template | Free within 24hr window, $0.0034 outside |
| Meta authentication template | $0.0034 per message |
| Meta marketing template | Varies by country (~$0.01-0.06) |
| Setup/monthly | $0 (pay-as-you-go) |

**Estimated monthly cost for Style Inspo:**
- 100 conversations/month: ~$1-2
- 1,000 conversations/month: ~$10-20

---

## Troubleshooting

### Error 63020: "Channel could not find From address"
- You haven't accepted Twilio's invitation in Meta Business Manager
- Go to Meta Business Settings > Requests and accept pending requests

### Error 63110: "Phone number already registered"
- The number is already on WhatsApp (personal or another business)
- Solution: Delete WhatsApp account from that number first, then re-register via Twilio

### Messages not sending
1. Check Twilio Console logs for errors
2. Verify webhook URL is correct
3. Verify phone number format is `whatsapp:+1XXXXXXXXXX`

### Meta verification rejected
- Common reasons: name mismatch, unclear documents, address mismatch
- Fix the issue and resubmit with corrected documents

---

## Quick Reference Links

- [Twilio WhatsApp Console](https://console.twilio.com/us1/develop/sms/senders/whatsapp-senders)
- [Twilio Self-Signup Docs](https://www.twilio.com/docs/whatsapp/self-sign-up)
- [Meta Business Settings](https://business.facebook.com/settings/)
- [Meta WhatsApp Manager](https://business.facebook.com/wa/manage/home/)
- [Meta Display Name Guidelines](https://www.facebook.com/business/help/338047025165344)
- [Twilio WhatsApp Pricing](https://www.twilio.com/en-us/whatsapp/pricing)
- [WhatsApp Business Policy](https://www.whatsapp.com/legal/business-policy/)

---

## Summary Timeline

| Phase | Time | Blocking? |
|-------|------|-----------|
| Phase 1: Twilio Setup | 15-30 min | No |
| Phase 2: WhatsApp Registration | 30-60 min | No |
| Phase 3: Code Updates | 30 min | No |
| Phase 4: Meta Verification | 2-14 days | Partially (needed for >250/day) |
| Phase 5: Templates | 30 min + approval | No |

**Total hands-on time:** ~2-3 hours
**Total elapsed time:** 1-3 weeks (waiting for Meta verification)

**You can start messaging immediately after Phase 3**, with a 250/day limit. Meta verification (Phase 4) increases this limit and runs in parallel.
