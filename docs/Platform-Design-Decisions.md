# Platform Design Decisions – MHD

## Environment Strategy
- Environments are configuration-driven (local vs cloud).
- Cloud runtime uses Azure Container Apps with environment variables and secrets.
- No code changes are required between environments.

## Compute
- Azure Container Apps chosen for managed ingress, scaling, and secure defaults.
- System-assigned managed identity used where supported.
- Stateless API design.

## Networking
- Public ingress only at the application layer.
- No public database exposure.
- Platform assumes private-by-default internal communication.

## Data Layer
- Azure Cosmos DB (Mongo API) used for operational data.
- Azure Blob Storage used for raw and processed artifacts.
- Storage backend abstracted to allow future migration.

## Security Posture (Initial)
- Identity-first access where possible.
- Secrets injected via Container App secrets, not source code.
- Audit and index initialization handled at application startup.

## Rationale
Design prioritizes:
- Clear blast radius
- Environment parity
- Operational simplicity
- Future enterprise hardening

Platform Design Decisions
Overview

This document captures the foundational design decisions for the MHD platform, focusing on scalability, security, isolation, and operability. These decisions prioritize enterprise cloud patterns over short-term convenience.

1. Environments

Defined environments

dev – active development, experimentation, rapid iteration

prod – stable, hardened, production workloads

Key differences

Area	Dev	Prod
Scaling	Minimal	Auto-scaling enabled
Logging retention	Short	Extended
Data	Test / synthetic	Real / regulated
Access	Broader dev access	Strict RBAC

Why

Clear separation reduces blast radius

Mirrors enterprise SDLC practices

Enables compliance controls in prod without slowing dev

2. Tenant Model

Model chosen:
👉 Logical multi-tenancy with strong isolation

Isolation mechanisms

Tenant-scoped identifiers enforced at the application layer

Database collections / partitions keyed by tenant

Blob storage paths segmented by tenant

Role-based access checks on every request

Why

Cost-efficient for early stages

Scales horizontally

Matches SaaS patterns used by healthcare, analytics, and internal platforms

3. Subscription & Resource Organization

Azure hierarchy

Management Group (future)

Subscription: mhd-platform-dev

Subscription: mhd-platform-prod

Within each subscription

Resource Group per workload domain:

rg-platform-core

rg-platform-data

rg-platform-apps

Why

Clear ownership boundaries

Easier cost tracking

Enables policy enforcement at the right scope

4. Networking Strategy

Principles

Private by default

Explicit ingress only

No public data services

Design

Single VNet per environment

Subnets:

ingress (App Gateway / Front Door integration)

app (Container Apps / AKS)

data (Cosmos DB, Storage, SQL via private endpoints)

Connectivity

Private Endpoints for:

Storage

Cosmos DB

Key Vault

Public access disabled wherever supported

Why

Reduces attack surface

Matches Zero Trust assumptions

Aligns with regulated-data expectations

5. Identity & Access Management

Identity provider

Microsoft Entra ID

Workload identity

Managed Identities for:

API services

Background jobs

Data access

Human access

Entra ID groups:

Platform Admins

Developers

Read-Only / Audit

Authorization

Azure RBAC at:

Subscription

Resource Group

Resource level (when needed)

Why

Eliminates shared secrets

Enforces least privilege

Auditable and revocable access

6. Build & Deployment Strategy

Container build

Azure Container Registry

Centralized image builds

Tagged with:

latest

commit SHA (future)

Deployment

Azure Container Apps

Revision-based deployments

Environment variables injected via:

Secrets

Managed identity references

Why

Repeatable deployments

Clear rollback capability

Separation of code and configuration

7. Guiding Principles

Security is structural, not optional

Identity is the control plane

Isolation beats complexity

Operability matters as much as features

Every decision must survive scale


