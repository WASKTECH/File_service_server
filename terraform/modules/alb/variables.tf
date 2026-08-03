variable "environment" {
  description = "Execution environment"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security Group ID for ALB"
  type        = string
}

variable "certificate_arn" {
  description = "ACM SSL Certificate ARN for HTTPS listener (Optional)"
  type        = string
  default     = ""
}

variable "health_check_path" {
  description = "Path for container health checks"
  type        = string
  default     = "/api/v1/health"
}

variable "logs_bucket_id" {
  description = "S3 bucket ID for ALB access logs (Optional)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
