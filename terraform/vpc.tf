# The network MazeHub runs in: two public subnets and two private subnets, one
# pair in each of two availability zones.
#
# Why the registry module instead of hand-written resources: a working EKS
# network is a VPC, four subnets, an internet gateway, a NAT gateway, three
# route tables, four associations and an EIP. The module builds that graph in
# the order EKS needs, and it already knows the subnet tag contract below.

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = "${var.project}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs

  # The worker nodes sit in the private subnets, and they still have to reach
  # the internet outbound: the kubelet pulls container images, registers with
  # the control plane endpoint and fetches the EKS add-ons. A private subnet
  # with no NAT gateway produces nodes stuck in NotReady, which is the usual
  # first failure of a hand-rolled EKS network.
  enable_nat_gateway = true

  # Cost, not availability. One NAT gateway costs about USD 0.056 each hour.
  # One for each zone would triple that for a cluster that only has to live for
  # a 75 minute screenshot window. The trade-off accepted: if zone 1a goes
  # down, the nodes in 1b lose outbound access. Acceptable for a demo, wrong for
  # production, where single_nat_gateway should be false.
  single_nat_gateway = true

  # The AWS load balancer controller and the in-tree service controller find
  # subnets by tag, not by name or by route table. Without these two tags a
  # Service of type LoadBalancer fails with "could not find any suitable
  # subnets", and the Ingress for Module 8 never gets an address.
  #   kubernetes.io/role/elb          -> put internet-facing load balancers here
  #   kubernetes.io/role/internal-elb -> put internal load balancers here
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  # DNS hostnames are required before EKS will accept the VPC: the kubelet
  # resolves the private DNS name of its own node to register itself.
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = local.tags
}
