environment               = "dev"
project_name              = "wasktech-file-service"
aws_region                = "us-east-1"
vpc_cidr                  = "10.0.0.0/16"
availability_zones        = ["us-east-1a", "us-east-1b"]
enable_single_nat_gateway = true
db_instance_class        = "db.t4g.micro"
db_multi_az              = false
ecs_cpu                   = 512
ecs_memory                = 1024
ecs_desired_count         = 1
ecs_min_capacity          = 1
ecs_max_capacity          = 4
enable_custom_domain      = false
domain_name               = "dev-api.wasktech.com"
route53_zone_id           = ""

tags = {
  Environment = "dev"
  Owner       = "DevOps Team"
  CostCenter  = "Engineering-Dev"
}
