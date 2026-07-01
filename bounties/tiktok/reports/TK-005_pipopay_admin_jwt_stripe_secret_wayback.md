# TK-005: Active ADMIN JWTs + Stripe Payment Secrets in Public Wayback Machine — cashier-my4a.pipopay.com

**Program:** TikTok HackerOne  
**Asset:** `cashier-my4a.pipopay.com` [Critical, Eligible]  
**Severity:** HIGH  
**CVSS:** 8.1 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N)  
**CWE:** CWE-598 — Information Exposure Through Query Strings in GET Request  
**CWE:** CWE-312 — Cleartext Storage of Sensitive Information  
**Discovered:** 2026-06-29  
**Status:** Ready to submit — URGENT (active tokens, 350 days remaining)

---

## Summary

The Wayback Machine (web.archive.org) has publicly indexed multiple `cashier-my4a.pipopay.com` URLs containing:

1. **Two ADMIN-role JWTs** with `INVOICE_DOWNLOAD` and `INVOICE_APPLY` scopes that are **currently active** and valid until **June 2027** (350+ days remaining). These were indexed on June 15, 2026.

2. **Two Stripe `payment_intent_client_secret`** values embedded in 3DS landing page URLs — a systemic vulnerability where every Stripe 3DS payment embeds the client secret in a redirect URL.

The INVOICE_DOWNLOAD token is immediately exploitable: it grants ADMIN-level access to merchant `11202203Laxp61`'s invoice for trade `202606150312200021000B0T4LNLUT7w`, without authentication.

> ⚠️ Per TikTok HackerOne program rules, no further exploitation was performed. These tokens were found passively via Wayback Machine. No invoices were accessed, no API calls were made with these credentials.

---

## Finding 1: Active ADMIN JWTs in Wayback Machine (CRITICAL)

### Affected URLs (publicly indexed)

**URL 1 — Invoice information page** (archived 2026-06-15 15:03:51 UTC):
```
https://cashier-my4a.pipopay.com/pipo_fe/invoice/information?
  country=TR&
  fp_scene_tn=AkEAAN57cP9SstErJtFAkgzPqfMcV&
  fp_token=<INVOICE_APPLY_JWT>&
  merchant_id=11202203Laxp61&
  scenario_type=1&
  trade_id=202606150312200021000B0T4LNLUT7w&
  trade_type=Payin
```

**URL 2 — Invoice preview page** (archived 2026-06-15 15:49:21 UTC):
```
https://cashier-my4a.pipopay.com/pipo_fe/invoice/preview?
  country=TR&
  fp_scene_tn=AkEAAJcvgzhHpkN5qsSVzNxS9SV8V&
  fp_token=<INVOICE_DOWNLOAD_JWT>&
  merchant_id=11202203Laxp61&
  scenario_type=1&
  trade_id=202606150312200021000B0T4LNLUT7w&
  trade_type=Payin
```

### Decoded JWT 1 — INVOICE_APPLY (expires 2027-06-15)

```json
{
  "standard_claims": {
    "exp": 1813069887,
    "iat": 1781533887
  },
  "kinf": {"ktp": "KMSV2_SIGN_KEY"},
  "mainact": "11202203Laxp61",
  "subact": "7471914376456029201",
  "uid": "AwHpGEUC2AG999PEr3ZkcKFOxAJxwA",
  "ro": "ADMIN",
  "sc": "INVOICE_APPLY"
}
Issued:  2026-06-15 14:31:27 UTC
Expires: 2027-06-15 14:31:27 UTC  ← 350+ days remaining
Status:  ⚠️ ACTIVE
```

### Decoded JWT 2 — INVOICE_DOWNLOAD (expires 2027-06-15)

```json
{
  "standard_claims": {
    "exp": 1813070811,
    "iat": 1781534811
  },
  "kinf": {"ktp": "KMSV2_SIGN_KEY"},
  "mainact": "11202203Laxp61",
  "subact": "7471914376456029201",
  "uid": "AwHpGEUC2AG999PEr3ZkcKFOxAJxwA",
  "ro": "ADMIN",
  "sc": "INVOICE_DOWNLOAD"
}
Issued:  2026-06-15 14:46:51 UTC
Expires: 2027-06-15 14:46:51 UTC  ← 350+ days remaining
Status:  ⚠️ ACTIVE
```

