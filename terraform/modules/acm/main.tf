resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = var.tags
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.zone_id != "" ? {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.zone_id
}

resource "aws_acm_certificate_validation" "cert" {
  count = var.wait_for_validation ? 1 : 0

  certificate_arn = aws_acm_certificate.cert.arn
  validation_record_fqdns = var.zone_id != "" ? [for record in aws_route53_record.cert_validation : record.fqdn] : [
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.resource_record_name
  ]

  timeouts {
    create = "45m"
  }
}
