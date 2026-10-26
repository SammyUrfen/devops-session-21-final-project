# Evidence

One file for each screenshot the rubric asks for. The module column is the module in
`GRADING.md`. Nothing here is source code. The application, the chart, the workflow and the
Terraform files are in the repository root.

| Module | What the rubric asks for | File |
|---|---|---|
| M1 | The running application in a browser | [m01-app-gallery.png](m01-app-gallery.png) |
| M1 | The player view with the solved path | [m01-app-play-with-solution.png](m01-app-play-with-solution.png) |
| M2 | `pytest -v`, all tests pass | [m02-pytest-39-passed.png](m02-pytest-39-passed.png) |
| M3 | The commit history, 10 commits or more | [m03-commit-history.png](m03-commit-history.png) |
| M4 | `docker compose up --build`, the build | [m04-compose-up-build-1.png](m04-compose-up-build-1.png) |
| M4 | `docker compose up --build`, the 3 services up | [m04-compose-up-build-2.png](m04-compose-up-build-2.png) |
| M4 | The browser at `http://localhost:3000` | [m01-app-gallery.png](m01-app-gallery.png) |
| M5 | A green pipeline run, 6 jobs | [m05-pipeline-green.png](m05-pipeline-green.png) |
| M5 | The GHCR package page with SHA tags | [m05-ghcr-sha-tags.png](m05-ghcr-sha-tags.png) |
| M6 | The Trivy step in a pipeline run | [m06-trivy-scan-step.png](m06-trivy-scan-step.png) |
| M6 | The Trivy result, 1 MEDIUM and 0 HIGH | [m06-trivy-findings.png](m06-trivy-findings.png) |
| M7 | `terraform plan`, the start | [m07-plan-start.png](m07-plan-start.png) |
| M7 | `terraform plan`, 62 to add | [m07-plan-summary.png](m07-plan-summary.png) |
| M7 | `terraform apply`, 62 added | [m07-apply-complete.png](m07-apply-complete.png) |
| M7 | The AWS Console, the VPC and its 4 subnets | [m07-console-vpc-subnets.png](m07-console-vpc-subnets.png) |
| M7 | The AWS Console, the EKS node group | [m07-console-eks-node-group.png](m07-console-eks-node-group.png) |
| M7 | The 2 EKS worker nodes, both Ready | [m07-eks-nodes-ready.png](m07-eks-nodes-ready.png) |
| M7 | `terraform destroy`, 62 destroyed | [m07-destroy-complete.png](m07-destroy-complete.png) |
| M8 | `kubectl apply -f k8s/namespace.yaml` | [m08-namespace-apply.png](m08-namespace-apply.png) |
| M8 | `helm upgrade --install` | [m08-helm-upgrade-install.png](m08-helm-upgrade-install.png) |
| M8 | `helm list -n mazehub` | [m08-helm-list.png](m08-helm-list.png) |
| M8 | 2 replicas for the backend and the frontend | [m08-get-deploy-replicas.png](m08-get-deploy-replicas.png) |
| M8 | `kubectl get svc -n mazehub` | [m08-get-svc.png](m08-get-svc.png) |
| M8 | `kubectl get pods -n mazehub`, all Running | [m08-get-pods-running.png](m08-get-pods-running.png) |
| M8 | The Ingress rules, `/` and `/api` | [m08-ingress-routes.png](m08-ingress-routes.png) |
| M8 | The application through the Ingress host | [m08-app-through-ingress.png](m08-app-through-ingress.png) |
| M9 | The `/metrics` endpoint | [m09-metrics-endpoint.png](m09-metrics-endpoint.png) |
| M9 | The Prometheus Targets page, 2 of 2 up | [m09-prometheus-targets-up.png](m09-prometheus-targets-up.png) |
| M9 | The Grafana dashboard, 5 panels with data | [m09-grafana-dashboard.png](m09-grafana-dashboard.png) |
| M10 | The recorded demo, 4 minutes | [../../demo/mazehub-demo.mp4](../../demo/mazehub-demo.mp4) |

## The demo recording

The video and the slide deck are in [`../../demo/`](../../demo/). That folder has its own index
with the timings.
