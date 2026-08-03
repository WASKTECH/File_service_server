variable "domain_name" {
  description = "Primary domain name for ACM SSL Certificate (e.g. api.wasktech.com)"
  type        = string
}

variable "zone_id" {
  description = "Route53 Hosted Zone ID for DNS validation"
  type        = string
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
