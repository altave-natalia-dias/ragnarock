# TK-003: Admin-Role JWT Tokens Embedded in Public URLs — pay.tokopediax.com (Wayback Machine)

**Program:** TikTok HackerOne  
**Asset:** `pay.tokopediax.com` [Critical, Eligible]  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)  
**CWE:** CWE-598 — Information Exposure Through Query Strings in GET Request  
**CWE:** CWE-200 — Exposure of Sensitive Information  
**Discovered:** 2026-06-29  
**Status:** Ready to submit

---

## Summary

TikTok's payment platform (`pay.tokopediax.com`) was found to embed merchant admin-role JWT tokens directly in URL query parameters. These URLs were indexed by the Wayback Machine (web.archive.org) and are publicly accessible. The exposed JWTs contain:

- **Merchant ID** (`mainact`, `subact`)
- **User ID** (`uid`) 
- **ADMIN role** (`"ro": "ADMIN"`)
- **Account scope** (`"sc": "free"`)
- **Payment order IDs** embedded in the same URL

While the specific tokens are expired (4-day validity), the systemic practice of embedding admin JWTs in URLs creates ongoing security risk:
1. New tokens with the same admin role are generated and placed in URLs for each new payment session
2. These URLs are accessible from browser history, server access logs, Referer headers, CDN logs, and web crawlers

---

## Evidence

### Wayback Machine URL (archived)

Source: `https://web.archive.org/cdx/search/cdx?url=pay.tokopediax.com/*&output=text`

**URL 1 (June 2025):**
```
https://pay.tokopediax.com/pipo_fe/ecom/payout/init?
  country_code=ID&
  fp_scene_tn=AkEAAg56DzjWZksvnutPTc996eVMK&
  fp_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdGFuZGFyZF9jbGFpbXMiOnsiZXhwIjoxNzUxMDg3MDEyLCJqdGkiOiJBa0FBQXAyRFpUeDdYa3B4dlpmZFJYSktVOTljSyIsImlhdCI6MTc1MDc0MTQxMn0sImtpbmYiOnsia3RwIjoiVENDX0ZJWEVEX1NJR05fS0VZIn0sIm1haW5hY3QiOiIxMTIwMjMxMURZemZzMiIsInN1YmFjdCI6IkFTa0FBTW9rUzJqeWJFV0hpZVdBYUxzYm5vNEsiLCJ1aWQiOiJBU2tBQU1va1MyanliRVdIaWVXQWFMc2JubzRLIiwicm8iOiJBRE1JTiIsInNjIjoiZnJlZSJ9.GbFRCGw-SVBFbu6w4gNE0XOZsrW697rs4EnS8XK5Hoo&
  merchant_id=11202311DYzfs2&
  order_id=202506240301500010002AzaP8HzpGsY&
  target_page=free&
  withdraw_limit_number=1031764&
  aid=4068&
  language=id-ID
```

**URL 2 (September 2025):**
```
https://pay.tokopediax.com/pipo_fe/ecom/payout/init?
  country_code=ID&
  fp_scene_tn=AkEAAgMLQ5F5CkQJgz29SP7HzYgkK&
  fp_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdGFuZGFyZF9jbGFpbXMiOnsiZXhwIjoxNzU3MjIyMjkxLCJqdGkiOiJBa0FBQW1yVnowdUU1MHRNakdraWRLYVFPSFVLIiwiaWF0IjoxNzU2ODc2NjkxfSwia2luZiI6eyJrdHAiOiJUQ0NfRklYRURfU0lHTl9LRVkifSwibWFpbmFjdCI6IjExMjAyMzExRFl6ZnMyIiwic3ViYWN0IjoiQVNrQUFNb2tTMmp5YkVXSGllV0FhTHNibm80SyIsInVpZCI6IkFTa0FBTW9rUzJqeWJFV0hpZVdBYUxzYm5vNEsiLCJybyI6IkFETUlOIiwic2MiOiJmcmVlIn0.wPNIcakZYVzBYCHMzxL4s2G8QgyJ1TVdKEAshz-qjTM&
  merchant_id=11202311DYzfs2&
  order_id=202509030301500010002AzgQ45xr7AU&
  target_page=free&
  withdraw_limit_number=440168&
  aid=4068&
  language=id-ID
```

### Decoded JWT Payloads

**Token 1 (expired June 28, 2025):**
```json
{
  "standard_claims": {
    "exp": 1751087012,
    "jti": "AkAAAp2DZTx7XkpxvZfdRXJKU99cK",
    "iat": 1750741412
  },
  "kinf": {
    "ktp": "TCC_FIXED_SIGN_KEY"
  },
  "mainact": "11202311DYzfs2",
  "subact": "ASkAAMokS2jybEWHieWAaLsbno4K",
  "uid": "ASkAAMokS2jybEWHieWAaLsbno4K",
  "ro": "ADMIN",
  "sc": "free"
}
Issued: 2025-06-24T05:03:32Z | Expires: 2025-06-28T05:03:32Z
```

**Token 2 (expired September 7, 2025):**
```json
{
  "standard_claims": {
    "exp": 1757222291,
    "jti": "AkAAAmrVz0uE50tMjGkidKaQOHUK",
    "iat": 1756876691
  },
  "kinf": {
    "ktp": "TCC_FIXED_SIGN_KEY"
  },
  "mainact": "11202311DYzfs2",
  "subact": "ASkAAMokS2jybEWHieWAaLsbno4K",
  "uid": "ASkAAMokS2jybEWHieWAaLsbno4K",
  "ro": "ADMIN",
  "sc": "free"
}
Issued: 2025-09-03T05:18:11Z | Expires: 2025-09-07T05:18:11Z
```

