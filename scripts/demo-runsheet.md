# Demo runsheet — MazeHub

A 13 minute live demo. The rubric item it answers is M10: "commit a change, watch the pipeline run,
see the deployment update." Steps 9 to 12 are that loop, and they carry 3 of the 5 points. Keep them
even if everything else gets cut.

## Before the room

Open four terminals and three browser tabs, so nothing starts cold.

| # | Terminal | Prepared with |
|---|---|---|
| T1 | Compose | `cd devops-session-21-final-project`, stack already up |
| T2 | Cluster | `export KUBECONFIG=$HOME/.kube/s21.yaml` |
| T3 | Pipeline watch | `gh run watch` ready to type |
| T4 | Terraform | `cd terraform` |

| Tab | URL |
|---|---|
| App | <http://localhost:3000> (3001 if another server holds 3000) |
| Prometheus | <http://127.0.0.1:42110/targets?search=mazehub> |
| Grafana | <http://127.0.0.1:42120/d/mazehub/mazehub?from=now-30m&to=now> |

Check three things: `docker compose ps` shows three services, `kubectl get pods -n mazehub` shows
five Running, and both port-forwards answer. Add `192.168.58.2 mazehub.local` to `/etc/hosts` if you
want the Ingress demo in a browser instead of curl.

---

## 1. The app, 90 seconds

Browser, the App tab.

```text
Say: MazeHub is a maze gallery. The server generates every maze from a seed, proves it is solvable
with a breadth-first search before it stores it, and the player walks it on a canvas.
```

1. Show the gallery and the stat tiles.
2. Click **Play** on an EASY maze. Move with the arrow keys. Point at the move counter.
3. Click **Show solution**. Say: that amber path is the same breadth-first search, served from
   `/api/mazes/{id}/solution`.
4. Walk to the bottom right cell. The green Solved bar appears. Say: the browser posted a completion
   with the real move count.
5. Open **Completed**. The run is in the table.

## 2. The structural guard, 90 seconds

Sidebar, **Draw**.

1. Click the outer edge of a top-row cell. Read the refusal out loud: the outside of the maze must
   stay closed.
2. Press **Check** with nothing open: no path yet.
3. Open walls from the top left to the bottom right. Press **Check**: it names the path length.
4. Publish it. The gallery switches to the Community tab.

```text
Say: the browser runs that check for speed, not for trust. The server runs five checks again:
size, value range, a closed border, neighbours agreeing about a shared wall, and a real path.
A client cannot store an unsolvable maze.
```

## 3. Tests, 60 seconds

T1:

```bash
cd backend && .venv/bin/python -m pytest -q && cd ..
cd frontend && node --test src/maze.test.mjs | tail -5 && cd ..
```

Say: 39 backend tests and 10 frontend tests. They run on a throwaway SQLite file, never Postgres,
and the pipeline runs both before any image is built.

## 4. Docker, 45 seconds

T1:

```bash
docker compose ps
docker compose logs backend | grep -iE 'running upgrade|uvicorn running'
```

Say: three services. The backend runs the Alembic migration, then serves. The frontend image is a
two-stage build, Node to build and nginx-unprivileged to serve, and both images run as a non-root
uid.

## 5. Kubernetes and Helm, 90 seconds

T2:

```bash
helm list -n mazehub
kubectl get deploy,svc,pods,hpa -n mazehub
kubectl describe ingress mazehub -n mazehub | sed -n '9,15p'
curl -s -H 'Host: mazehub.local' http://192.168.58.2/api/mazes/stats
```

Say: two backend replicas, two frontend replicas, three ClusterIP Services, and one Ingress sending
`/` to the frontend and `/api` to the backend. The HPA holds the backend between 2 and 5 pods on a
50% CPU target.

## 6. The probe really gates traffic, 45 seconds

T2:

```bash
kubectl get endpoints mazehub-backend -n mazehub
```

Say: two addresses, both Ready pods. When I pointed the readiness probe at a path the app does not
serve, the pod stayed `0/1` and never entered this list, so no request reached it. The container was
alive the whole time, so nothing restarted. That run is in the evidence file.

## 7. Monitoring, 90 seconds

Browser.

1. Prometheus tab: the job `mazehub-backend`, both endpoints **UP**. Say: a ServiceMonitor from the
   chart told Prometheus to find them.
2. Grafana tab: five panels. Name them. Requests per second by handler, p95 latency, responses per
   second by status class, backend targets up, requests served.

T2, if asked where the numbers come from:

```bash
kubectl exec -n mazehub deploy/mazehub-backend -c backend -- \
  python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/metrics').read().decode()[:400])"
```

## 8. Security, 60 seconds

Show `.github/workflows/ci-cd.yml` and `security/TRIVY.md`.

