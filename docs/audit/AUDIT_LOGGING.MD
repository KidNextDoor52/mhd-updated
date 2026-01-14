# Audit Logging & Event Tracking
**Project:** MHD (My Health Data) Platform  
**Audience:** Security, Compliance, Architecture  
**Goal:** Ensure all sensitive actions are attributable, reviewable, and auditable.

---

## 1. Purpose

Audit logging in MHD exists to answer four questions:

- **Who** did something
- **What** they did
- **When** it occurred
- **Whether** it succeeded or failed

Audit logs are designed for **security review, incident response, and compliance**, not debugging.

---

## 2. Audit Event Schema

All audit events follow a consistent structure.

```json
{
  "ts": "2026-01-13T22:14:03Z",
  "action": "create_share_link",
  "ok": true,
  "err": null,
  "actor": {
    "user_id": "65a1f3...",
    "username": "rmccray",
    "role": "user"
  },
  "meta": {
    "recipient": "coach@example.com",
    "scope": "file",
    "file_ids": ["65a2c9..."]
  },
  "source": "api"
}
```
---

## 2a. Required Fields

**Field	Description**

**Field**                    **Description**
ts	                         UTC timestamp
action	                     Canonical action name
ok	                         Boolean success indicator
err	                         Error summary (if any)
actor	                       Identity performing action
meta	                       Action-specific metadata
source	                     Entry point (web, api, job)

---

## 3. Required Audited Events

The following events must always be logged:

**Authentication**

- login_success

- login_failed

- token_revoked

- refresh_token_used

**Authorization**

- permission_denied

- role_violation_attempt

**Data Access**

- upload_file

- download_file

- shared_download

- failed_shared_download

**Sharing**

- create_share_link

- revoke_share_link

- expired_share_link_access

**Administrative**

- admin_override

- config_change

- secret_rotation

---

## 4. Storage & Access

- Audit events are stored in MongoDB (audit_events)

- Collection is write-only from application code

- No client-side access

Read access limited to:

- Security review

- Incident response

- Compliance export

Indexes:

- ts

- action

---

## 5. Retention Policy
**Environment**	       **Retention**
Dev	                   30 days
Staging	               90 days
Production	           365 days

Expired logs are deleted automatically via scheduled job.

---

## 6. Incident Support

Audit logs are the primary artifact for:

- Security investigations

- Data access disputes

- Regulatory inquiries

- Internal reviews

Logs are immutable once written.

---

## 7. Non-Goals

❌ Debug logging
❌ Performance tracing
❌ User-facing activity history

These belong to separate systems.

---

## 8. Summary

Audit logging in MHD provides:

- Full accountability

- Clear forensic trail

- Minimal operational overhead

It is intentionally boring — and reliable.