terraform {
  backend "s3" {
    bucket         = "wasktech-tfstate-dev-us-east-1"
    key            = "file-service/dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "wasktech-tflocks-dev"
    encrypt        = true
  }
}
