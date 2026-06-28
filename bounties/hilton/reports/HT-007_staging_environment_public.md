# HT-007: Staging Environment Publicly Accessible — suppliersconnectionstage.hilton.com

**Program:** Hilton HackerOne  
**Asset:** `*.hilton.com` (Tier B)  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)  
**CWE:** CWE-668 — Exposure of Resource to Wrong Sphere  
**Status:** Ready to submit

---

## Summary

`https://suppliersconnectionstage.hilton.com` is a publicly accessible staging environment of the Hilton Suppliers' Connection portal that:

1. **Is reachable from the public internet** without IP allowlisting or access controls
2. **Exposes the same unauthenticated admin interface** found in production (same as HT-002): content management fields, file upload handlers, and announcement management without authentication
3. **Uses a separate Google Analytics ID** (`UA-66328623-3` vs. production `UA-66328623-1`), confirming it is a distinct, independently tracked environment
4. **Accepts unauthenticated file uploads** at the same path as production: `/Handlers/FileUpload.ashx`
5. **Has a ViewState with value** — indicating state is being maintained on this instance, suggesting it may have real test/staging data

Staging environments typically have weaker security controls, contain test credentials, may connect to shared infrastructure, and can reveal pre-production features and functionality that is not yet patched.

---

## Proof of Concept

### Step 1: Confirm staging environment is publicly reachable

```bash
curl -si "https://suppliersconnectionstage.hilton.com/" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne"
# HTTP/2 302 → HTTP/2 200 — accessible without IP restrictions
```

### Step 2: Unauthenticated admin interface (same as HT-002)

```bash
curl -s "https://suppliersconnectionstage.hilton.com/learninglounge/home.aspx" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  | grep -E "textAnnouncement|txtClickActionURL|chkEnabled|chkEveryone|fileTileImage"
```

**Response: HTTP 200, same admin content management fields present:**

```html
<textarea name="textAnnouncement"></textarea>
<input type="text" name="txtClickActionURL" />
<input type="checkbox" name="chkEnabled" />
<input type="checkbox" name="chkEveryone" />
<input type="file" name="fileTileImage" />
<textarea name="textTemplate1"></textarea>
<textarea name="textTemplate2"></textarea>
```

### Step 3: Unauthenticated file upload handler

```bash
# Same GIFAR/SVG-as-JPEG attack as in HT-003
curl -si "https://suppliersconnectionstage.hilton.com/Handlers/FileUpload.ashx?op=upload&type=image" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -F "file=@xss_payload.jpg;type=image/jpeg"
# HTTP/2 200 — accepted without authentication
```

### Step 4: Google Analytics confirms separate environment

- Staging GA ID: `UA-66328623-3`
- Production GA ID: `UA-66328623-1`

### Step 5: Admin pages discoverable on staging

```bash
# HTTP 200 (content varies — some show error page, some may expose data):
/learninglounge/home.aspx      → 200 (admin content management exposed)
/Handlers/FileUpload.ashx      → 200 (upload handler accessible)
/LearningLounge/Admin.aspx     → 200
/LearningLounge/Announcements.aspx → 200
/LearningLounge/Tiles.aspx     → 200
/LearningLounge/Slides.aspx    → 200
/Account/Profile.aspx          → 200
/Account/Users.aspx            → 200
/Account/ApprovedCategories.aspx → 200
```

---

## What Staging Environments Typically Expose

1. **Test credentials** embedded in pages, comments, or environment variables
2. **Less mature WAF rules** — injection attacks that are blocked in production may succeed here
3. **Debug output** — error messages, stack traces, verbose logging
4. **Pre-production features** — functionality not yet enabled in production (e.g., new auth flows, new admin panels)
5. **Shared infrastructure** — staging may connect to the same database or internal services as production, meaning staging compromise can pivot to production data

---

## Impact

1. **Extended attack surface**: Every vulnerability found on the production `suppliersconnection.hilton.com` (HT-002, HT-003) applies equally to the staging environment, doubling the exploitable attack surface.

2. **Staging-to-production pivot**: If staging shares credentials, database connections, or session tokens with production (a common misconfiguration), an attacker who exploits staging can access production data.

3. **Less monitoring**: Staging environments often have reduced security monitoring, allowing extended reconnaissance and exploitation without triggering production security controls.

4. **Information disclosure**: Staging may expose additional debugging information, configuration files, or test accounts that reveal the application's structure and internal logic.

---

## Steps to Reproduce

1. Navigate to `https://suppliersconnectionstage.hilton.com/` — observe HTTP 302 → 200 (accessible)
2. Navigate to `https://suppliersconnectionstage.hilton.com/learninglounge/home.aspx` — observe same admin CMS fields without authentication as found in production
3. Perform file upload: `POST /Handlers/FileUpload.ashx?op=upload&type=image` with any `.jpg` file — observe HTTP 200 (accepted)

---

## Recommendations

1. **IP-restrict staging environments**: Staging should only be accessible from corporate VPN or allowlisted IPs.
2. **Require authentication**: Even if content is not sensitive, staging should require authentication before serving any content.
3. **Separate infrastructure**: Staging should not share database connections, API keys, or credentials with production.
4. **WAF rules**: Apply the same WAF profile to staging as production.

---

## Related Findings

- **HT-002**: Same unauthenticated admin interface on production `suppliersconnection.hilton.com`
- **HT-003**: Same unauthenticated file upload handler on production `suppliersconnection.hilton.com`

---

## References

- CWE-668: Exposure of Resource to Wrong Sphere
- OWASP A05:2021 — Security Misconfiguration
- OWASP Testing Guide: OTG-CONFIG-008 — Test RIA Cross Domain Policy
