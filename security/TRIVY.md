# Trivy scan — what it looks at and what it found

Trivy 0.75.0 runs in job 5 of `.github/workflows/ci-cd.yml`, after the images are built and before
anything is pushed. It scans both images, `ghcr.io/sammyurfen/mazehub-backend` and
`ghcr.io/sammyurfen/mazehub-frontend`, each tagged with the commit SHA. For each image it reads the
Alpine package database and every Python distribution inside the layers, matches the installed
versions against its vulnerability feed, and also runs its secret scanner over the filesystem. Each
image is scanned twice: once as a full report across LOW to CRITICAL with `--exit-zero`, so the log
shows everything, and once as the gate with `--exit-code 1 --severity HIGH,CRITICAL
--ignore-unfixed --ignorefile security/.trivyignore`, so the build fails only on a HIGH or CRITICAL
that has a fixed version available. `security/.trivyignore` is empty on purpose, so nothing is
hidden from the gate.

The last recorded run is commit `3db8615`, 11 October 2026, pipeline run 38176668989. The full log
of that scan step is in `.evidence/trivy-run.txt`. The backend image reported
`Total: 1 (LOW: 0, MEDIUM: 1, HIGH: 0, CRITICAL: 0)` on Alpine 3.24.2 across 38 OS packages. The one
finding is **CVE-2026-85091**, a MEDIUM buffer-overflow issue in `zlib`, installed as `1.3.2-r0`
with a fix in `1.3.2-r1`. The frontend image, on Alpine 3.23.4 across 70 packages, reported no
vulnerability at all, because its Dockerfile runs one `apk upgrade` in the runtime stage: the 1.29
nginx-unprivileged base shipped 42 fixable HIGH CVEs before that upgrade. The gate passed both
images with zero fixable HIGH or CRITICAL, so the push to GHCR ran.

The one MEDIUM does not fail the build, and that is the intended behaviour rather than an oversight:
the gate is set at HIGH, and zlib reaches this image only as a transitive dependency of the Python
base, and the backend adds no gzip middleware, so no request path hands it compressed input from a caller. It clears on its
own at the next base-image rebuild, once `python:3.12-alpine` picks up `zlib 1.3.2-r1`.
