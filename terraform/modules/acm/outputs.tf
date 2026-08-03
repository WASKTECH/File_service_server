output "certificate_arn" {
  description = "ARN of the validated ACM Certificate"
  value       = aws_acm_certificate_validation.cert.certificate_arn
}
