# Networking Module (VPC, Subnets, IGW, NAT, Route Tables, S3 Endpoint)
module "networking" {
  source = "./modules/networking"

  environment               = var.environment
  project_name              = var.project_name
  vpc_cidr                  = var.vpc_cidr
  availability_zones        = var.availability_zones
  enable_single_nat_gateway = var.enable_single_nat_gateway

  tags = local.common_tags
}

# Security Module (ALB, ECS, and RDS Security Groups)
module "security" {
  source = "./modules/security"

  environment  = var.environment
  project_name = var.project_name
  vpc_id       = module.networking.vpc_id

  tags = local.common_tags
}

# ECR Module (Private Docker Repository)
module "ecr" {
  source = "./modules/ecr"

  environment  = var.environment
  project_name = var.project_name

  tags = local.common_tags
}

# S3 Module (Multi-Tenant File Storage & Access Logs)
module "s3" {
  source = "./modules/s3"

  environment  = var.environment
  project_name = var.project_name

  tags = local.common_tags
}

# Secrets Module (AWS Secrets Manager for DB & App Secrets)
module "secrets" {
  source = "./modules/secrets"

  environment  = var.environment
  project_name = var.project_name
  db_host      = module.rds.db_address
  db_name      = "filedb"
  db_username  = "fileapi"

  tags = local.common_tags
}

# IAM Module (ECS Task Execution & Task Roles)
module "iam" {
  source = "./modules/iam"

  environment         = var.environment
  project_name        = var.project_name
  s3_bucket_arn       = module.s3.bucket_arn
  s3_kms_key_arn      = module.s3.kms_key_arn
  secrets_arn         = module.secrets.secret_arn
  secrets_kms_key_arn = module.secrets.kms_key_arn

  tags = local.common_tags
}

# RDS Module (PostgreSQL 16 Engine)
module "rds" {
  source = "./modules/rds"

  environment           = var.environment
  project_name          = var.project_name
  db_subnet_group_name  = module.networking.db_subnet_group_name
  rds_security_group_id = module.security.rds_security_group_id
  instance_class        = var.db_instance_class
  multi_az              = var.db_multi_az
  db_password           = module.secrets.db_password
  deletion_protection   = var.environment == "production"

  tags = local.common_tags
}

# ACM Module (Optional SSL Certificate)
module "acm" {
  count  = var.enable_custom_domain ? 1 : 0
  source = "./modules/acm"

  domain_name = var.domain_name
  zone_id     = var.route53_zone_id

  tags = local.common_tags
}

# ALB Module (Application Load Balancer)
module "alb" {
  source = "./modules/alb"

  environment           = var.environment
  project_name          = var.project_name
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  alb_security_group_id = module.security.alb_security_group_id
  certificate_arn       = var.enable_custom_domain ? module.acm[0].certificate_arn : ""
  logs_bucket_id        = module.s3.logs_bucket_id

  tags = local.common_tags
}

# Route53 Module (Optional DNS Alias Record)
module "route53" {
  count  = var.enable_custom_domain ? 1 : 0
  source = "./modules/route53"

  domain_name  = var.domain_name
  zone_id      = var.route53_zone_id
  alb_dns_name = module.alb.alb_dns_name
  alb_zone_id  = module.alb.alb_zone_id
}

# ECS Module (Fargate Cluster, Task Def, Service & Auto Scaling)
module "ecs" {
  source = "./modules/ecs"

  environment             = var.environment
  project_name            = var.project_name
  aws_region              = var.aws_region
  container_image         = local.container_image
  cpu                     = var.ecs_cpu
  memory                  = var.ecs_memory
  desired_count           = var.ecs_desired_count
  min_capacity            = var.ecs_min_capacity
  max_capacity            = var.ecs_max_capacity
  private_app_subnet_ids  = module.networking.private_app_subnet_ids
  ecs_security_group_id   = module.security.ecs_security_group_id
  target_group_arn        = module.alb.target_group_arn
  ecs_execution_role_arn  = module.iam.ecs_execution_role_arn
  ecs_task_role_arn       = module.iam.ecs_task_role_arn
  s3_bucket_name          = module.s3.bucket_id
  secrets_arn             = module.secrets.secret_arn

  tags = local.common_tags
}

# CloudWatch Module (Dashboard & Metric Alarms)
module "cloudwatch" {
  source = "./modules/cloudwatch"

  environment         = var.environment
  project_name        = var.project_name
  ecs_cluster_name    = module.ecs.cluster_name
  ecs_service_name    = module.ecs.service_name
  alb_suffix          = module.alb.alb_arn
  target_group_suffix = module.alb.target_group_arn
  rds_db_identifier   = module.rds.db_instance_id

  tags = local.common_tags
}
