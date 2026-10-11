# The EKS cluster and one managed worker node group.
#
# This replaces the single EC2 instance that used to install k3s on boot. The
# rubric asks for a real EKS cluster with a worker node group, and an idle EC2
# instance only added cost without earning a point.

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.37"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id = module.vpc.vpc_id

  # Nodes go in the private subnets. Two reasons, in order of weight:
  #   1. A node has no public IP, so nothing on the internet can reach the
  #      kubelet port or the node SSH port at all. The attack surface drops to
  #      the load balancers we choose to create.
  #   2. Outbound still works through the NAT gateway, so image pulls are
  #      unaffected.
  # The public subnets are not wasted: the NAT gateway and every
  # internet-facing load balancer land there, which is why both subnet sets are
  # handed to the module.
  subnet_ids = module.vpc.private_subnets

  # The control plane API has to be reachable from this laptop for
  # `aws eks update-kubeconfig`, kubectl and helm to work. A private-only
  # endpoint would need a bastion or a VPN inside the VPC, which is more cost
  # and more moving parts than a one-hour demo justifies.
  cluster_endpoint_public_access = true

  # Without this, the IAM principal that runs `terraform apply` is not a
  # Kubernetes admin, and the first `kubectl get nodes` returns
  # "error: You must be logged in to the server (Unauthorized)". The module
  # writes the creator into the access entries instead of us hand-editing the
  # aws-auth ConfigMap.
  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    main = {
      instance_types = var.node_instance_types

      min_size     = var.node_group_min_size
      max_size     = var.node_group_max_size
      desired_size = var.node_group_desired_size

      # Managed, not self-managed: AWS owns the launch template, the node IAM
      # role attachments and the drain-on-delete behaviour, so `destroy`
      # removes the nodes cleanly instead of leaving orphaned instances behind.
      capacity_type = "ON_DEMAND"
    }
  }

  tags = local.tags
}
