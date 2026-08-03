variable "environment" {
  description = "Execution environment"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 file storage bucket"
  type        = string
}

variable "s3_kms_key_arn" {
  description = "ARN of the KMS Key used for S3 bucket encryption"
  type        = string
}

variable "secrets_arn" {
  description = "ARN of Secrets Manager secret"
  type        = string
}

variable "secrets_kms_key_arn" {
  description = "ARN of KMS key used for Secrets Manager"
  type        = string
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
