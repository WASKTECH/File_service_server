terraform {
  backend "s3" {
    bucket         = "wasktech-tfstate-production-us-east-1"
    key            = "file-service/production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "wasktech-tflocks-production"
    encrypt        = true
  }
}