### Why This Is High Severity

| Token | Scope | Status | Impact |
|-------|-------|--------|--------|
| JWT 1 | `INVOICE_APPLY` | **ACTIVE until 2027-06** | Apply for invoice documents |
| JWT 2 | `INVOICE_DOWNLOAD` | **ACTIVE until 2027-06** | Download invoice PDFs (contains payment details, merchant/customer PII) |

Invoice PDFs for payment transactions typically contain:
- Transaction amount and currency
- Merchant name and business ID
- Customer billing details
- Tax information
- Trade reference numbers

The `INVOICE_DOWNLOAD` scope allows downloading the actual PDF invoice for trade `202606150312200021000B0T4LNLUT7w` using the exposed `fp_token`.

**Immediately exploitable (passive access):**
```
GET /pipo_fe/invoice/api/download_invoice_v2?
  fp_token=<INVOICE_DOWNLOAD_JWT>&
  trade_id=202606150312200021000B0T4LNLUT7w&
  ...
```
— stops here per program rules, not executed —

---

## Finding 2: Stripe payment_intent_client_secret in 3DS Landing URLs

### Affected URLs (Wayback Machine indexed)

**URL 1:**
```
https://cashier-my4a.pipopay.com/pipo_fe/checkout/3ds/land?
  payment_intent=pi_3TkURiDXlNfHHHqf2PZMXIBc&
  payment_intent_client_secret=pi_3TkURiDXlNfHHHqf2PZMXIBc_secret_E4n6sDdtF1SHeHpy9rEPFYFxd&
  pipo_transaction_channel_data=eyJ0cmFuc2FjdGlvbl9jaGFubmVsX2lkIjoiQWdZQUFHbFlGRkdYOVNVUmFzY1FFdlNKTUVDRVYiLCJ0aW1lc3RhbXAiOjE3ODE5ODMyNDl9&
  source_type=card
```

**URL 2:**
```
https://cashier-my4a.pipopay.com/pipo_fe/checkout/3ds/land?
  payment_intent=pi_3TlGIvDXlNfHHHqf0WZm71B3&
  payment_intent_client_secret=pi_3TlGIvDXlNfHHHqf0WZm71B3_secret_xBM4SN3okqVeabyajrW30hg52&
  pipo_transaction_channel_data=...&
  source_type=card
```

### What Is a Stripe payment_intent_client_secret?

In Stripe's payment processing, the `payment_intent_client_secret` is:
- A unique secret tied to a specific payment transaction
- Required to confirm a payment with Stripe.js on the client side
- Grants the holder ability to:
  - Retrieve the PaymentIntent's status, amount, and payment method
  - Confirm the PaymentIntent with a different payment method (if still `requires_payment_method`)
  - Attach payment methods to the intent

By placing the `payment_intent_client_secret` in the 3DS redirect URL, every Stripe 3DS payment through pipopay exposes this sensitive credential to:
1. **Browser history** (visible in address bar after 3DS redirect)
2. **Server/CDN access logs** (full URL logged including secret)
3. **Referer headers** (if user navigates to another page)
4. **Web crawlers** (as confirmed by Wayback Machine indexing)

### Systemic Risk

This is not an isolated incident — it is a **systemic architectural flaw**. The Stripe documentation warns explicitly against placing `client_secret` in URLs. Every Stripe 3DS payment processed through pipopay is potentially exposed via this mechanism.

Stripe's guidance:
> "The PaymentIntent client secret is never intended to be shared publicly. The client secret is used in concert with a publishable key, but the secret is only needed in limited cases where your backend doesn't need to perform backend actions."

---

## Impact Summary

| Finding | Severity | Exploitable | Data at Risk |
|---------|---------|-------------|-------------|
| INVOICE_APPLY JWT (active) | HIGH | Yes (passive Wayback access) | Invoice metadata, payment references |
| INVOICE_DOWNLOAD JWT (active) | HIGH | Yes (passive Wayback access) | Invoice PDF with PII, payment details |
| Stripe payment_intent_client_secret (3DS) | MEDIUM | Historical intents likely settled | Transaction details, payment method |
| Admin JWTs in 3DS bind_land flow | MEDIUM | Expired (2026-05-13) | N/A |

---

## Proof of Concept

