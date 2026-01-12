# Security Model & Trust Boundaries
**Project:** MHD (My Health Data) Platform  
**Author:** Robert McCray  
**Scope:** Cloud-native, multi-tenant data platform (FastAPI + Azure Container Apps + Cosmos DB + Azure Blob)

---

## 1. Security Philosophy (Executive Summary)

The MHD platform is designed with **security as a structural property**, not a bolt-on feature.

Key principles:
- Identity-first security (Zero Trust)
- Least-privilege by default
- Explicit trust boundaries
- No shared credentials
- No implicit network trust
- No direct data plane exposure

Security decisions prioritize **blast-radius containment**, **auditability**, and **operational clarity**.

---

## 2. Trust Boundaries (High-Level)

### External Boundary
- Public internet traffic terminates at **Azure Container Apps ingress**
- TLS enforced
- No direct access to data services

### Application Boundary
- FastAPI services run inside a managed container environment
- Services authenticate users via JWT
- Internal service logic never trusts request context blindly

### Data Boundary
- Cosmos DB (Mongo API) accessed only via application identity
- Blob Storage accessed only via managed identity or connection string
- No public containers or buckets

### Control Plane vs Data Plane
- Control plane (Azure Resource Manager, ACR, ACA) isolated from runtime
- Data plane access requires runtime identity and explicit permissions

---

## 3. Identity & Access Model

### Users
- Authenticated via application auth (JWT-based)
- Role-based access enforced at API boundary (`require_role`)
- No shared users across tenants

### Services
- Managed identities (where supported)
- Environment-scoped secrets via ACA secrets
- No secrets committed to source control

### Admin Operations
- No direct database access from public network
- Admin actions logged and auditable

---

## 4. Threat Surfaces

| Surface | Risk | Mitigation |
|------|------|----------|
| Public API | Unauthorized access | JWT auth + role checks |
| Blob storage | Data exfiltration | Private access only |
| Database | Tenant crossover | App-enforced isolation |
| Secrets | Leakage | ACA secret store |
| CI/CD | Supply chain | ACR + controlled builds |

---

## 5. Data Protection

- Encryption at rest (platform-managed)
- Encryption in transit (TLS)
- Explicit container/bucket separation:
  - Raw data
  - Processed data
  - ML artifacts
- No cross-container writes without explicit code paths

---

## 6. Logging & Audit

- Authentication events logged
- Pipeline executions tracked
- Model training and promotion auditable
- Future extension: centralized log analytics

---

## 7. What This Platform Intentionally Does NOT Allow

These are **explicit design decisions**, not missing features.

❌ No direct database connections from clients  
❌ No public blob containers  
❌ No shared credentials across services  
❌ No cross-tenant data access  
❌ No admin actions without auditability  
❌ No long-lived secrets in code or images  
❌ No implicit trust based on network location  

---

## 8. Security Posture Summary

This platform enforces:
- Strong identity boundaries
- Minimal attack surface
- Clear ownership of access paths
- Explicit failure modes

Security is enforced **by architecture**, not policy alone.
