# Threat Model Appendix (STRIDE)
**Project:** MHD Platform  
**Methodology:** STRIDE  
**Audience:** Security, Architecture, Compliance Review

---

## 1. Assets

- User identity & roles
- Health / performance data
- Uploaded documents
- Trained ML models
- Analytics outputs
- Infrastructure configuration

---

## 2. STRIDE Analysis

### S — Spoofing Identity
**Threat:** Attacker impersonates a user or service  
**Mitigations:**
- JWT validation
- Role enforcement at API boundary
- No shared credentials
- Secret injection via ACA

---

### T — Tampering
**Threat:** Data modified in transit or at rest  
**Mitigations:**
- TLS everywhere
- No direct client-to-database access
- Controlled pipeline write paths
- Immutable ML artifacts

---

### R — Repudiation
**Threat:** User denies performing an action  
**Mitigations:**
- Authenticated API calls
- Pipeline run tracking
- Model promotion audit trail

---

### I — Information Disclosure
**Threat:** Sensitive data exposed  
**Mitigations:**
- Private storage
- No public containers
- No secrets in images or repo
- Tenant isolation at app layer

---

### D — Denial of Service
**Threat:** Service unavailable  
**Mitigations:**
- Container autoscaling
- Stateless API design
- Graceful failure of background jobs

---

### E — Elevation of Privilege
**Threat:** User gains unauthorized capabilities  
**Mitigations:**
- Explicit role checks
- No admin endpoints without guards
- Separation of training vs serving roles

---

## 3. Attack → Mitigation Mapping

| Attack Scenario | Mitigation |
|----------------|-----------|
| Stolen token | Short-lived JWTs |
| API abuse | Role-based access |
| Storage scraping | Private containers |
| DB compromise | App-only access |
| CI/CD poisoning | Controlled registry |
| Insider misuse | Audit trails |

---

## 4. Failure Scenarios

### Identity Provider Failure
- Result: Auth unavailable
- Impact: Read-only or blocked access
- Recovery: Restore identity service

### Storage Outage
- Result: Ingest failures
- Impact: No data loss
- Recovery: Retry + alert

### Database Latency
- Result: Slow API
- Impact: Degraded UX
- Recovery: Scale + caching

---

## 5. Known Tradeoffs

- Tenant isolation enforced at application layer (not per-DB)
- No customer-managed encryption keys (yet)
- Simplified auth flows for MVP velocity

These are **conscious tradeoffs**, not gaps.

---

## 6. Future Security Enhancements (Planned)

- Per-tenant database or collection-level isolation
- Attribute-based access control (ABAC)
- Centralized SIEM
- Customer-managed keys (CMK)
- Automated security testing in CI

---

## 7. Summary

This threat model confirms:
- Risks are known
- Mitigations are explicit
- Residual risk is documented

The platform is suitable for regulated environments with clear upgrade paths.

