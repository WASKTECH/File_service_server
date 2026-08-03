output "fqdn" {
  description = "Fully qualified domain name of the API record"
  value       = aws_route53_record.api_a.fqdn
}
