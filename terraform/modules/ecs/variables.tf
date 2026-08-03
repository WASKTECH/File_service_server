variable "environment" {
  description = "Execution environment (dev, staging, production)"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "container_image" {
  description = "ECR image URL with tag"
  type        = string
}

variable "cpu" {
  description = "Fargate CPU units (256 = 0.25 vCPU, 512 = 0.5 vCPU, 1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Fargate Memory in MB (1024 = 1 GB, 2048 = 2 GB)"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum capacity for auto scaling"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Maximum capacity for auto scaling"
  type        = number
  default     = 10
}

variable "private_app_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security Group ID for ECS tasks"
  type        = string
}

variable "target_group_arn" {
  description = "ALB Target Group ARN"
  type        = string
}

variable "ecs_execution_role_arn" {
  description = "ARN of ECS Task Execution Role"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN of ECS Task Role"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 storage bucket"
  type        = string
}

variable "secrets_arn" {
  description = "ARN of AWS Secrets Manager Secret containing app secrets"
  type        = string
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
