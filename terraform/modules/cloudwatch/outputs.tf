output "dashboard_name" {
  description = "Name of the CloudWatch Dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "ecs_cpu_alarm_arn" {
  description = "ARN of the ECS CPU High metric alarm"
  value       = aws_cloudwatch_metric_alarm.ecs_cpu_high.arn
}

output "ecs_memory_alarm_arn" {
  description = "ARN of the ECS Memory High metric alarm"
  value       = aws_cloudwatch_metric_alarm.ecs_memory_high.arn
}

output "alb_5xx_alarm_arn" {
  description = "ARN of the ALB 5XX metric alarm"
  value       = aws_cloudwatch_metric_alarm.alb_5xx_high.arn
}

output "rds_storage_alarm_arn" {
  description = "ARN of the RDS Storage Low metric alarm"
  value       = aws_cloudwatch_metric_alarm.rds_storage_low.arn
}
