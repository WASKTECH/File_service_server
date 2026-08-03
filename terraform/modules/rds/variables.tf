variable "environment" {
  description = "Execution environment"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "db_subnet_group_name" {
  description = "Name of DB Subnet Group"
  type        = string
}

variable "rds_security_group_id" {
  description = "Security Group ID for RDS"
  type        = string
}

variable "engine_version" {
  description = "PostgreSQL Engine Version"
  type        = string
  default     = "16.3"
}

variable "instance_class" {
  description = "RDS Instance Class"
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Allocated storage size in GB"
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Maximum storage limit for storage autoscaling in GB"
  type        = number
  default     = 100
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment for high availability"
  type        = bool
  default     = false
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "filedb"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "fileapi"
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "backup_retention_period" {
  description = "Days to retain automated backups"
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Prevent accidental deletion of RDS instance"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
