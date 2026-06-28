# HT-006: GraphQL Error Messages Expose Internal REST API Paths + WSO2 Misconfiguration

**Program:** Hilton HackerOne  
**Asset:** `hilton.com` (Tier A)  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)  
**CWE:** CWE-209 — Generation of Error Message Containing Sensitive Information  
**Status:** Ready to submit

---

## Summary

When GraphQL mutations are invoked without authentication, the error response body leaks:

1. **Internal REST API path templates** — e.g., `/hospitality-{realm}/v2/guests/{guestId}/creds/password`
2. **Unresolved WSO2 template variable** — `{realm}` is URL-encoded as `%7Brealm%7D` in the error path, indicating the backend gateway has an unresolved configuration placeholder
3. **WSO2 API Manager error codes** — `900902` ("Missing Credentials") reveals the internal API gateway product
4. **Misconfigured auth header name** — The description reads `null : Bearer ACCESS_TOKEN` (the expected Authorization header name is `null` — a WSO2 misconfiguration)
5. **Internal microservice name** — `dx-guests-gql` appears in the `context` field of every error

These details allow an attacker to:
- Map the internal REST API structure behind the GraphQL facade
- Identify the WSO2 API Manager as the gateway product for targeted CVE research
- Understand the backend URL scheme for direct API access attempts

---

## Proof of Concept

### Path Disclosure 1: `updateGuestPassword`

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "updateGuestPassword",
    "query": "mutation updateGuestPassword($guestId: BigInt!, $input: GuestSetPasswordInput!, $language: String!) { updateGuestPassword(guestId: $guestId, input: $input, language: $language) { _id error { code message } } }",
    "variables": {"guestId": 100000000, "input": {"password": "x", "newPassword": "y", "confirmNewPassword": "y"}, "language": "en"}
  }'
```

**Response (HTTP 401):**
```json
{
  "errors": [{
    "message": "Unauthorized",
    "extensions": {
      "code": "401",
      "request": {
        "method": "POST",
        "path": "/hospitality-%7Brealm%7D/v2/guests/100000000/creds/password"
      },
      "response": {
        "body": {
          "code": "900902",
          "message": "Missing Credentials",
          "description": "Invalid Credentials. Make sure your API invocation call has a header: 'null : Bearer ACCESS_TOKEN' or 'null : Basic ACCESS_TOKEN' or 'apikey: API_KEY'"
        }
      }
    },
    "context": "dx-guests-gql",
    "code": 401
  }]
}
```

### Path Disclosure 2: `createGuest`

```bash
curl -s "https://www.hilton.com/graphql/customer" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{
    "operationName": "createGuest",
    "query": "mutation createGuest($input: EnrollInput!, $language: String!) { createGuest(input: $input, language: $language) { _id error { code message } } }",
    "variables": {"input": {"name": {"firstName":"Test","lastName":"User"}, "email": {"emailAddress":"t@t.com"}, "address": {"country":"US","addressType":"home"}, "preferredLanguage":"en","privacyRequested":false}, "language":"en"}
  }'
```

**Response — leaks enrollment path:**
```json
{
  "request": {
    "method": "POST",
    "path": "/hospitality-%7Brealm%7D/v2/realms/guests/enroll"
  }
}
```

---

## Leaked Information Summary

| Artifact | Value |
|---------|-------|
| Internal API prefix | `/hospitality-customer/v2/` |
| Password change path | `POST /hospitality-customer/v2/guests/{guestId}/creds/password` |
| Enrollment path | `POST /hospitality-customer/v2/realms/guests/enroll` |
| Guest data path | `GET /hospitality-customer/v2/guests/{guestId}` |
| Property data path | `GET /hospitality-customer/v2/props/{ctyhocn}` |
| WSO2 realm | `customer` (seen resolved in `amexPrefill` and `travelDocOptions` errors) |
| Unresolved template | `{realm}` → URL-encoded `%7Brealm%7D` in guest/password errors (config bug) |
| Gateway product | WSO2 API Manager (error code 900902 is WSO2-specific) |
| Misconfigured header | Header name resolves to `null` instead of `Authorization` |
| Internal microservices | `dx-guests-gql`, `dx-offers-gql`, `dx-reservations-gql` |

---

## Additional Context: Unresolved Template Variable

The path `/hospitality-%7Brealm%7D/v2/guests/...` where `%7Brealm%7D` is the URL-encoded `{realm}` indicates that WSO2 API Manager has a dynamic context variable `{realm}` that is never being substituted before the path is used in error messages. In a properly configured WSO2 deployment, `{realm}` would resolve to the tenant identifier (e.g., `hilton`) at request time. Its presence unexpanded in production suggests a misconfiguration in the WSO2 API definition.

---

## Impact

1. **Attack surface mapping**: Knowing the internal path scheme `/hospitality-{realm}/v2/guests/{guestId}/creds/password` enables direct bypass attempts against the WSO2 layer if WAF rules or network segmentation are misconfigured.

2. **WSO2 CVE targeting**: With the gateway product identified as WSO2 API Manager, an attacker can research applicable CVEs (e.g., authentication bypass, information disclosure, SSRF chains in WSO2 AM).

3. **Configuration intelligence**: The `null : Bearer` header name reveals a misconfiguration that may indicate broader WSO2 setup issues — an attacker can attempt calls with `null: Bearer TOKEN` headers directly against any exposed WSO2 endpoints.

4. **Numeric ID enumeration hint**: The path `/hospitality-{realm}/v2/guests/100000000/creds/password` confirms that `guestId` is a sequential BigInt — combined with IDOR vulnerabilities (if found), this confirms numeric enumeration is feasible.

---

## Recommendations

1. **Sanitize GraphQL error responses**: Do not forward raw backend `request.path` or `response.body` fields from internal gateway errors to API consumers. Return only a generic error message.
2. **Fix WSO2 configuration**: Resolve the `{realm}` template variable substitution. The variable should be replaced with the actual tenant name at API definition time or at runtime.
3. **Fix `null` header name**: The Authorization header mapping in WSO2 API Manager needs to be explicitly configured to `Authorization` instead of resolving to `null`.
4. **Limit error context**: Remove the `context: "dx-guests-gql"` field from error responses — internal service names should not be exposed in external APIs.

---

## References

- WSO2 error codes: https://apim.docs.wso2.com/en/latest/troubleshooting/error-handling/
- CWE-209: Information Exposure Through an Error Message
- OWASP API Security A09:2023 — Improper Inventory Management
