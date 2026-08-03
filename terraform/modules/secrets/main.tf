resource "random_password" "db_password" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

locals {
  effective_db_password = var.db_password != "" ? var.db_password : random_password.db_password.result
}

# KMS Key for Secrets Manager
resource "aws_kms_key" "secrets" {
  description             = "KMS Key for ${var.project_name}-${var.environment} Secrets"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-secrets-kms-key"
    }
  )
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-${var.environment}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# Secrets Manager Secret for App & DB Credentials
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.project_name}/${var.environment}/app-secrets"
  description             = "Database credentials and application secrets for ${var.project_name} (${var.environment})"
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = 0

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-app-secrets"
    }
  )
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    POSTGRES_USER     = var.db_username
    POSTGRES_PASSWORD = local.effective_db_password
    POSTGRES_DB       = var.db_name
    DATABASE_URL      = "postgresql://${var.db_username}:${local.effective_db_password}@${var.db_host}:${var.db_port}/${var.db_name}"
    SECRET_KEY        = random_password.secret_key.result
  })
}
