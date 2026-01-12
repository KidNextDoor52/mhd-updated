terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
  }
}

provider "azurerm" {
  features {}
}

# -----------------------------
# Resource Group
# -----------------------------
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# -----------------------------
# Log Analytics (for Container Apps logs)
# -----------------------------
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-mhd-azurelite"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# -----------------------------
# Container Apps Environment
# -----------------------------
resource "azurerm_container_app_environment" "aca_env" {
  name                       = var.environment_name
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
}

# -----------------------------
# Storage Account + Containers
# -----------------------------
resource "azurerm_storage_account" "sa" {
  name                     = var.storage_account_name
  location                 = azurerm_resource_group.rg.location
  resource_group_name      = azurerm_resource_group.rg.name
  account_tier             = "Standard"
  account_replication_type = "LRS"

  allow_nested_items_to_be_public = false
}

resource "azurerm_storage_container" "raw" {
  name                  = "mhd-raw"
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "processed" {
  name                  = "mhd-processed"
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}

# -----------------------------
# Azure Container Registry (ACR)
# -----------------------------
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = var.acr_sku
  admin_enabled       = false
}

# -----------------------------
# Container App (Public Ingress)
# -----------------------------
resource "azurerm_container_app" "api" {
  name                         = var.container_app_name
  container_app_environment_id = azurerm_container_app_environment.aca_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = "system"
  }

  template {
    container {
      name   = "api"
      image  = var.image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "ENV"
        value = "cloud"
      }

      env {
        name  = "MONGO_URI"
        value = var.mongo_uri
      }

      env {
        name  = "MONGO_DB"
        value = var.mongo_db
      }

      env {
        name  = "SECRET_KEY"
        value = var.secret_key
      }

      env {
        name  = "SESSION_SECRET_KEY"
        value = var.session_secret_key
      }

      env {
        name  = "STORAGE_BACKEND"
        value = "azure"
      }

      env {
        name  = "AZURE_BLOB_CONN_STR"
        value = azurerm_storage_account.sa.primary_connection_string
      }

      env {
        name  = "AZURE_CONTAINER_RAW"
        value = azurerm_storage_container.raw.name
      }

      env {
        name  = "AZURE_CONTAINER_PROCESSED"
        value = azurerm_storage_container.processed.name
      }

      dynamic "env" {
        for_each = var.base_url == "" ? [] : [1]
        content {
          name  = "BASE_URL"
          value = var.base_url
        }
      }
    }
  }
}

# Allow the Container App identity to pull images from ACR
resource "azurerm_role_assignment" "aca_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.api.identity[0].principal_id
}