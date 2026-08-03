output "cluster_id" {
  description = "ID of the ECS Cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Name of the ECS Cluster"
  value       = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  description = "ARN of the ECS Cluster"
  value       = aws_ecs_cluster.main.arn
}

output "service_name" {
  description = "Name of the ECS Service"
  value       = aws_ecs_service.main.name
}

output "service_id" {
  description = "ID of the ECS Service"
  value       = aws_ecs_service.main.id
}

output "task_definition_arn" {
  description = "ARN of the Task Definition"
  value       = aws_ecs_task_definition.main.arn
}

output "task_definition_family" {
  description = "Family of the Task Definition"
  value       = aws_ecs_task_definition.main.family
}

output "log_group_name" {
  description = "Name of the CloudWatch Log Group for ECS"
  value       = aws_cloudwatch_log_group.ecs.name
}
