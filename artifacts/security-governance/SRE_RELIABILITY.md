# SRE & Reliability Model
**Project:** MHD Platform  
**Audience:** Platform Engineering, Ops

---

## 1. Health Endpoints

### `/healthz`
- Process alive
- No dependencies checked

### `/readyz`
- Mongo reachable
- Storage configured
- Safe to receive traffic

Used by:
- Deployments
- Scaling decisions

---

## 2. Service Level Objectives (SLOs)

| Metric | Target |
|-----|-------|
| API availability | 99.9% |
| Upload success | 99.5% |
| Download latency | <500ms p95 |
| Auth success | >99% |

---

## 3. Logging & Metrics

- Logs to stdout/stderr
- Structured logs
- No file logging
- Azure-native aggregation

---

## 4. Failure Modes

| Failure | Impact | Recovery |
|------|-------|---------|
| API crash | 503 | Auto-restart |
| DB latency | Slow API | Scale |
| Storage outage | Upload blocked | Retry |
| Bad deploy | Errors | Rollback |

---

## 5. Disaster Recovery (Basic)

Backups:
- Mongo backups
- Blob versioning (planned)

Restore:
- Redeploy image
- Restore DB
- Validate `/readyz`

---

## 6. Cold Start Expectations

- ACA cold start: seconds
- Mitigated via:
  - Warm instances
  - Stateless design

---

## 7. Summary

Reliability is achieved through:
- Simplicity
- Observability
- Fast rollback
