# Terraform — MazeHub AWS infrastructure

This directory builds the AWS infrastructure for MazeHub: a VPC with two public and two private
subnets, an EKS cluster with one managed worker node group, and two ECR repositories.

It covers rubric module M7, 15 points.

**State of the run.** `init`, `fmt`, `validate` and `plan` all ran and passed. `apply` and `destroy`
are **not run yet: the user runs these in the screenshot window.**

| Command | State |
|---|---|
| `terraform version` | Ran. v1.16.1 |
| `terraform init` | Ran. Clean |
| `terraform fmt -recursive` | Ran. No file needed a change |
| `terraform validate` | Ran. `Success! The configuration is valid.` |
| `terraform plan` | Ran. `Plan: 62 to add, 0 to change, 0 to destroy.` No error, no warning |
| `terraform apply` | Not run yet: the user runs these in the screenshot window |
| `terraform destroy` | Not run yet: the user runs these in the screenshot window |

Raw output is under `.evidence/` at the repository root: `terraform-checks.txt` and
`terraform-plan.txt`. That folder is git-ignored.

---

## Architecture

```text
                          internet
                              |
                      +---------------+
                      |    internet   |
                      |    gateway    |
                      +-------+-------+
                              |
  VPC 10.21.0.0/16            |
  +---------------------------+--------------------------------+
  |                                                            |
  |  ap-south-1a                      ap-south-1b              |
  |  +-----------------------+        +----------------------+  |
  |  | public 10.21.101.0/24 |        | public 10.21.102.0/24| |
  |  |  NAT gateway          |        |                      | |
  |  |  load balancers       |        |  load balancers      | |
  |  +----------+------------+        +----------------------+  |
  |             | (outbound only)                               |
  |  +----------v------------+        +----------------------+  |
  |  | private 10.21.1.0/24  |        | private 10.21.2.0/24 | |
  |  |  EKS worker nodes     |        |  EKS worker nodes    | |
  |  +-----------------------+        +----------------------+  |
  +------------------------------------------------------------+

  EKS control plane (AWS managed, outside the VPC, public endpoint on)
  ECR: mazehub-backend, mazehub-frontend
```

Two availability zones, because EKS refuses a cluster whose subnets sit in only one zone, and
because the rubric asks for at least two public subnets.

The worker nodes sit in the **private** subnets. No node has a public IP, so nothing on the
internet can reach a kubelet port directly. The nodes still pull images outbound through the NAT
gateway in the public subnet.

### Why the subnet tags matter

The Kubernetes load balancer controller finds subnets by tag, not by name and not by route table.

| Tag | On | Meaning |
|---|---|---|
| `kubernetes.io/role/elb = 1` | the two public subnets | Put an internet-facing load balancer here |
| `kubernetes.io/role/internal-elb = 1` | the two private subnets | Put an internal load balancer here |

Without the public tag, a Service of type `LoadBalancer` fails with "could not find any suitable
subnets", and the module 8 Ingress never receives an address.

---

## Files

| File | Holds |
|---|---|
| `versions.tf` | Terraform and provider version pins |
| `provider.tf` | The AWS provider, the region, and the common `tags` local |
| `variables.tf` | Every input, each with a description and a default |
| `vpc.tf` | The `terraform-aws-modules/vpc/aws` module, pinned `~> 5.8` |
| `eks.tf` | The `terraform-aws-modules/eks/aws` module, pinned `~> 20.37` |
| `ecr.tf` | Two image repositories and their lifecycle policy |
| `outputs.tf` | Cluster name, endpoint, VPC id, subnet ids, node group, kubeconfig command |
| `terraform.tfvars.example` | A copy-and-edit template. It holds no real credential |

The provider stays on the `5.x` line. The EKS module `20.37.x` declares `< 6.0.0` on
`hashicorp/aws`, so a root module that asks for `6.x` cannot init at all.

---

## Variables

