variable "environment" {
  description = "Execution environment"
  type        = string
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "wasktech-file-service"
}

variable "ecs_cluster_name" {
  description = "ECS Cluster Name"
  type        = string
}

variable "ecs_service_name" {
  description = "ECS Service Name"
  type        = string
}

variable "alb_suffix" {
  description = "ALB Suffix (e.g. app/wasktech-file-service-prod-alb/12345)"
  type        = string
}

variable "target_group_suffix" {
  description = "Target Group Suffix (e.g. targetgroup/wasktech-file-service-prod-tg/67890)"
  type        = string
}

variable "rds_db_identifier" {
  description = "RDS DB Instance Identifier"
  type        = string
}

variable "sns_alarm_topic_arn" {
  description = "SNS Topic ARN for CloudWatch Alarms (Optional)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
