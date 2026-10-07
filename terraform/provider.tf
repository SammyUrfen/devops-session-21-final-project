terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Every resource gets these tags, so the bill and the console show what Terraform made.
  default_tags {
    tags = {
      Project   = var.project
      Session   = "21"
      ManagedBy = "Terraform"
    }
  }
}