Every variable has a default, so an empty `terraform.tfvars` works.

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `aws_region` | string | `ap-south-1` | Region for every resource |
| `project` | string | `mazehub` | Name prefix and `Project` tag |
| `cluster_name` | string | `mazehub-eks` | EKS cluster name, also the kubeconfig context |
| `cluster_version` | string | `1.31` | Kubernetes minor version of the control plane |
| `vpc_cidr` | string | `10.21.0.0/16` | VPC address range |
| `availability_zones` | list(string) | `["ap-south-1a", "ap-south-1b"]` | Zones to spread subnets across. Two minimum |
| `public_subnet_cidrs` | list(string) | `["10.21.101.0/24", "10.21.102.0/24"]` | The two public subnets |
| `private_subnet_cidrs` | list(string) | `["10.21.1.0/24", "10.21.2.0/24"]` | The two private subnets |
| `node_instance_types` | list(string) | `["t3.medium"]` | Worker size. The smallest that fits the system pods plus MazeHub |
| `node_group_min_size` | number | `2` | Smallest node count |
| `node_group_max_size` | number | `3` | Largest node count. It caps the cost of a scale-out |
| `node_group_desired_size` | number | `2` | Node count at creation |
| `ecr_image_retention_count` | number | `10` | Images each repository keeps |

---

## Cost

Rates are on-demand `ap-south-1`, October 2026. Treat them as close, not exact.

| Piece | Count | Each hour | Why it costs what it does |
|---|---|---|---|
| EKS control plane | 1 | USD 0.10 | A flat per-cluster charge. It runs whether or not a node exists |
| `t3.medium` worker node | 2 | USD 0.0528 each, USD 0.1056 together | On-demand compute |
| NAT gateway | 1 | USD 0.056 | An hourly charge plus about USD 0.045 for each GB processed |
| Elastic IP for the NAT | 1 | USD 0.005 | Charged while attached |
| 20 GiB gp3 root volume | 2 | about USD 0.002 together | USD 0.0924 for each GB each month |
| Internet gateway, route tables, subnets, security groups | many | USD 0.00 | Free |
| ECR storage | 2 repos | about USD 0.00 | USD 0.10 for each GB each month. Two small images round to nothing |
| **Total** | | **about USD 0.27 each hour** | |

A load balancer created later by a Kubernetes Service adds about USD 0.0225 each hour on top.

Creation takes about 15 minutes. Destruction takes about 15 minutes. A 75 minute window costs
about **USD 0.35**.

> **Run `terraform destroy` when the screenshots are done.**
> Nothing here stops on its own. A cluster left running overnight costs about USD 6.50, and a
> cluster left for a month costs about USD 195. Destroy is part of the rubric, worth 2 points, and
> the destroy output is a required screenshot.

---

## Command order

The IAM user needs rights first. EKS creation calls `iam:CreateRole`, `iam:AttachRolePolicy`,
`iam:PassRole`, `eks:*` and `logs:*`. Attach `AdministratorAccess` to `SammyUrfen-CLI` for the
window, then remove it.

```bash
# 0. Confirm which identity is in play.
aws sts get-caller-identity

cd terraform

# 1. Download the provider and the two registry modules.
terraform init

# 2. Format and check. Both are offline and free.
terraform fmt -recursive
terraform validate

# 3. Read the plan. It adds 62 resources and creates nothing.
terraform plan

# 4. Create the infrastructure. About 15 minutes. THIS COSTS MONEY.
terraform apply

# 5. Point kubectl at the new cluster.
aws eks update-kubeconfig --region ap-south-1 --name mazehub-eks

# 6. Confirm the two nodes joined and are Ready.
kubectl get nodes

# 7. Take the screenshots: the AWS console VPC page, the EKS cluster page.

# 8. Remove everything. About 15 minutes. Do not skip this.
terraform destroy
```

Step 5 is also printed by the `update_kubeconfig_command` output, with the real region and cluster
name filled in.

### Screenshots module 7 needs

1. The `terraform plan` output.
2. The AWS console, the VPC with its two public subnets, in `ap-south-1`.
3. The AWS console, the EKS cluster and its `main` node group.
4. The `terraform destroy` output, ending in `Destroy complete!`.

---

## Notes

- `terraform.tfvars`, `.terraform/` and every `*.tfstate` file are git-ignored. No state and no
  credential is committed.
- `.terraform.lock.hcl` **is** committed on purpose, so a later `init` resolves the same provider
  versions.
- State is local. A single operator on one laptop does not need a remote backend, and an S3 plus
  DynamoDB backend would add cost and setup for no gain here. A team would need one.
- There is one NAT gateway, not one for each zone. That is a deliberate cost trade-off. If zone
  `1a` fails, the nodes in `1b` lose outbound access. Set `single_nat_gateway = false` for
  production.
