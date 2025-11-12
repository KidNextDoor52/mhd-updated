MHD – My Health Data (Core App + ML Platform)

MHD is a FastAPI-based platform for athlete health & performance data. It supports secure document intake, structured forms, equipment & weight-room tracking, dashboards, and production-grade ML for:

Injury Risk Early Warning (binary classification)

Session Quality Auto-Scoring (regression / ordinal)

The stack is containerized, reproducible (MLflow), observable (Mongo + aggregates), and portable across dev (Docker, Azurite/MinIO) and cloud (Azure/AWS).

Contents

Quick Start (Dev)

Architecture (At a Glance)

Services

Repository Layout

Environment Variables

APIs (Auth, App, ML, Metrics, Dashboard)

Data Contracts (Mongo Collections)

ML Pipelines

Background Jobs

Observability & Monitoring

Security & Compliance

CI/CD & Releases

Cloud Deployment Notes

Troubleshooting

Glossary

Quick Start (Dev)
# 1) Clone & enter
git clone <repo-url>
cd mhd-updated/mhd-nlp-docker

# 2) Create .env (see template below)
cp .env.example .env
# fill in secrets for Google OAuth (optional in dev), session/JWT keys, etc.

# 3) Bring up the stack
docker compose -f docker-compose.dev.yml up -d --build

# 4) Health check
curl http://localhost:8000/health    # => {"status":"ok"}

# 5) Open UIs
# App (FastAPI routes + templates)
http://localhost:8000
# Mongo Express
http://localhost:8081
# MLflow Tracking UI
http://localhost:5000
# MinIO Console
http://localhost:9001  (access: MINIO_ROOT_USER/MINIO_ROOT_PASSWORD)


Minimal .env.example

# App
SESSION_SECRET_KEY=dev-session-secret
SECRET_KEY=dev-jwt-secret
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REFRESH_TOKEN_COOKIE=mhd_refresh_token
COOKIE_SECURE=false

# Mongo
MONGO_URL=mongodb://mongo:27017/mhd

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
PROMOTE_MIN_AUC=0.75
MODEL_NAME=mhd_logreg

# Object Storage (MinIO S3)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET_MODELS=mhd-models
S3_BUCKET_DATA=mhd-data

# Redis (RQ)
REDIS_URL=redis://redis:6379/0

# Google OAuth (optional in dev)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

Architecture (At a Glance)
+--------------------------+        +-----------------------+
|        FastAPI           | <----> |        MongoDB        |
|  - Auth, forms, uploads  |        |  - users/sessions/... |
|  - Dashboards            |        +-----------------------+
|  - ML APIs (/pipeline,   |
|    /predict, /metrics)   |        +-----------------------+
+------------+-------------+  --->  |        MLflow         |
             |                      |  - runs, metrics,     |
             |                      |    artifacts, registry|
             |                      +-----------------------+
             v
+--------------------------+        +-----------------------+
|         RQ Worker        |  --->  |        MinIO          |
|  - async training jobs   |        |  - data & model store |
+--------------------------+        +-----------------------+
             ^
             |
+------------+-------------+
|      Redis (queues)      |
+--------------------------+

Dev cloud emulators:
- MinIO (S3) simulates object storage
- Azurite simulates Azure Blob storage (optional sidecar)

Services
Service	Port	Purpose
backend (FastAPI + Uvicorn)	8000	App + APIs, serves static/templates
worker (pipeline utils)	—	ML utilities (feature build, etc.)
rq-worker (Redis Queue)	—	Background training/inference jobs
mlflow	5000	Experiment tracking & Model Registry
mlflow-db (Postgres)	5433→5432	MLflow backend store
mongo	27017	Application data
mongo-express	8081	UI for Mongo
minio	9000/9001	S3 API / Web console
azurite	10000–10002	Azure Blob/Queue/Table emulator
redis	6379	RQ queues, caching
Repository Layout
app/
  auth.py                # JWT, refresh, helpers
  authz.py               # role checks (viewer/trainer/admin)
  db/                    # Mongo handles & helpers
  db_init.py             # indexes
  features/              # feature builders (injury_risk, session_quality)
  labeling/              # label builders
  monitoring/            # middleware, nightly aggregates, drift
  pipelines/
    orchestrator.py      # run_training_job(), registry promotion
    steps/
      deid.py            # PHI-stripping utilities
      train.py           # train_basic(), RF for quality
      validate.py        # metric gates
      deploy.py          # local manifest + MLflow Registry promote
      quality.py         # schema checks (e.g., Great Expectations stubs)
  routes/
    auth.py, auth_google.py, connect.py
    dashboard.py, models.py, predict.py
    pipeline.py, pipeline_ingest.py, pipeline_async.py
    events.py, forms.py, library.py, profile.py, share.py, upload.py, weightroom.py, training.py
  templates/             # Jinja2 pages (dashboard/trainer, etc.)
  static/                # CSS/JS/assets

