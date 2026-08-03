terraform {
  backend "s3" {
    bucket         = "wasktech-tfstate-staging-us-east-1"
    key            = "file-service/staging/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "wasktech-tflocks-staging"
    encrypt        = true
  }
}