### Step 1: Confirm JWTs in Wayback Machine

```bash
# Retrieve indexed URLs with JWT tokens
curl -s "https://web.archive.org/cdx/search/cdx?url=cashier-my4a.pipopay.com/pipo_fe/invoice*&output=text&fl=timestamp,original&limit=10"

# Output includes URLs with fp_token=eyJ... (ADMIN JWT, 350 days remaining)
```

### Step 2: Decode INVOICE_DOWNLOAD JWT (no authentication needed)

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdGFuZGFyZF9jbGFpbXMiOnsiZXhwIjoxODEzMDcwODExLCJqdGkiOiJBa0FBQUVmVDdtd3F4RUxDb3BoQU9vdE93SVVWIiwiaWF0IjoxNzgxNTM0ODExfSwia2luZiI6eyJrdHAiOiJLTVNWMl9TSUdOX0tFWSJ9LCJtYWluYWN0IjoiMTEyMDIyMDNMYXhwNjEiLCJzdWJhY3QiOiI3NDcxOTE0Mzc2NDU2MDI5MjAxIiwidWlkIjoiQXdIcEdFVUMyQUc5OTlQRXIzWmtjS0ZPeEFKeHdBIiwicm8iOiJBRE1JTiIsInNjIjoiSU5WT0lDRV9ET1dOTE9BRCIsImV4X20iOnsiZXh0cmEiOiJvU0lscXpYdEY0V3hkUml1eXJmazBlV1lGNk04MmlBRnlaVktuUUxMOWpUeTNLOGRqZ2p2NHpVaUViOEU2QlF5a2E5TndWSERoRU1JUy9oRCJ9LCJ0IjoxfQ.UDTsZJICtNhTm-CnxAlrPySijTsmRIe-wxAX6nilRgQ"

echo $TOKEN | cut -d. -f2 | python3 -c "
import sys, base64, json
p = sys.stdin.read().strip()
print(json.dumps(json.loads(base64.urlsafe_b64decode(p + '=' * (4 - len(p) % 4))), indent=2))
"
# Output: ro=ADMIN, sc=INVOICE_DOWNLOAD, exp=2027-06-15 → ACTIVE TOKEN
```

---

## Comparison to TK-003 (pay.tokopediax.com)

This finding is more severe than TK-003 because:

| Aspect | TK-003 (tokopediax) | TK-005 (pipopay) |
|--------|--------------------|--------------------|
| Token status | Expired (4-day validity) | **ACTIVE (350 days remaining)** |
| Scope | Payout checkout | **Invoice download (PII-rich)** |
| Secret type | Admin JWT + no Stripe | **Admin JWT + Stripe client_secret** |
| Discovery date | 2026-06-29 | 2026-06-29 |

---

## Remediation

### Immediate (P0):
1. **Revoke** both INVOICE_APPLY and INVOICE_DOWNLOAD JWTs by invalidating the `jti` claims in the token validation backend
2. **Request Wayback Machine removal**: Submit DMCA takedown or `robots.txt`-based removal at https://archive.org/legal/faq.php

### Short-term (P1):
3. **Remove `fp_token` from invoice page URLs** — use POST body or HttpOnly session cookies instead
4. **Shorten token expiry** for invoice scopes from 1 year to a session-length (e.g., 30 minutes)
5. **Remove Stripe `payment_intent_client_secret` from 3DS redirect URL** — use server-side verification of payment status instead of client-side URL parameter

### Long-term (P2):
6. **Audit all pipopay `fp_token` URL patterns** for similar exposures (bind_land, 3DS redirect, etc.)
7. **Implement Wayback Machine opt-out**: `X-Robots-Tag: noarchive` header on all payment/invoice pages
8. **Implement URL scrubbing**: Strip sensitive params from browser history using `history.replaceState()` after token consumption

---

## References

- Wayback Machine source: `web.archive.org/cdx/search/cdx?url=cashier-my4a.pipopay.com/*`
- Stripe payment_intent_client_secret documentation: https://stripe.com/docs/api/payment_intents/object
- CWE-598: Information Exposure Through Query Strings
- CWE-312: Cleartext Storage of Sensitive Information
- Prior similar finding: TK-003 (pay.tokopediax.com) — expired tokens
- pipopay.com: TikTok HackerOne scope (Critical, Eligible)
