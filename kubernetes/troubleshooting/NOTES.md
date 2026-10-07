Break files for the final troubleshooting challenge. Each one is applied to the running Helm release
(see the Troubleshooting section of the root README):

| # | Break | How |
|---|---|---|
| 1 | Bad image tag | `helm upgrade ... --set backend.tag=does-not-exist` |
| 2 | Wrong Service selector | `kubectl patch svc incidentboard-backend --patch-file 2-wrong-selector.yaml` |
| 3 | Failing readiness probe | `kubectl patch deploy incidentboard-backend --patch-file 3-failing-probe.yaml` |
| 4 | Missing Secret key | `kubectl patch secret incidentboard-db --type=json -p '[{"op":"remove","path":"/data/DATABASE_URL"}]'` |
| 5 | Bad Ingress backend port | `kubectl patch ingress incidentboard --type=json --patch-file 5-bad-ingress-backend.yaml` |
