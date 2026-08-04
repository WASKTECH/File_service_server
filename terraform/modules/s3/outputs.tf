output "bucket_id" {
  description = "The name of the main S3 bucket"
  value       = aws_s3_bucket.main.id
}

output "bucket_arn" {
  description = "The ARN of the main S3 bucket"
  value       = aws_s3_bucket.main.arn
}

output "kms_key_arn" {
  description = "The ARN of the KMS Key used for S3 encryption"
  value       = ""
}

output "kms_key_id" {
  description = "The ID of the KMS Key used for S3 encryption"
  value       = ""
}

output "logs_bucket_id" {
  description = "The name of the access logs S3 bucket"
  value       = aws_s3_bucket.logs.id
}
