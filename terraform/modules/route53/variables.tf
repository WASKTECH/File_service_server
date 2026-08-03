variable "domain_name" {
  description = "Domain name for the record (e.g. api.wasktech.com)"
  type        = string
}

variable "zone_id" {
  description = "Route53 Hosted Zone ID"
  type        = string
}

variable "alb_dns_name" {
  description = "ALB DNS Name"
  type        = string
}

variable "alb_zone_id" {
  description = "ALB Canonical Hosted Zone ID"
  type        = string
}