---

## Technical Analysis

### Why Admin Tokens in URLs Are Problematic

The `fp_token` parameter is a signed JWT Bearer token that grants ADMIN-level access to the payout checkout for merchant `11202311DYzfs2`. By placing this token in a URL query parameter:

1. **Browser history**: The URL (including the admin token) is stored in the merchant's browser history
2. **Server access logs**: Web servers, CDNs (Akamai, Cloudflare), and load balancers log full request URLs including query parameters
3. **Referer header leakage**: If the merchant navigates from this URL to another site, the Referer header exposes the full URL with the admin token
4. **Web crawler indexing**: As confirmed by the Wayback Machine, these URLs were crawled and indexed publicly
5. **Shoulder surfing**: The admin token is visible in the browser address bar

### Verified API Endpoints Using This Token Pattern

From Wayback Machine (all using `fp_scene_tn` derived from `fp_token`):

```
GET /pipo_fe/api_ecom/payout/checkout_ui/get_config?fp_scene_tn=...
GET /pipo_fe/api_ecom/payout/proxy/cashier/v1/order/query?fp_scene_tn=...
GET /pipo_fe/api_ecom/payout/proxy/cashier/v1/merchant/preference?fp_scene_tn=...
GET /pipo_fe/api_ecom/payout/proxy/payout/v1/cashier/get_pi_basic_info?fp_scene_tn=...
```

These endpoints query order data, merchant preferences, and payment info. A valid (non-expired) `fp_token` with ADMIN role in these URLs would expose:
- Order details
- Withdrawal limits (`withdraw_limit_number=1031764`)
- Payment configuration

### Systemic Risk

The `TCC_FIXED_SIGN_KEY` key type suggests this is a "fixed" signing key (not rotated per request). If an attacker captures a valid `fp_token` before it expires (4-day window):
1. They can query all merchant payment data
2. They have ADMIN role access to the merchant's payment account
3. They could potentially initiate or modify withdrawal operations

---

## Impact

| Impact | Description | Severity |
|--------|-------------|---------|
| Admin credentials in Wayback | Publicly searchable admin tokens | Medium |
| Server/CDN log exposure | Admin tokens in full-URL logs | Medium |
| 4-day exploitation window | Token valid for 4 days after generation | Medium-High |
| Merchant ID exposure | `11202311DYzfs2` and UIDs publicly exposed | Low |
| Order ID exposure | Payment order IDs publicly searchable | Low |

---

## Proof of Concept

### Step 1: Retrieve the archived URLs from Wayback Machine

```bash
curl -s "https://web.archive.org/cdx/search/cdx?url=pay.tokopediax.com/*&output=text&fl=original&collapse=urlkey" | \
  grep "fp_token=" | head -10
```

### Step 2: Decode the JWT to reveal admin credentials

```bash
# Extract and decode the fp_token payload
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdGFuZGFyZF9jbGFpbXMiOnsiZXhwIjoxNzUxMDg3MDEyLCJqdGkiOiJBa0FBQXAyRFpUeDdYa3B4dlpmZFJYSktVOTljSyIsImlhdCI6MTc1MDc0MTQxMn0sImtpbmYiOnsia3RwIjoiVENDX0ZJWEVEX1NJR05fS0VZIn0sIm1haW5hY3QiOiIxMTIwMjMxMURZemZzMiIsInN1YmFjdCI6IkFTa0FBTW9rUzJqeWJFV0hpZVdBYUxzYm5vNEsiLCJ1aWQiOiJBU2tBQU1va1MyanliRVdIaWVXQWFMc2JubzRLIiwicm8iOiJBRE1JTiIsInNjIjoiZnJlZSJ9.GbFRCGw-SVBFbu6w4gNE0XOZsrW697rs4EnS8XK5Hoo"

echo $TOKEN | cut -d. -f2 | python3 -c "
import sys, base64, json
p = sys.stdin.read().strip()
padded = p + '=' * (4 - len(p) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(padded)), indent=2))
"
# Output: {..., "ro": "ADMIN", "mainact": "11202311DYzfs2", ...}
```

---

## Remediation

1. **Move `fp_token` from URL query parameter to POST body or HTTP header**: Tokens should never be placed in URL parameters where they appear in logs, browser history, and referrer headers.

2. **Implement Wayback Machine opt-out**: Add `X-Robots-Tag: noarchive` or use `robots.txt` to prevent public archiving of payment URLs. Add META noindex to payment pages.

3. **Implement `Cache-Control: no-store` headers** on all payment pages to prevent caching of sensitive tokens.

4. **Rotate signing keys more frequently**: The `TCC_FIXED_SIGN_KEY` suggests a fixed key. Consider request-specific signing to limit impact of key exposure.

5. **Monitor for public exposure**: Set up alerts for Wayback Machine indexing of payment URLs containing JWTs.

---

## References

- Wayback Machine source: `web.archive.org/cdx/search/cdx?url=pay.tokopediax.com/*`
- OWASP: [Don't put sensitive data in URL parameters](https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_url)
- CWE-598: Information Exposure Through Query Strings in GET Request
- pay.tokopediax.com is in TikTok HackerOne scope (Critical, Eligible, 5 prior reports)
