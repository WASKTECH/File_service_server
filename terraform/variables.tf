variable "environment" {
  description = "Execution environment (dev, staging, production)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "project_name" {
  description = "Project name prefix for all infrastructure resources"
  type        = string
  default     = "wasktech-file-service"
}

variable "aws_region" {
  description = "Target AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR Block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of Availability Zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "enable_single_nat_gateway" {
  description = "Enable single NAT gateway to optimize costs in non-production environments"
  type        = bool
  default     = true
}

variable "db_instance_class" {
  description = "RDS PostgreSQL Instance Class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ RDS Deployment"
  type        = bool
  default     = false
}

variable "ecs_cpu" {
  description = "ECS Fargate Task CPU units"
  type        = number
  default     = 512
}

variable "ecs_memory" {
  description = "ECS Fargate Task Memory (MB)"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "ECS Desired Task Count"
  type        = number
  default     = 2
}

variable "ecs_min_capacity" {
  description = "ECS Min Auto Scaling Capacity"
  type        = number
  default     = 2
}

variable "ecs_max_capacity" {
  description = "ECS Max Auto Scaling Capacity"
  type        = number
  default     = 10
}

variable "enable_custom_domain" {
  description = "Request an ACM certificate for domain_name and expose HTTPS on the ALB once attached"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Custom domain for ACM and the API (e.g. fileservice.wasktechnologies.com)"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route53 Hosted Zone ID. Leave empty when the CNAME is managed outside this AWS account."
  type        = string
  default     = ""
}

variable "attach_acm_certificate" {
  description = "Attach the ACM certificate to the ALB HTTPS listener. Set true after ACM DNS validation records exist. Ignored when route53_zone_id is set (validation is automatic)."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Custom tags map"
  type        = map(string)
  default     = {}
}
