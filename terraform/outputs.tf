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
  value = var.enable_custom_domain ? (
    local.attach_certificate ? "https://${var.domain_name}" : "http://${var.domain_name}"
  ) : "http://${module.alb.alb_dns_name}"
}

output "acm_validation_records" {
  description = "ACM DNS validation records to create at the DNS provider when Route53 is not used"
  value       = var.enable_custom_domain ? module.acm[0].validation_records : []
}

output "acm_certificate_status" {
  description = "ACM certificate status when a custom domain is enabled"
  value       = var.enable_custom_domain ? module.acm[0].certificate_status : "disabled"
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
