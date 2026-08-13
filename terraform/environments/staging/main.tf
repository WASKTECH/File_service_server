module "root" {
  source = "../../"

  environment               = var.environment
  project_name              = var.project_name
  aws_region                = var.aws_region
  vpc_cidr                  = var.vpc_cidr
  availability_zones        = var.availability_zones
  enable_single_nat_gateway = var.enable_single_nat_gateway
  db_instance_class         = var.db_instance_class
  db_multi_az               = var.db_multi_az
  ecs_cpu                   = var.ecs_cpu
  ecs_memory                = var.ecs_memory
  ecs_desired_count         = var.ecs_desired_count
  ecs_min_capacity          = var.ecs_min_capacity
  ecs_max_capacity          = var.ecs_max_capacity
  enable_custom_domain      = var.enable_custom_domain
  domain_name               = var.domain_name
  route53_zone_id           = var.route53_zone_id
  attach_acm_certificate    = var.attach_acm_certificate
  tags                      = var.tags
}

output "api_url" {
  value = module.root.api_url
}

output "alb_dns_name" {
  value = module.root.alb_dns_name
}

output "acm_validation_records" {
  value = module.root.acm_validation_records
}

output "acm_certificate_status" {
  value = module.root.acm_certificate_status
}

output "ecr_repository_url" {
  value = module.root.ecr_repository_url
}

output "s3_bucket_name" {
  value = module.root.s3_bucket_name
}

output "rds_endpoint" {
  value = module.root.rds_endpoint
}
