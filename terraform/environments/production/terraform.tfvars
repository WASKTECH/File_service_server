environment               = "production"
project_name              = "wasktech-file-service"
aws_region                = "us-east-1"
vpc_cidr                  = "10.2.0.0/16"
availability_zones        = ["us-east-1a", "us-east-1b"]
enable_single_nat_gateway = false
db_instance_class        = "db.r6g.large"
db_multi_az              = true
ecs_cpu                   = 1024
ecs_memory                = 2048
ecs_desired_count         = 2
ecs_min_capacity          = 2
ecs_max_capacity          = 10
enable_custom_domain      = true
domain_name               = "api.wasktech.com"
route53_zone_id           = "Z0123456789ABCDEF0123" # Replace with actual Hosted Zone ID in AWS

tags = {
  Environment = "production"
  Owner       = "DevOps Team"
  CostCenter  = "Engineering-Prod"
  Compliance  = "Enterprise-Strict"
}
