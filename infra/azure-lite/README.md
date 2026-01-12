# Azure-Lite Deployment (Terraform)

This folder provisions a minimal, low-cost Azure deployment for MHD:

- Azure Container Apps (runs the API container)
- Azure Storage Account + Blob containers (raw/processed/uploads)
- Azure Key Vault (secrets)
- Log Analytics Workspace (logs)

This is intended as a portfolio-grade "platform layer" artifact.

## Required tools
- Azure CLI
- Terraform

## Quick start
1) Login
```bash
az login
az account show
