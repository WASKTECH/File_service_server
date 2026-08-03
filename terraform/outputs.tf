output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS Name"
  value       = module.alb.alb_dns_name
}

output "api_url" {
  description = "Full URL to access the File Service API"
  value       = var.enable_custom_domain ? "https://${var.domain_name}" : "http://${module.alb.alb_dns_name}"
}

output "ecr_repository_url" {
  description = "ECR Repository URL for pushing Docker images"
  value       = module.ecr.repository_url
}

output "s3_bucket_name" {
  description = "S3 Storage Bucket Name"
  value       = module.s3.bucket_id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL Endpoint"
  value       = module.rds.db_endpoint
}

output "ecs_cluster_name" {
  description = "ECS Cluster Name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS Service Name"
  value       = module.ecs.service_name
}

output "cloudwatch_dashboard_name" {
  description = "CloudWatch Dashboard Name"
  value       = module.cloudwatch.dashboard_name
}

output "secrets_manager_arn" {
  description = "Secrets Manager Secret ARN"
  value       = module.secrets.secret_arn
}
