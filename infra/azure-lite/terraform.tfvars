location            = "eastus"
resource_group_name = "rg-mhd-azurelite"

# MUST be globally unique
storage_account_name = "mhdrobazurelite26" # change if taken

# MUST be globally unique
acr_name = "acrrobazurelite26" # change if taken

container_app_name = "mhd-api"
environment_name   = "mhd-aca-env"

# Image reference (we'll push later)
image = "acrrobazurelite26.azurecr.io/mhd-api:latest"

mongo_db = "mhd_cloud"

# Leave base_url blank first apply
base_url = ""