```text
Say: five scanners. Bandit on the Python source, pip-audit and npm audit on the dependencies,
gitleaks over the whole history, and Trivy on both built images. The build job declares
needs: [test, sast, sca, secrets], so a red scanner means nothing is pushed at all. The last image
scan found one MEDIUM, CVE-2026-85091 in zlib, with zero fixable HIGH or CRITICAL, so the gate
passed.
```

---

## The pipeline loop — steps 9 to 12, about 5 minutes

This is the scored part. Run it while step 8 is still on screen if time is tight.

### 9. Make a real change

The smallest honest change is the banner the API serves. Edit `helm/mazehub/values.yaml`:

```bash
sed -i 's/banner: "Find your way out"/banner: "Live demo build"/' helm/mazehub/values.yaml
git diff --stat
```

Say: this is a one-line change to the chart values, and it rolls the pods, because the Deployment
carries a checksum of the ConfigMap.

### 10. Commit and push

```bash
git add helm/mazehub/values.yaml
git commit -m "Change the API banner for the demo"
git push
```

### 11. Watch the pipeline

T3:

```bash
gh run watch
```

While it runs, narrate the six jobs from the Actions page. Jobs 1 to 4 run in parallel, job 5 waits
for all four, job 6 waits for job 5.

```text
Say: job 1 runs both test suites and builds the frontend. Jobs 2, 3 and 4 are the scanners. Job 5
builds both images, tags them with this commit SHA, scans them with Trivy, gates, then pushes to
GHCR. Job 6 brings up a kind cluster, installs the same Helm chart with these two SHA tags, and
curls the backend and the frontend from inside the cluster.
```

A full run takes about 3 minutes. Use the wait for the Terraform step below, then come back.

### 12. See the deployment update

When job 5 is green, show the SHA tag and the new image:

```bash
SHA=$(git rev-parse HEAD)
echo "ghcr.io/sammyurfen/mazehub-backend:$SHA"
gh run view --log | grep -a "Total: " | tail -2
```

Then show job 6's own output in the run page: `kubectl get deploy,pods,svc` inside the kind cluster,
and the smoke test printing `{"status":"READY"}` followed by the stats JSON. That is the deployment
updating from this commit.

On the local cluster, roll the same change by hand so the audience sees the banner move:

```bash
helm upgrade mazehub helm/mazehub -f k8s/values-local.yaml -n mazehub --wait --timeout 8m
kubectl get pods -n mazehub            # a new ReplicaSet, the old pods terminating
curl -s -H 'Host: mazehub.local' http://192.168.58.2/api/config
```

The banner in that JSON is the string committed in step 9.

```text
Say, honestly: the GitOps path is the same loop without my hands on it. gitops/application.yaml
declares an Argo CD Application with automated sync, prune and self-heal, so a push to the values
file is the whole deploy. I proved that loop on 7 October under the project's earlier name, and the
output is in the evidence. Argo CD is scaled to zero right now, because this node has 3 GB and the
app plus kube-prometheus-stack needs the memory. Nothing hides behind that: the pipeline path I just
ran is the one that is live.
```

---

## 13. Terraform, 60 seconds

T4:

```bash
terraform validate
tail -3 ../.evidence/terraform-plan.txt
```

Say: a VPC with two public and two private subnets across two availability zones, an EKS cluster on
Kubernetes 1.31 with one managed node group of two `t3.medium` nodes, and two ECR repositories.
`Plan: 62 to add, 0 to change, 0 to destroy`, no error and no warning. It costs about USD 0.27 each
hour, so `apply` and `destroy` run in one timed window and not during this demo. The workers sit in
the private subnets, so no node has a public IP, and the subnet `kubernetes.io/role/elb` tags are
what let a LoadBalancer Service find a place to live.

Be explicit: no AWS resource exists right now. Only the plan has run.

## 14. Close, 30 seconds

Show `README.md` section 15, the rubric map.

```text
Say: every module has a file path and an honest state in that table. Nine are done, Terraform is
plan-complete with apply and destroy pending, and the gaps are written down rather than talked
around.
```

---

## If something breaks on stage

| Problem | Do this |
|---|---|
| The port-forward died | `kubectl -n monitoring port-forward svc/kps-grafana 42120:80 &` and reload |
| `mazehub.local` does not resolve | Switch to `curl -H 'Host: mazehub.local' http://192.168.58.2/...` |
| The pipeline is slow | Move to steps 13 and 14, then return to the Actions tab |
| A pod is not Ready | `kubectl describe pod` and read the events out loud. The troubleshooting section of the README is the same workflow |
| Port 3000 is taken | The stack is on 3001. Say so and move on |

## Cut list, if you are over time

Drop in this order: step 6, step 2, step 13. Never drop steps 9 to 12.
