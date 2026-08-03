variable "environment" {
  description = "Execution environment"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "fileapi"
}

variable "db_password" {
  description = "Database master password. If empty, a random password will be generated"
  type        = string
  default     = ""
  sensitive   = true
}

variable "db_host" {
  description = "Database host address"
  type        = string
  default     = ""
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "filedb"
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
