## [MEDIUM] — Unauthenticated OAuth Dynamic Client Registration on api.anthropic.com

**CVE:** N/A
**CVSS Score:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)
**CWE:** CWE-306 (Missing Authentication for Critical Function)
**Escopo Originário:** `api.anthropic.com` (Core — API)
**Affected Endpoint(s):** `POST https://api.anthropic.com/register`
**Discovered:** 2026-06-28
**Asset:** Domain — Core (api.anthropic.com)
**Program:** Anthropic HackerOne Bug Bounty

---

### Summary

The OAuth 2.0 Dynamic Client Registration endpoint (`POST /register`) on `api.anthropic.com` is completely unauthenticated, allowing anyone to register OAuth clients without any authentication, rate limiting, or approval process.

This is a **real finding** — confirmed through multiple independent tests — but with **limited practical impact** as currently demonstrated (see detailed analysis below). The registration is functional and connected to the authorization flow, but the `/authorize` endpoint enforces a server-side redirect_uri whitelist that does not automatically include dynamically registered URIs.

---

### Confirmed Facts (Validated via Tests)

#### 1. DCR is OPEN — 201 Created without auth

Registering a new OAuth client requires NO authentication:

```http
POST /register HTTP/2
Host: api.anthropic.com
Content-Type: application/json

{"redirect_uris":["https://anthropic-validate2.requestcatcher.com/cb"]}

→ HTTP/2 201 Created
→ client_id: 43c283c4-701e-48ca-bbfa-dc15f0b5b548
```

Confirmed 5+ times with different payloads. Always 201.

#### 2. /authorize VALIDATES DCR client_ids

The /authorize endpoint accepts client_ids registered via DCR:

- Valid DCR client_id + claude.ai redirect → **302 redirect** to MCP connector
- Non-existent client_id → **400 "Invalid client_id"**

This proves DCR is wired to the authorization server.

#### 3. Server-side redirect_uri whitelist is enforced

/authorize has its OWN redirect_uri whitelist that does NOT include DCR-registered URIs:

| redirect_uri | Result |
|-------------|--------|
| Registered via DCR (requestcatcher.com) | 403 "not authorized" |
| claude.ai/callback | 302 (works!) |
| minimal-test.com | 400 "Unregistered" |
| @evil.com bypass | 400 |
| .evil.com bypass | 400 |

#### 4. Client impersonation is possible

Clients can be registered with arbitrary names, including "Claude Desktop":

```json
POST /register
{"redirect_uris":["https://claude.ai/callback"],"client_name":"Claude Desktop",...}
→ 201 Created, client_id: 5e4c2d6a-79be-4ec4-b300-5fbce6235da1
```

However, no consent screen displays this name to users in the current flow.

#### 5. MCP GDrive connector is DEPRECATED (410 Gone)

The redirect target `/mcp/gdrive/google/install` returns:

> "This MCP server has been turned down. Please use drivemcp.googleapis.com/mcp/v1 instead"

#### 6. OAuth metadata publicly exposed

```json
GET /.well-known/oauth-authorization-server → 200
{
  "issuer": "https://api.anthropic.com/mcp/gdrive",
  "registration_endpoint": "https://api.anthropic.com/register",
  "authorization_endpoint": "https://api.anthropic.com/authorize",
  "token_endpoint": "https://api.anthropic.com/token",
  "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256"]
}
```

#### 7. OAuth security measures observed

| Control | Status |
|---------|--------|
| PKCE | ✅ Required (S256 only) |
| redirect_uri whitelist | ✅ Server-side |
| Auth code grant only | ✅ No client_credentials |
| client_secret rotation | ⚠️ `client_secret_expires_at: 0` (never) |

---

### What Was NOT Confirmed (Limited Impact)

| Claim | Status | Reason |
|-------|--------|--------|
| Token issuance | ❌ | Requires real user auth via browser |
| Scope reflection | ❌ | Token never obtained to check scopes |
| Consent bypass | ❌ | Not found in testing |
| Session fixation | ❌ | /consent not accessible directly (404) |
| MCP tool access | ❌ | Connector is deprecated (410) |
| ATO chain (CRITICAL) | ❌ | Speculative — no chain demonstrated |

---

### Impact Assessment

**Standalone impact:** LOW-MEDIUM
- Anyone can register OAuth clients on the Anthropic API
- No authentication or rate limiting on registration
- Client impersonation is possible (register as "Claude Desktop")
- However, registered clients cannot use arbitrary redirect URIs in /authorize
- The MCP connector that client_ids relate to is deprecated

**Practical risk:** The open registration creates a surface for:
1. **Client enumeration**: Confidential client_ids can be discovered
2. **Spam/phishing**: Registering look-alike clients with legitimate names
3. **Future risk**: If new MCP connectors are added without proper authorization controls

**What would raise severity:**
- If a new MCP connector is deployed that accepts DCR client_ids with custom redirect_uris
- If token issuance without user authentication is possible via another grant type
- If scope escalation from DCR registration is confirmed

---

### CVSS Analysis

**Standalone CVSS: 5.3 (MEDIUM)**
`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N`

- AV:N (Network): Internet-accessible
- AC:L (Low): No special conditions
- PR:N (None): No authentication required
- UI:N (None): No user interaction for registration
- S:U (Unchanged): No scope change
- C:L (Low): Confidential client_ids exposed
- I:L (Low): Ability to create/register data on the platform
- A:N (None): No availability impact

---

### Remediation Recommendations

1. **Require authentication** for the `/register` endpoint (API key or admin approval)
2. **Implement rate limiting** specifically on /register (200 req/hour max)
3. **Audit existing registered clients** — review all entries for suspicious activity
4. **Remove or restrict `client_secret_expires_at: 0`** in minimal-payload registrations
5. **Consider removing the deprecated metadata** (`issuer` points to deprecated MCP server)

---

### Evidence

**Registered Clients (all confirmed):**
| Client ID | Name | redirect_uri | Secret | Expires |
|-----------|------|-------------|--------|---------|
| f2bc56ca-... | MCP Integration | requestcatcher.com/callback | None (public) | N/A |
| 629a603e-... | (minimal) | minimal-test.com/cb | a7c86522... | Never (0) |
| 43c283c4-... | Validation Test | requestcatcher.com/cb | None (public) | N/A |
| 5e4c2d6a-... | Claude Desktop | claude.ai/callback | None (public) | N/A |
| db51c0d4-... | Official Claude Desktop | claude.ai | None (public) | N/A |
| 60336ba2-... | Test Client | requestcatcher.com/callback | None (public) | N/A |

**Server Identity:**
- `x-powered-by: Express` (Node.js Express)
- `server: cloudflare` (Cloudflare CDN)
- TLS: Google Trust Services, TLS 1.3, X25519
- Rate limit: 100 requests / 900 seconds

**Discovery timestamp:** 2026-06-28 23:28:29 UTC
**Last validation:** 2026-06-28 23:39:00 UTC

---

### References

- RFC 7591 — OAuth 2.0 Dynamic Client Registration Protocol
- RFC 6749 — The OAuth 2.0 Authorization Framework
- CWE-306: Missing Authentication for Critical Function
- OAuth 2.0 Security BCP (RFC 9700)

---

### Notes

This finding was submitted after thorough validation including:
- 6+ registration attempts with varying payloads
- redirect_uri whitelist bypass testing (6 techniques)
- PKCE requirement verification
- Grant type enumeration
- Client impersonation testing
- MCP connector probe and follow
- /authorize client_id validation confirmation
- /token endpoint behavior analysis
