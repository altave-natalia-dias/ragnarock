# HT-002: suppliersconnection.hilton.com — Unauthenticated Admin Interface Exposure

**Program:** Hilton HackerOne  
**Asset:** `suppliersconnection.hilton.com` (Tier B)  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)  
**CWE:** CWE-284 — Improper Access Control  
**Status:** Ready to submit (pending: confirm with authenticated session that fields are also admin-only)

---

## Summary

The Learning Lounge section of `suppliersconnection.hilton.com` at `/learninglounge/home.aspx` is accessible by any unauthenticated user. The page exposes a full content management and admin interface including:

- Announcement creation form (`textAnnouncement` textarea)
- URL-based click action fields (`txtClickActionURL`, `txtTileClickActionURL`)
- Content publishing controls (`chkEnabled`, `chkEnabledAnnouncement`, `chkTileEnabled`)
- Audience targeting checkboxes (`chkEveryone`, `chkPartners`, `chkOwnersConsultants`, `chkEmployeesOnly`)
- File upload inputs for announcements and promotional tiles (`fileUploadAnnouncement`, `fileTileImage`)
- HTML template editing textareas (`textTemplate1`, `textTemplate2`)
- Partner ID reference (`ctl00$mainContent$txtPartnerId`)
- Region targeting (`txtRegions`)

**These fields appear intended for administrator-only use** (content management of what suppliers see). Their presence in the unauthenticated page HTML constitutes an information disclosure and incomplete access control implementation.

---

## Proof of Concept

No parameters, no authentication, no cookies required:

```bash
curl -s "https://suppliersconnection.hilton.com/learninglounge/home.aspx" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" | grep -E "textAnnouncement|txtClickActionURL|chkEnabled|chkEveryone|fileTileImage"
```

**Response: HTTP 200, admin fields present in HTML:**

```html
<!-- Announcement admin fields -->
<textarea name="textAnnouncement" id="textAnnouncement" maxlength="500"></textarea>
<input type="checkbox" name="chkEnabledAnnouncement" id="chkEnabledAnnouncement" value="enabled" />

<!-- URL injection target -->
<input type="text" name="txtClickActionURL" id="txtClickActionURL" />
<select name="selectClickType" id="selectClickType">...</select>

<!-- Audience targeting -->
<input type="checkbox" name="chkEveryone" id="chkEveryone" />
<input type="checkbox" name="chkPartners" id="chkPartners" />
<input type="checkbox" name="chkOwnersConsultants" id="chkOwnersConsultants" />
<input type="checkbox" name="chkEmployeesOnly" id="chkEmployeesOnly" />

<!-- File uploads -->
<input type="file" name="fileUploadAnnouncement" id="fileUploadAnnouncement" />
<input type="file" name="fileTileImage" id="fileTileImage" />

<!-- HTML templates -->
<textarea id="textTemplate1" name="textTemplate1"></textarea>
<textarea id="textTemplate2" name="textTemplate2"></textarea>

<!-- Partner reference (IDOR potential) -->
<input type="hidden" name="ctl00$mainContent$txtPartnerId" id="mainContent_txtPartnerId" />
```

**Additional observations:**
- The `?r=` URL parameter shown in navigation links (e.g., `/learninglounge/home.aspx?r=UM5V9ZV8`) is **not validated server-side** — any value (including empty) returns HTTP 200 with full admin interface.
- 61 total form inputs are exposed including Meet&Greet form (company/contact/phone/email/file upload) and Lunch&Learn form.
- `__VIEWSTATEENCRYPTED` field is present but empty, indicating ViewState encryption is not active.
- Google Analytics ID `UA-66328623-1` disclosed.

---

## Impact

1. **Admin interface structure disclosure**: An attacker can fully map the CMS capabilities of the Learning Lounge (announcements, tiles, URL-based navigation, template system, audience segmentation) without logging in.

2. **Attack surface for authenticated exploitation**: Combined with a valid supplier session, these fields could enable: stored XSS via `textTemplate1/2` (HTML template injection), stored XSS or phishing via `txtClickActionURL` (javascript: URI stored as clickable link), mass-audience announcement injection (`chkEveryone` + `textAnnouncement`), unauthorized content publishing/unpublishing (`chkEnabled` flags).

3. **Broken access model**: The page serves a mixed interface (public Meet&Greet submission + admin content management) without role separation. The admin fields being present in the unauthenticated page suggests the role check is applied server-side during POST processing but not during initial GET rendering — this is a defense-in-depth gap.

---

## Steps to Reproduce

1. Open a browser with Developer Tools → Network tab.
2. Navigate to: `https://suppliersconnection.hilton.com/learninglounge/home.aspx`
3. Observe HTTP 200 response with full page content.
4. In DevTools → Elements, search for `textAnnouncement`, `txtClickActionURL`, `chkEveryone` — all present without any login.
5. No session cookie, no authentication header, no access code required.

---

## Recommendations

1. Serve admin fields only to authenticated sessions with the appropriate role (admin/content-manager).
2. Split the page into a public form (Meet&Greet submission) and a protected admin section with role-based rendering.
3. Validate ViewState encryption: set `ViewStateEncryptionMode="Always"` in the page directive.
4. Remove or randomize the Google Analytics ID if it is meant to be confidential.

---

## Notes

The suppliersconnection.hilton.com program note states CSRF is temporarily excluded. This report does not rely on CSRF — it demonstrates unauthenticated GET access to admin-facing HTML structure.
