variable "environment" {
  description = "Execution environment (dev, staging, production)"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "container_port" {
  description = "Port exposed by the FastAPI container"
  type        = number
  default     = 8000
}

variable "db_port" {
  description = "Port exposed by PostgreSQL database"
  type        = number
  default     = 5432
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
