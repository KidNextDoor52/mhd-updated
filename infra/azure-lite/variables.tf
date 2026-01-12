variable "location" {
  type    = string
  default = "eastus"
}

variable "resource_group_name" {
  type    = string
  default = "rg-mhd-azurelite"
}

variable "container_app_name" {
  type    = string
  default = "mhd-api"
}

variable "environment_name" {
  type    = string
  default = "mhd-aca-env"
}

variable "storage_account_name" {
  type        = string
  description = "Globally unique (3-24 lowercase letters/numbers)"
}

variable "acr_name" {
  type        = string
  description = "Globally unique (5-50 lowercase letters/numbers)"
}

variable "acr_sku" {
  type    = string
  default = "Basic"
}

variable "image" {
  type        = string
  description = "ACR image to deploy, e.g. <acr>.azurecr.io/mhd-api:latest"
}

variable "mongo_uri" {
  type      = string
  sensitive = true
}

variable "mongo_db" {
  type    = string
  default = "mhd_cloud"
}

variable "secret_key" {
  type      = string
  sensitive = true
}

variable "session_secret_key" {
  type      = string
  sensitive = true
}

variable "base_url" {
  type        = string
  description = "Public URL used to generate share links (set after first apply)"
  default     = ""
}
