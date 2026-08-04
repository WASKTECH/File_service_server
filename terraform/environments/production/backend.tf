terraform {
  backend "s3" {
    bucket  = "myapp-files-prod-wask"
    key     = "terraform-state/file-service/production/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
