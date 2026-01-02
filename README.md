# MHD: Secure Multi-Tenant Health Data Platform
> **Reference Architecture for HIPAA-Compliant Microservices**

## 🏗️ Architectural Overview
This platform is a production-ready, cloud-native ecosystem designed to give individuals and organizations secure ownership and portability of sensitive health records.

### 🔒 Security-By-Design Highlights
* **Identity-First Access:** Enforced OIDC/OAuth2 authentication via Microsoft Entra ID with tenant-scoped JWT validation.
* **Network Isolation:** All application workloads and data stores are isolated within private subnets via VNet encapsulation and Private Endpoints.
* **Zero-Trust Ingestion:** Automated OCR-to-FHIR pipelines that validate and de-identify data at the edge before storage.

## 🛠️ Tech Stack
* **Compute:** Azure Kubernetes Service (AKS)
* **Data Tier:** Snowflake (Governed Analytics), Azure SQL, Cosmos DB
* **Secrets:** Azure Key Vault for certificate rotation and secret management

## 🚀 How to Deploy (Containerized Workflow)

### 1. Prerequisites
* **Azure CLI & Kubectl:** Configured for the target subscription.
* **Secret Management:** Ensure `az keyvault` contains the necessary OIDC provider client secrets.

### 2. Environment Configuration
Create a `.env` file from the provided template to configure the FHIR validation endpoint and Snowflake analytics sink.

### 3. Local Validation (Docker Compose)
Verify the microservices mesh locally before pushing to the cloud:
```bash
docker-compose up --build

### 4. AKS Cluster Deployment
Deploy the validated images to the Azure Kubernetes Service (AKS) private cluster using Helm:

Bash

helm install mhd-platform ./charts/mhd-platform --set tenantId=$AZURE_TENANT_ID
