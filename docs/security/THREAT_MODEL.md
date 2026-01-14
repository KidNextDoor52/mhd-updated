# Threat Model (Executive)
**Project:** MHD Platform  
**Audience:** Directors, Security Leadership

---

## 1. Threat Modeling Approach

We apply **STRIDE-lite** focusing on:
- Realistic abuse
- High-impact threats
- Practical mitigations

---

## 2. Key Threats & Controls

| Threat | Control |
|-----|--------|
| Token theft | Short-lived JWTs |
| Data scraping | Private storage |
| Tenant crossover | App-layer isolation |
| Privilege escalation | Role checks |
| Replay attacks | Expiry + jti |
| Insider misuse | Audit logging |

---

## 3. Most Likely Abuse Cases

### Share Link Abuse
Mitigations:
- Expiry
- Email binding
- Category/file scope
- Audit logging

### Enumeration
Mitigations:
- ObjectId randomness
- Auth checks
- Rate limiting (planned)

### Injection
Mitigations:
- ODM usage
- No raw query execution
- Input normalization

---

## 4. Monitoring Signals

Watch for:
- Failed auth spikes
- Repeated denied downloads
- High-volume access from single identity
- Unexpected storage errors

---

## 5. Residual Risk

Accepted risks:
- App-layer tenant isolation
- MVP auth simplifications

These are documented and revisitable.

---

## 6. Summary

The platform:
- Knows its risks
- Controls them explicitly
- Logs what matters

This is a deliberate security posture.
