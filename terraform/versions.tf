# Version pins live here, away from the resources, so an upgrade touches one file.
#
# Why pin the AWS provider to the 5.x line and not 6.x: the EKS module 20.37.x
# series declares a `< 6.0.0` constraint on hashicorp/aws. Terraform refuses to
# init when the root module asks for 6.x, so the root and the child must agree.
terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95"
    }
  }
}
