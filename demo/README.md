# Demo

| File | What it is |
|---|---|
| [mazehub-demo.mp4](mazehub-demo.mp4) | The presentation video, 4 minutes 6 seconds, 1920x1080 |
| [mazehub-capstone.pptx](mazehub-capstone.pptx) | The slide deck, 14 slides |
| [mazehub-capstone.pdf](mazehub-capstone.pdf) | The same deck as a PDF, so a browser can open it |

## What the video shows

The rubric asks for one loop: commit a change, watch the pipeline run, see the deployment update.

| Time | What happens |
|---|---|
| 0:05 | One line changes in `helm/mazehub/values.yaml` |
| 0:33 | `git add`, `git commit`, `git push` |
| 1:03 | The pipeline starts. Six jobs |
| 2:33 | Jobs 1 to 5 pass |
| 4:03 | Job 6 installs the chart with the new SHA tags. 5 pods Running, the smoke test returns `{"status":"READY"}` |

## The slides

14 slides, one for each module plus a title, an architecture page and an honest limits page.
Every screenshot the rubric asks for is in [`../docs/evidence/`](../docs/evidence/).
