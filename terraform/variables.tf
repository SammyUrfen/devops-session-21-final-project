variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for resources."
  type        = string
  default     = "incidentboard"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.21.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block of the public subnet (must sit inside vpc_cidr)."
  type        = string
  default     = "10.21.1.0/24"
}

variable "instance_type" {
  description = "EC2 size. t3.small (2 GiB) is the smallest size where k3s plus this app fits."
  type        = string
  default     = "t3.small"
}

variable "ssh_allowed_cidr" {
  description = "Only this CIDR may reach port 22. Use your own public IP as x.x.x.x/32."
  type        = string

  validation {
    condition     = can(cidrhost(var.ssh_allowed_cidr, 0)) && var.ssh_allowed_cidr != "0.0.0.0/0"
    error_message = "ssh_allowed_cidr must be a valid CIDR and must not be 0.0.0.0/0."
  }
}

variable "key_name" {
  description = "Name of an existing EC2 key pair for SSH. Leave null to launch without one."
  type        = string
  default     = null
}
