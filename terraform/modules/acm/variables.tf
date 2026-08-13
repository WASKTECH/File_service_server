variable "domain_name" {
  description = "Primary domain name for ACM SSL Certificate (e.g. fileservice.wasktechnologies.com)"
  type        = string
}

variable "zone_id" {
  description = "Route53 Hosted Zone ID for DNS validation. Leave empty when DNS is managed outside this AWS account."
  type        = string
  default     = ""
}

variable "wait_for_validation" {
  description = "Wait until ACM issues the certificate. Set true only after DNS validation records exist (always true when zone_id is set)."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags map"
  type        = map(string)
  default     = {}
}
