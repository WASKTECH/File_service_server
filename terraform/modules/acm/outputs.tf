output "certificate_arn" {
  description = "ARN of the ACM certificate (validated when wait_for_validation is true)"
  value       = var.wait_for_validation ? aws_acm_certificate_validation.cert[0].certificate_arn : aws_acm_certificate.cert.arn
}

output "certificate_status" {
  description = "ACM certificate status (PENDING_VALIDATION, ISSUED, etc.)"
  value       = aws_acm_certificate.cert.status
}

output "validation_records" {
  description = "DNS records required to validate the ACM certificate when Route53 is not used"
  value = [
    for dvo in aws_acm_certificate.cert.domain_validation_options : {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  ]
}
