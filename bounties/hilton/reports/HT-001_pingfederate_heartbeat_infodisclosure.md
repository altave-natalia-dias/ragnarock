# HT-001: PingFederate Heartbeat Endpoint — Sensitive Information Disclosure

**Program:** Hilton HackerOne  
**Asset:** `fd.hilton.com` (*.hilton.com — Tier B)  
**Severity:** Medium  
**CVSS:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)  
**CWE:** CWE-200 — Exposure of Sensitive Information to an Unauthorized Actor  
**Status:** Ready to submit

---

## Summary

The PingFederate Identity Provider at `https://fd.hilton.com/pf/heartbeat.ping` is publicly accessible without authentication and returns detailed internal infrastructure information including:

- **Internal cluster IP addresses** (8 nodes across two subnets)
- **Microsoft Azure tenant IDs and domains** 
- **Authentication adapter names** (internal identity flow topology)
- **Database connection pool identifiers** (JDBC/LDAP)
- **Real-time performance metrics** (CPU, JVM memory, response times, transaction counts)

This information disclosure aids an attacker in mapping Hilton's internal infrastructure and identity architecture, reduces reconnaissance time for targeted attacks, and enables more precise social engineering (e.g., Azure AD-targeted phishing using disclosed tenant information).

---

## Proof of Concept

```bash
curl -s "https://fd.hilton.com/pf/heartbeat.ping" \
  -H "User-Agent: Mozilla/5.0 ... HackerOne"
```

**Response (HTTP 200, unauthenticated):**

```json
{"items":[{
  "cluster.members": "[10.72.40.45:7300, 10.72.40.45:7200, 10.72.40.46:7200, 10.72.40.47:7200, 10.72.40.47:7300, 10.80.40.170:7200, 10.80.40.34:7200, 10.80.40.32:7200]",
  "cluster.members.detail": "[{address=10.72.40.45:7300, mode=CLUSTERED_CONSOLE, consoleRole=PASSIVE, ...}, {address=10.72.40.45:7200, mode=CLUSTERED_ENGINE}, ...]",
  "connection.https://login.microsoftonline.com/660292d2-cfd5-4a3d-b7a7-e8f7ee458a0a/v2.0.token.count": "7",
  "connection.https://login.microsoftonline.com/hilton.onmicrosoft.com/v2.0.token.count": "10",
  "connection.https://login.microsoftonline.com/hiltonprod.onmicrosoft.com/v2.0.token.count": "0",
  "adapter.HTMLPasswordProd.lookupAuthN.count": "787",
  "adapter.IdentifyFirst.lookupAuthN.count": "972",
  "adapter.OTP.lookupAuthN.count": "0",
  "adapter.kerberosadapter.lookupAuthN.count": "735",
  "adapter.pendingworkeraccessDenial.lookupAuthN.count": "0",
  "ds.JDBC.JDBC-00BF87DE97B02D59E8474F48781BE305FB9E01DD.max.connections": "50",
  "ds.LDAP.LDAP-384B5149EE40746B5E4FD11184B7677E01A103D9.max.connections": "100",
  "cpu.load": "5.82",
  "total.jvm.memory": "1073.742 MB",
  "total.physical.system.memory": "16.525 GB",
  ...
}]}
```

---

## Disclosed Information (Classified)

### 1. Internal Cluster Topology (8 nodes)

| Node | Role | Subnet |
|------|------|--------|
| 10.72.40.45:7300 | CLUSTERED_CONSOLE (PASSIVE) | 10.72.40.0/24 |
| 10.72.40.45:7200 | CLUSTERED_ENGINE | 10.72.40.0/24 |
| 10.72.40.46:7200 | CLUSTERED_ENGINE | 10.72.40.0/24 |
| 10.72.40.47:7200 | CLUSTERED_ENGINE | 10.72.40.0/24 |
| 10.72.40.47:7300 | CLUSTERED_CONSOLE | 10.72.40.0/24 |
| 10.80.40.170:7200 | CLUSTERED_ENGINE | 10.80.40.0/24 |
| 10.80.40.34:7200 | CLUSTERED_ENGINE | 10.80.40.0/24 |
| 10.80.40.32:7200 | CLUSTERED_ENGINE | 10.80.40.0/24 |

### 2. Azure AD Tenant Information

| Item | Value |
|------|-------|
| Tenant ID (confirmed) | `660292d2-cfd5-4a3d-b7a7-e8f7ee458a0a` |
| Primary domain | `hilton.onmicrosoft.com` |
| Production domain | `hiltonprod.onmicrosoft.com` |

Confirmed via `https://login.microsoftonline.com/hilton.onmicrosoft.com/v2.0/.well-known/openid-configuration` — issuer matches the disclosed tenant ID.

### 3. Authentication Adapter Names (Identity Flow Topology)

| Adapter | Authentication Type |
|---------|-------------------|
| `HTMLPasswordProd` | Username/password form (787 logins in last 300s window) |
| `IdentifyFirst` | Identifier-first flow (972 lookups) |
| `OTP` | One-time password / MFA |
| `kerberosadapter` | Kerberos/Windows SSO (735 lookups — active) |
| `pendingworkeraccessDenial` | Access denial for pending workers |

### 4. Database/LDAP Connection IDs (3 JDBC + 3 LDAP pools)
Internal data store identifiers exposed. LDAP pool `LDAP-592D5041` shows 46 errors — potential infrastructure issue indicator.

---

## Impact

1. **Infrastructure mapping**: 8 internal cluster node IPs enable lateral movement planning if attacker achieves initial access to 10.72.0.0/16 or 10.80.0.0/16 subnets via other vulnerabilities.

2. **Azure AD targeted phishing**: Knowing tenant ID `660292d2-cfd5-4a3d-b7a7-e8f7ee458a0a` and domains `hilton.onmicrosoft.com` / `hiltonprod.onmicrosoft.com` enables: user enumeration via `https://login.microsoftonline.com/{tenant}/openid/userinfo`, credential stuffing against Azure AD, crafting of convincing spear-phishing emails referencing known Hilton infrastructure.

3. **Authentication bypass research**: Adapter names reveal the exact auth flow — attacker knows that: Kerberos is used (Windows domain exists), OTP/MFA exists (can focus on MFA bypass chains), `HTMLPasswordProd` is the main credential adapter (direct attack target).

4. **Real-time operational data**: CPU/memory/response times reveal server load patterns useful for timing attacks or DoS planning.

---

## Recommendations

1. Restrict `/pf/heartbeat.ping` to internal network access only (WAF rule: block external IPs).
2. If public exposure is required, return only `{"status":"OK"}` without infrastructure details.
3. Move cluster IP enumeration to admin-only authenticated endpoint.
4. PingFederate admin guide recommends disabling public heartbeat or restricting its response data.

---

## References

- PingFederate Admin Guide: System → Server → Performance — Heartbeat configuration
- CWE-200: Information Exposure
- OWASP A05:2021 — Security Misconfiguration
