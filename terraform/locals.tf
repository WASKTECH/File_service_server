locals {
  common_tags = merge(
    var.tags,
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "WASKTECH/File_service_server"
    }
  )

  container_image = "${module.ecr.repository_url}:latest"

  # Route53 in this account can create ACM validation records immediately.
  # External DNS requires a second apply after the validation CNAME is added.
  attach_certificate = var.enable_custom_domain && (var.route53_zone_id != "" || var.attach_acm_certificate)
}
