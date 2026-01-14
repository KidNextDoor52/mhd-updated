# Governance & Control Framework
**Project:** MHD Platform  
**Audience:** Architecture, Compliance, Leadership

---

## 1. Governance Goals

The governance model ensures:

- Predictable change
- Controlled access
- Auditable decisions
- Reduced operational risk

Governance is enforced through **process + architecture**, not policy documents alone.

---

## 2. Data Retention & Deletion

### Retention Rules
| Data Type | Retention |
|--------|----------|
| Upload metadata | Life of account |
| Uploaded files | User-controlled |
| Audit logs | 30–365 days |
| Share links | Auto-expire |

### Deletion
- User-initiated deletion supported
- Orphaned blobs periodically cleaned
- Deletions logged as audit events

---

## 3. Least Privilege & Separation of Duties

### Principles
- Users access only their tenant data
- Admins cannot access raw PHI casually
- No single role can:
  - Upload data
  - Approve access
  - Disable auditing

---

## 4. Secrets Management

### Policy
- **No secrets in repo**
- **No secrets in container images**
- **No secrets in `.env` for prod**

### Implementation
- Azure Container Apps secret store
- Secret references injected at runtime
- Rotation does not require redeploy

---

## 5. Configuration Policy

| Rule | Enforcement |
|----|------------|
| No prod secrets in env files | CI checks |
| Versioned deployments | Image tags |
| Immutable revisions | ACA revisions |
| Explicit startup config | `/version` endpoint |

---

## 6. Change Management

### Deployment Rules
- Every change = new image tag
- Every image tag = new ACA revision
- Rollback via revision switch

### Required Metadata
- Git commit SHA
- Build timestamp
- Image tag

---

## 7. Access Reviews

Quarterly checklist:
- Review admin users
- Review share link usage
- Review audit exceptions
- Review failed auth attempts

---

## 8. Incident Triggers

Immediate review required if:
- Repeated denied downloads
- Excessive token failures
- Unusual data access volume
- Storage access errors

---

## 9. Summary

Governance in MHD is:
- Lightweight
- Enforceable
- Observable

It scales with the platform.