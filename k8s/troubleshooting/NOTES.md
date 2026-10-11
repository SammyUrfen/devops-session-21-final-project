Break files for the final troubleshooting challenge. Each one is applied to the running Helm release
(see the Troubleshooting section of the root README):

| # | Break | How |
|---|---|---|
| 1 | Bad image tag | `helm upgrade ... --set backend.tag=does-not-exist` |
| 2 | Wrong Service selector | `kubectl patch svc mazehub-backend --patch-file 2-wrong-selector.yaml` |
| 3 | Failing readiness probe | `kubectl patch deploy mazehub-backend --patch-file 3-failing-probe.yaml` |
| 4 | Missing Secret key | `kubectl patch secret mazehub-db --type=json -p '[{"op":"remove","path":"/data/DATABASE_URL"}]'` |
| 5 | Bad Ingress backend port | `kubectl patch ingress mazehub --type=json --patch-file 5-bad-ingress-backend.yaml` |

## Undoing a `kubectl patch` break

A plain `helm upgrade` does not undo breaks 2, 3 or 5. The patch makes `kubectl-patch` the owner of
that one field under server-side apply, and Helm then stops with a conflict:

```text
Error: UPGRADE FAILED: conflict occurred while applying object ...: conflict with "kubectl-patch"
```

Give the field back with the same tool that took it, then upgrade. For break 3:

```sh
kubectl patch deploy mazehub-backend -n mazehub --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/ready"}]'
helm upgrade mazehub helm/mazehub -f k8s/values-local.yaml -n mazehub --wait
```

`helm upgrade --force` also works. It replaces the object instead of merging, so it drops every
field manager, and it recreates the Deployment rather than rolling it.
