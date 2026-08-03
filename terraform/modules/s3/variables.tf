variable "environment" {
  description = "Execution environment (dev, staging, production)"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "bucket_name" {
  description = "Name of the S3 bucket. If empty, auto-generated based on project and environment"
  type        = string
  default     = ""
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS in S3 presigned upload/download requests"
  type        = list(string)
  default     = ["*"]
}

variable "versioning_status" {
  description = "S3 Versioning configuration (Enabled or Suspended)"
  type        = string
  default     = "Enabled"
}

variable "expiration_days" {
  description = "Days after which non-current versions are deleted (0 to disable)"
  type        = number
  default     = 90
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
