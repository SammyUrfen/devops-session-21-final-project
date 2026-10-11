variable "aws_region" {
  description = "Region for every resource. ap-south-1 is the closest region, so node boot and image pulls are fastest from here."
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix and Project tag for every resource."
  type        = string
  default     = "mazehub"
}

variable "cluster_name" {
  description = "Name of the EKS cluster. It appears in the kubeconfig context and in the AWS console."
  type        = string
  default     = "mazehub-eks"
}

variable "cluster_version" {
  description = "Kubernetes minor version of the EKS control plane. 1.31 is the version the course reference pins."
  type        = string
  default     = "1.31"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC. A /16 leaves room for the four /24 subnets below plus later growth."
  type        = string
  default     = "10.21.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to spread the subnets across. Two is the EKS minimum, and the rubric needs two public subnets."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "EKS requires subnets in at least two availability zones."
  }
}

variable "public_subnet_cidrs" {
  description = "One public subnet CIDR for each availability zone. These hold the NAT gateway and the load balancers."
  type        = list(string)
  default     = ["10.21.101.0/24", "10.21.102.0/24"]
}

variable "private_subnet_cidrs" {
  description = "One private subnet CIDR for each availability zone. The worker nodes live here."
  type        = list(string)
  default     = ["10.21.1.0/24", "10.21.2.0/24"]
}

variable "node_instance_types" {
  description = "Instance types for the managed node group. t3.medium (2 vCPU, 4 GiB) is the smallest size that fits the EKS system pods plus MazeHub."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_group_min_size" {
  description = "Smallest node count. Two nodes let a pod reschedule when one node goes away."
  type        = number
  default     = 2
}

variable "node_group_max_size" {
  description = "Largest node count. Three caps the cost of a scale-out during the demo window."
  type        = number
  default     = 3
}

variable "node_group_desired_size" {
  description = "Node count at creation time."
  type        = number
  default     = 2
}

variable "ecr_image_retention_count" {
  description = "Number of images each ECR repository keeps. Older images expire, so storage cost stays flat."
  type        = number
  default     = 10
}
