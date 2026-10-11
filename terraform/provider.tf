provider "aws" {
  region = var.aws_region

  # default_tags stamps every taggable resource, including the ones the VPC and
  # EKS modules create for us. That matters for cost: the AWS bill can be split
  # by the Project tag, so the cost of this capstone window is auditable after
  # the fact rather than guessed at.
  default_tags {
    tags = local.tags
  }
}

locals {
  # One tag set, referenced by the provider and by every module. Keeping it in a
  # local instead of repeating the map stops the three copies from drifting.
  tags = {
    Project   = var.project
    Owner     = "SammyUrfen"
    ManagedBy = "terraform"
    Session   = "21"
  }
}
