variable "environment" {
  description = "Execution environment"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "max_image_count" {
  description = "Maximum number of images to retain in ECR repository"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
