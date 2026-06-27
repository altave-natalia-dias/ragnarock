# AR2 — Static CSP Nonce Defeats XSS Protection on iframe.arkoselabs.com

**Título:** CSP Nonce is Static (Hardcoded in CloudFront Cache) on iframe.arkoselabs.com, Rendering Nonce-Based Protection Ineffective  
**Severidade:** LOW (CVSS 3.7) standalone; escalates to HIGH if chained with XSS  
**CVSS Vector:** `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:N` → **3.7 LOW**  
**CWE:** CWE-330 (Use of Insufficiently Random Values) / CWE-693 (Protection Mechanism Failure)  
**Target:** `iframe.arkoselabs.com` (Core Application — $100-$300 as standalone LOW)  
**Status:** Confirmado — nonce idêntico em múltiplas requisições independentes  

---

## Summary

The Arkose challenge iframe page (`iframe.arkoselabs.com`) deploys a Content Security Policy (CSP) that uses a `nonce` to authorize inline scripts. However, the nonce value is **hardcoded in a static HTML file** stored in AWS S3 and served through CloudFront — it never changes between requests. This fundamentally defeats the security model of nonce-based CSP: the nonce's value is publicly known and identical for every page load.

A Content Security Policy nonce must be cryptographically random and unique per-request. When it is static, any script injection capable of including the known nonce value bypasses CSP protection entirely.

---

## Affected Files

| URL | Nonce Value | Cache State |
|-----|------------|-------------|
| `https://iframe.arkoselabs.com/` | `ea1059e09780776c4a6301e8867454e2` | `x-cache: Hit`, `age: 8645+` |
| `https://iframe.arkoselabs.com/v2/DEMO/2.17.6/enforcement.cdeb82f474225dff1677448c6bc82e87.html` | `2e86232d80ec842350915967bb1e356d` | `x-cache: Miss` (but nonce still static in S3 source) |

---

## Proof of Concept — Static Nonce Verification

The following commands confirm the nonce is identical across 3 independent requests:

```bash
# Request 1
curl -s "https://iframe.arkoselabs.com" | grep -oP 'nonce="[^"]+"' | head -1
# Output: nonce="ea1059e09780776c4a6301e8867454e2"

# Request 2 (different session, no cache headers)
curl -s "https://iframe.arkoselabs.com" | grep -oP 'nonce="[^"]+"' | head -1
# Output: nonce="ea1059e09780776c4a6301e8867454e2"

# Request 3
curl -s "https://iframe.arkoselabs.com" | grep -oP 'nonce="[^"]+"' | head -1
# Output: nonce="ea1059e09780776c4a6301e8867454e2"
```

**All three requests return the exact same nonce.**

The CSP header confirms it:
```
content-security-policy: 
  default-src 'self' iframe.arkoselabs.com client-api.arkoselabs.com;
  script-src 'self' 'nonce-ea1059e09780776c4a6301e8867454e2' iframe.arkoselabs.com client-api.arkoselabs.com;
  style-src 'self' 'nonce-ea1059e09780776c4a6301e8867454e2' iframe.arkoselabs.com client-api.arkoselabs.com;
```

The same nonce also appears twice in the HTML body:
```html
<style nonce="ea1059e09780776c4a6301e8867454e2">body{margin:0}</style>
<script nonce="ea1059e09780776c4a6301e8867454e2">...
```

---

## Root Cause

The enforcement page is stored as a static HTML file in AWS S3 and served via CloudFront. During deployment/build, a nonce value was generated and baked into the file. Because the file is static (not server-side rendered per-request), the nonce is the same for every visitor.

**CloudFront cache evidence:**
```
x-cache: Hit from cloudfront
age: 8645         ← served from cache for ~2.4 hours (same nonce)
last-modified: Tue, 23 Jun 2026 03:59:19 GMT  ← static file
```

The enforcement HTML and the CSP nonce header are generated from the same static file — they always match, and both are always the same value.

---

## Impact

### Standalone Impact
As an isolated finding, the static nonce makes CSP nonce protection equivalent to having no CSP nonce protection at all. The policy `'nonce-ea1059e09780776c4a6301e8867454e2'` provides the same security as `'unsafe-inline'` (none).

### Impact if Chained with XSS
If any future XSS vulnerability is found on `iframe.arkoselabs.com` or in the Arkose JavaScript SDK running within the iframe, the known nonce would allow bypassing the CSP:

```javascript
// Attacker-injected payload using the known static nonce
<script nonce="ea1059e09780776c4a6301e8867454e2">
    parent.postMessage(JSON.stringify({
        eventId: "challenge-complete",
        publicKey: document.location.pathname,
        payload: {sessionToken: "FORGED_TOKEN"}
    }), "*");
</script>
```

This would execute within the iframe context, post a forged completion event to the parent window, and potentially trick integrators into accepting a fabricated `sessionToken`.

### Context of the Arkose iframe
The iframe is the core trust boundary in Arkose's architecture:
- It runs `client-api.arkoselabs.com/v2/{publicKey}/api.js` (73KB of proprietary JS)
- It emits `sessionToken` values via `postMessage`
- A successful CSP bypass in the iframe could undermine the entire challenge-response integrity model

---

## Remediation

**Required:** The HTML file must be dynamically rendered server-side (or via a Lambda@Edge / CloudFront function) to inject a unique, cryptographically random nonce per request.

```javascript
// CloudFront Function (Node.js) — inject dynamic nonce
function handler(event) {
    const crypto = require('crypto');
    const nonce = crypto.randomBytes(16).toString('hex');
    
    // Inject nonce into CSP header and HTML body
    const response = event.response;
    response.headers['content-security-policy'] = {
        value: `script-src 'nonce-${nonce}' 'self' iframe.arkoselabs.com; ...`
    };
    return response;
}
```

Or switch to **hash-based CSP** for the static inline scripts, which does not require per-request randomness:
```
script-src 'sha256-{hash_of_inline_script}' 'self' ...
```

---

## CVSS Breakdown

| Metric | Value | Reason |
|--------|-------|--------|
| Attack Vector | Network | Exploitable from anywhere |
| Attack Complexity | High | Requires XSS in iframe to exploit fully |
| Privileges Required | None | — |
| User Interaction | None | — |
| Scope | Unchanged | — |
| Confidentiality | Low | Static nonce is already public |
| Integrity | Low | Potential future CSP bypass |
| Availability | None | — |

**Standalone CVSS: 3.7 LOW**

*Chained with XSS: CVSS could reach HIGH (7.0+) depending on the XSS impact in the iframe context.*

---

## Supplementary: postMessage Wildcard Target

As a related observation, every postMessage event emitted by the iframe uses `"*"` as the target origin:

```javascript
parent.postMessage(JSON.stringify({
    eventId: "challenge-complete",
    publicKey: t,
    payload: {sessionToken: e.token}
}), "*");  // ← broadcasts to all origins
```

This is likely an intentional design choice (Arkose doesn't know which domain embeds the iframe), but it means the `sessionToken` is sent to the direct parent window regardless of its origin. If combined with the static nonce bypass above, an injected script in the iframe could forge challenge-complete events and intercept them.

---

## Notes

- All testing was passive (read-only HTTP GET/HEAD requests to public endpoints)
- No authenticated sessions were tested or required
- No production customer data was accessed