docker-compose.dev.yml
Dockerfile
requirements.txt
docs/README.md           # (this file)

Environment Variables
Var	Required	Default	Notes
SESSION_SECRET_KEY	✓	—	Starlette session signing
SECRET_KEY	✓	—	JWT signing
JWT_ALG		HS256	JWT algorithm
MONGO_URL	✓	mongodb://mongo:27017/mhd	Mongo DSN
MLFLOW_TRACKING_URI	✓	http://mlflow:5000	MLflow server
PROMOTE_MIN_AUC		0.75	Gate for injury model
MODEL_NAME		mhd_logreg	MLflow model name
S3_ENDPOINT_URL	✓	http://minio:9000	MinIO endpoint
S3_BUCKET_MODELS	✓	mhd-models	Model bucket
S3_BUCKET_DATA	✓	mhd-data	Data bucket
REDIS_URL	✓	redis://redis:6379/0	RQ queue
GOOGLE_CLIENT_ID			OAuth (optional dev)
GOOGLE_CLIENT_SECRET			OAuth (optional dev)
APIs (Auth, App, ML, Metrics, Dashboard)
Auth

POST /auth/signup – form: username, password, email

POST /auth/token – OAuth2 password; returns access_token, sets cookies

GET /auth/google/login → GET /auth/google/callback – Google OAuth

POST /auth/forgot-password, POST /auth/reset-password

POST /auth/logout

App (selected)

GET / – index

GET /dashboard – user dashboard

GET /dashboard/trainer (trainer role) – ML trainer view (charts, top-risk)

Other modules: /equipment, /weightroom, /upload, /forms, /share, etc.

ML – Pipeline & Serving

POST /pipeline/train – enqueue training job (RQ); returns job_id

GET /pipeline/status/{job_id} – job progress/completion

POST /pipeline/ingest – (optional) pull CSV from MinIO/Azurite → preprocess → trigger training

GET /models/current – manifest for current Production model

GET /models/compare?runs=a,b – compare two MLflow runs

POST /predict/risk – returns {score∈[0,1], run_id, model_version, …}

POST /predict/session_score – returns {score∈[0,5], run_id, model_version, …}

Metrics & Monitoring (trainer role)

GET /metrics/risk/summary – risk buckets + 7-day trend

GET /metrics/session/summary – score histogram (last 24h)

GET /secure-metrics – protected health of app/ML (latency, error rate, drift flags)

Role access (via app/authz.py)

viewer – read-only predictions

trainer – predictions + dashboard + metrics

admin – training/promotion/config

Data Contracts (Mongo Collections)
Collection	Document Shape (key fields)	Purpose
users	{ username, email, password?, role, provider?, created_at }	Auth/roles
sessions	{ athlete_id, ts, work, adherence, rpe, coach_rating?, vitals?, nlp: {...}, clean: {...} }	Training sessions; includes NLP/cleaning metadata
features	{ athlete_id, ts, version, x: {...} }	Engineered features (versioned)
labels	{ athlete_id, ts, horizon_days, y }	Ground truth labels
predictions	{ use_case, athlete_id, ts, x_version, run_id, model_version, score, meta? }	Online/offline predictions (traceable)
metric_aggregates	{ date, use_case, buckets, trends, kpis }	Nightly aggregates for dashboards
revoked_tokens	{ jti, sub, exp, reason }	JWT refresh revocation list
refresh_tokens	{ jti, sub, exp, revoked, created_at }	Server-side refresh token tracking
audit_logs	{ when, who, action, metadata }	Training/promotion/user actions (PHI-safe)

NLP/cleaning linkage: Feature builders read sessions.nlp (topics, sentiment, entities) and sessions.clean (normalized units, outlier flags). These tags become part of features.x and are logged to MLflow as feature_version + params.

ML Pipelines
1) Injury Risk Early Warning (Binary)

Goal: Flag elevated risk for next 7–14 days.

Signals: rolling load (volume/intensity), HR/BP trends, recovery markers, prior injuries, adherence, NLP topics from notes.

Model: Logistic Regression (class_weight="balanced")

Metrics: val_auc, val_pr_auc, precision_at_k (e.g., top 10%), recall

Promotion Gate: val_auc ≥ PROMOTE_MIN_AUC → MLflow Registry: Production

Serving: POST /predict/risk

2) Session Quality Auto-Scoring (Regression/Ordinal)

Goal: Predict 1–5 quality/effort from structured + NLP data.

Signals: sets/reps/tempo, RPE, rest timing, adherence; NLP (sentiment/topics) from notes.

Model: Random Forest Regressor (optionally ordinal calibration)

Metrics: val_mae, val_spearman (ρ), calibration plot

