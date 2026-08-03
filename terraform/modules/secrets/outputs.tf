output "secret_arn" {
  description = "ARN of the Secrets Manager Secret"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "secret_name" {
  description = "Name of the Secrets Manager Secret"
  value       = aws_secretsmanager_secret.app_secrets.name
}

output "db_password" {
  description = "The database password used"
  value       = local.effective_db_password
  sensitive   = true
}

output "kms_key_arn" {
  description = "ARN of the Secrets Manager KMS Key"
  value       = aws_kms_key.secrets.arn
}
