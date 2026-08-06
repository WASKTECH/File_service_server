terraform {
  backend "s3" {
    bucket  = "myapp-files-prod-wask"
    key     = "terraform-state/file-service/dev/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