Serving: POST /predict/session_score

Reproducibility

Each run logs feature_version, horizon, params, metrics, and a model artifact.

Each prediction stores run_id + model_version for traceability back to MLflow.

Background Jobs

Training enqueue: POST /pipeline/train → puts job on Redis (RQ)

Worker: rq-worker pulls and executes run_training_job() (in app/pipelines/orchestrator.py)

Nightly aggregates: app/monitoring/aggregate.py writes metric_aggregates (risk buckets, 7-day trends)

Drift monitors (optional starter): KS/PSI checks on feature distributions; file retrain if threshold exceeded

Observability & Monitoring

App latency & errors: app/monitoring/middleware.py logs per-route timings & status codes

Model health:

/secure-metrics (trainer/admin) – live health, latest run_id, latency, error rates

metric_aggregates – daily summaries for trainer dashboard

MLflow UI – compare runs, visualize metrics/artifacts

Audit:

app/utils/logger.log_activity() records who trained/promoted with run_id, feature_version, data hash

Security & Compliance

AuthN: JWT access + refresh cookies (/auth/token, Google OAuth optional)

AuthZ: app/authz.require_role("viewer"|"trainer"|"admin") used on sensitive routes

De-identification: app/pipelines/steps/deid.py runs before training to strip PHI from feature frames

PHI scope: Only the minimal, de-identified fields used in ML; raw docs remain in controlled storage

Traceability: Predictions store run_id/model_version; MLflow logs feature versions & params

Secrets: Use .env in dev; Key Vault / Secrets Manager in cloud

Transport: Enforce HTTPS and COOKIE_SECURE=true in production

CI/CD & Releases

Unit/Integration tests: steps, /pipeline/train, /predict/*

GitHub Actions (suggested):

Build Docker images

Run tests

Push images on main

Versioning:

App semver (tags)

Models via MLflow Model Registry (Staging → Production with approvals)

Features via feature_version param

Cloud Deployment Notes

Azure: AKS or App Service for FastAPI; Azure Blob (replace MinIO); Azure Postgres for MLflow; Azure Cache for Redis

AWS: ECS/EKS/Fargate; S3 (replace MinIO); RDS Postgres for MLflow; ElastiCache Redis

IaC: Keep env-specific Terraform under infra/azure and infra/aws

Same code, different env: only switch env vars & storage endpoints

Troubleshooting
Symptom	Likely Cause / Fix
Empty reply from server on /health	Backend container crashed. docker compose logs backend for Python tracebacks.
NameError: df is not defined in orchestrator.py	Ensure deidentify(df) is called after df is created, not at module import time.
rq: executable file not found or rq ... package cannot be directly executed	Use python -m rq worker ... in the worker command.
Click warnings: duplicate --serializer / -S	Remove duplicated flags in the RQ entrypoint.
MLflow warning about sklearn versions	Autologging warns when sklearn is out of tested range. Prefer sklearn ≤ 1.5.1 or upgrade MLflow.
ModuleNotFoundError: steps	Use absolute imports (from app.pipelines.steps.train import ...) or ensure PYTHONPATH=/app.
Can’t pip install azure	The azure meta-pkg is deprecated. Install specific libs (e.g., azure-storage-blob).
MinIO image tag not found	Use minio/minio:latest (dev) or a valid release tag; ensure compose pulls succeed.
Glossary

AUC – Area under ROC curve (binary quality)

PR-AUC – Area under Precision–Recall (rare positives)

MAE – Mean Absolute Error (regression quality)

Precision@K – Precision of top-K ranked predictions

RQ – Redis Queue, lightweight async jobs

MLflow – Run tracking + Model Registry

MinIO – S3-compatible object storage (local dev)

De-id – De-identification (remove PHI)

Feature Version – Tag for feature schema used by a model run

Example Calls
# Train (async)
curl -X POST http://localhost:8000/pipeline/train
# => {"status":"started","job_id":"<uuid>"}

# Poll status
curl http://localhost:8000/pipeline/status/<job_id>

# Predict injury risk (single row example)
curl -X POST http://localhost:8000/predict/risk \
  -H "Content-Type: application/json" \
  -d '{"rows":[{"athlete_id":"A1","age":29,"bp":124,"hr":70,"load7":320,"rpe":6,"topic_knee":1,"sentiment":-0.2}]}'
# => {"predictions":[{"score":0.31,"run_id":"...","model_version":3}]}

# Trainer metrics
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/metrics/risk/summary

Notes for Contributors

Keep new routes role-guarded using require_role() where appropriate.

Any new model must:

Log to MLflow with feature_version, params, metrics, artifacts

Save to Registry (Staging/Production) or write a local manifest in dev

Serve via /predict/<use_case> and store predictions with run_id + model_version

Add tests for: feature builders, validators, training, serving, and metrics endpoints.
