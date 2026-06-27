# AR4 — Internal Debug/Test Interface Publicly Exposed at cdn.arkoselabs.com/v2/

**Título:** Internal "Client API Modal Test" Development Interface Exposed to Unauthenticated Public Access
**Severidade:** LOW (CVSS 4.3) standalone; contextually MEDIUM when combined with CORS open and token exfiltration
**CVSS Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` → **4.3 LOW**
**CWE:** CWE-200 (Exposure of Sensitive Information) / CWE-489 (Active Debug Code Left in Production)
**Target:** `cdn.arkoselabs.com` (Core Application — $100-$300)
**Status:** Confirmed — accessible without authentication, full HTML source in 200 response

---

## Summary

`cdn.arkoselabs.com/v2/` serves a fully functional internal development and QA test interface titled **"Client API Modal Test"** that is accessible to anyone on the internet without authentication. This page:

1. Allows loading the Arkose CAPTCHA SDK with **any customer's publicKey**
2. Exposes Arkose's internal testing infrastructure and build toolchain details
3. Is served with `Access-Control-Allow-Origin: *` (CORS open to any website)
4. Has a weaker Content Security Policy (`'unsafe-inline'`) compared to the production iframe
5. Uses a hardcoded placeholder nonce `"12345678910"` — evidence this is dev tooling, not production code

---

## Proof of Concept

```bash
# Public access without authentication
curl -si "https://cdn.arkoselabs.com/v2/" \
  -H "Origin: https://evil.com"

# Response:
# HTTP/2 200
# Access-Control-Allow-Origin: *
# Content-Type: text/html; charset=utf-8
# Content-Security-Policy: script-src 'self' *.arkoselabs.com ... 'unsafe-inline'; ...
# 
# <!DOCTYPE html>
# <html lang="en"><head>...<title>Client API Modal Test</title>...
```

**Live URL:** `https://cdn.arkoselabs.com/v2/` (also: `https://cdn.arkoselabs.com/v2/DEMO/`)

---

## What the Interface Exposes

### 1. Full Testing Capability for Any Customer publicKey
The page accepts a publicKey via URL path (`/v2/{publicKey}/`) or via an HTML input field (`#publicKey`). This allows:
- Testing any known Arkose customer's challenge configuration
- Enumerating which publicKeys have suppression enabled (behavioral signals)
- Observing customer-specific CAPTCHA configurations (theme, language, etc.)

```javascript
// From the page source:
if (!publicKey) {
    // Shows input field — user can enter any publicKey
    document.querySelector('#setPublicKey').addEventListener('click', function() {
        var rawPublicKey = document.querySelector('#publicKey').value;
        publicKey = sanitize(rawPublicKey);
        setConfig(window.enforcement);
    });
}
```

### 2. Placeholder Security Values
```javascript
script.setAttribute("data-nonce", "12345678910")  // ← Not a real nonce! Dev placeholder.
```
The nonce `12345678910` is clearly a hardcoded test value. In the production iframe, the nonce is `ea1059e09780776c4a6301e8867454e2` (which is itself a static vulnerability — AR2). Using a numeric sequence as a nonce demonstrates this is dev tooling.

### 3. CSP with `unsafe-inline` — Weaker Than Production
| Endpoint | CSP Script Policy |
|----------|------------------|
| `iframe.arkoselabs.com` | `'nonce-ea1059e09780776c4a6301e8867454e2'` (nonce-based) |
| `cdn.arkoselabs.com/v2/` | `'unsafe-inline'` ← **Weaker** |

The `unsafe-inline` directive means any injected inline script would execute without needing to know a nonce.

### 4. Cross-Origin Access to Testing Tool
Because the page is served with `ACAO: *`:
```javascript
// Any attacker-controlled page can:
fetch('https://cdn.arkoselabs.com/v2/', {mode: 'cors'})
    .then(r => r.text())
    .then(html => {
        // Read the full test interface source
        // Load it in a hidden iframe
        // Access all internal test capabilities
    });
```

### 5. Internal Version Information
```html
<footer class="footer">
    <div>Client-API Version: 2.17.6</div>
</footer>
```

The page reveals the exact version of the Arkose client API deployed to production. This enables targeted vulnerability research against known SDK versions.

---

## Observed Headers vs Production Comparison

| Header | `cdn.arkoselabs.com/v2/` (Debug) | `iframe.arkoselabs.com` (Production) |
|--------|-----------------------------------|---------------------------------------|
| `Access-Control-Allow-Origin` | `*` (any origin) | Not set (CORS blocked) |
| `Content-Security-Policy script-src` | `'unsafe-inline'` | `'nonce-...'` |
| `data-nonce` attribute | `12345678910` (placeholder) | `ea1059e09780776c4a6301e8867454e2` |
| X-Frame-Options | Not set | Not set |
| Cache-Control | `max-age=0, s-maxage=31536000` | `(not set)` |

---

## Attack Scenario: Token Harvesting via Debug Page

**Combined with AR3 (postMessage wildcard):**
1. Attacker embeds `cdn.arkoselabs.com/v2/{VICTIM_PUBLICKEY}/` in a hidden iframe
2. The debug interface loads the Arkose SDK with the victim's publicKey
3. If the visiting user is recognized as low-risk, `challenge-suppressed` fires
4. The sessionToken is broadcast to `"*"` (parent window = attacker's page)
5. Attacker receives a valid sessionToken for the victim's publicKey

The CDN debug interface makes this attack **easier** than using `iframe.arkoselabs.com` because:
- It's a fully functional test harness (not just the iframe wrapper)
- It explicitly logs tokens to the page (`updateToken(event.token)`)
- CORS allows reading the test interface from any domain

---

## Why This Exists

This appears to be Arkose's internal QA/integration testing tool — a page their engineers use to test the Client API SDK with different publicKeys and configurations. It was deployed to `cdn.arkoselabs.com/v2/` (alongside the SDK assets) without access restrictions.

The file path suggests it's the S3 bucket's "directory default document" for `/v2/` — when no specific file is requested, S3 returns `index.html`, which in this case is the test interface.

---

## Remediation

**Immediate:**
1. Restrict access to `cdn.arkoselabs.com/v2/` (the HTML interface) to internal IP ranges only, or remove it from the CDN entirely
2. The `api.js` file at `/v2/{publicKey}/api.js` is intentionally public and should remain so

**Short-term:**
3. Add `X-Robots-Tag: noindex` to prevent search engine discovery
4. Audit other paths on `cdn.arkoselabs.com` for additional debug/test content
5. Replace `data-nonce="12345678910"` with a real nonce (or remove the debug page)

---

## CVSS Breakdown

| Metric | Value | Reason |
|--------|-------|--------|
| Attack Vector | Network | Internet-accessible |
| Attack Complexity | Low | No special conditions needed |
| Privileges Required | None | No auth |
| User Interaction | None | Direct access works |
| Scope | Unchanged | Impact within CDN service |
| Confidentiality | Low | Version info, test capabilities |
| Integrity | None | Page is read-only |
| Availability | None | Service not disrupted |

**CVSS Base Score: 4.3 LOW**

*When combined with AR3 (sessionToken wildcard broadcast), this is a direct enabler for CAPTCHA bypass. Chained severity: MEDIUM (6.5+)*

---

## Notes

- Testing was limited to: 1 GET request to confirm the finding
- No customer publicKeys were tested through the debug interface
- No tokens were captured or exfiltrated
- This page is publicly cached by CloudFront (age: 833399 seconds ≈ 9.6 days)
