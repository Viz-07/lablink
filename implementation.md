# LabLink: Deployment Guide (for you, the human)

> **Updated:** 23 Nov 2026, 15:25 IST.
> **Goal:** get the two links the PromptWars briefing asks for: a working **Cloud Run URL** and a **public GitHub repo** (`.git` URL, one branch, under 10 MB).
> Run every command in **your own PowerShell window** from `C:\projects\LabLink`, not inside an agent sandbox.

---

## Where things stand

All code-side work is finished and verified. These earlier steps are **done**, so skip them:

| Done | What |
|---|---|
| ✅ | Frontend build fix (`.at()`), production build 79.99 kB gzip |
| ✅ | `requirements.txt` (incl. `tzdata` so the IST timezone works in slim containers), `pyproject.toml` |
| ✅ | Gemini default model switched to `gemini-3.5-flash`; output budget 2048 tokens |
| ✅ | `Dockerfile` (Python 3.12), `.dockerignore`, `.gitignore`, `.env.example` |
| ✅ | Tests: backend 70 passed (90.6 % coverage), frontend 38 passed (incl. axe + WCAG contrast); ruff, bandit, strict typecheck and production `npm audit` all clean |
| ✅ | CI workflow, README, `docs/` (architecture, security, accessibility, allocation, build spec), LICENSE |
| ✅ | 8 local commits on `main`; nothing pushed yet |

**Not yet verified:** the Docker image has never been built. The first `gcloud run deploy` in Step 2 is its first build, so read the build log if it fails (see Troubleshooting).

**Deployment mode (decided; don't change it before judging):** one Cloud Run service, **in-memory storage**, **exactly one always-on instance**, Gemini through Vertex AI using the service account (no API keys). Firestore mode is not suitable for judging. Its repository reads the whole database on every request.

---

## Prerequisites

| Tool | Check |
|---|---|
| Google Cloud CLI | `gcloud --version` (install: https://cloud.google.com/sdk/docs/install) |
| Git | `git --version` |
| A GCP project with **billing enabled** | console.cloud.google.com |
| A GitHub account | — |
| Docker Desktop (optional, Step 1 only) | `docker --version` |

---

## Step 1 (optional): Test the container locally

Only if Docker Desktop is installed. It catches build problems before Cloud Build does.
```powershell
docker build -t lablink .
docker run --rm -p 8080:8080 -e APP_ENV=development -e STORAGE_BACKEND=memory -e AI_ENABLED=false lablink
```
Open http://localhost:8080 → sign in as Aarav → browse and book. (`APP_ENV=development` is used locally because the production cookie is `Secure` and won't stick over plain `http://`.) Stop with `Ctrl+C`.

---

## Step 2: One-time Google Cloud setup

Replace `YOUR_PROJECT_ID`:
```powershell
$P = "YOUR_PROJECT_ID"
$R = "asia-south1"
gcloud auth login
gcloud config set project $P
gcloud config set run/region $R

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com `
  aiplatform.googleapis.com secretmanager.googleapis.com

# Runtime service account (least privilege)
gcloud iam service-accounts create lablink-run --display-name "LabLink Cloud Run"
$SA = "lablink-run@$P.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding $P --member "serviceAccount:$SA" --role roles/aiplatform.user
gcloud projects add-iam-policy-binding $P --member "serviceAccount:$SA" --role roles/logging.logWriter

# Session secret in Secret Manager
python -c "import secrets;print(secrets.token_urlsafe(48), end='')" | Out-File -Encoding ascii -NoNewline secret.txt
gcloud secrets create lablink-session-secret --data-file secret.txt
Remove-Item secret.txt
gcloud secrets add-iam-policy-binding lablink-session-secret `
  --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor
```
Also open **Vertex AI → Model Garden** in the console and confirm **Gemini 3.5 Flash** (or 3.8 Flash) is available to your project.

---

## Step 3: Deploy to Cloud Run

From `C:\projects\LabLink`:
```powershell
gcloud run deploy lablink `
  --source . `
  --region $R `
  --service-account $SA `
  --allow-unauthenticated `
  --cpu 1 --memory 512Mi --concurrency 80 `
  --min-instances 1 --max-instances 1 --cpu-boost `
  --timeout 60 `
  --set-env-vars "APP_ENV=production,STORAGE_BACKEND=memory,GCP_PROJECT=$P,AI_ENABLED=true,AI_PROVIDER=vertex,GEMINI_MODEL=gemini-3.5-flash,GEMINI_LOCATION=global,DEMO_MODE=true,SEED_DEMO_DATA=true" `
  --set-secrets "SESSION_SECRET=lablink-session-secret:latest"
```
- Answer **Y** if asked to create an Artifact Registry repository.
- `GCP_PROJECT` must be set even in memory mode; without it, AI is disabled.
- `--max-instances 1` is mandatory in memory mode, and `--min-instances 1` keeps it warm for judges.
- The command ends by printing the **Service URL**: that is your "Deployed Project" link.

---

## Step 4: Verify the live deployment (do all of it)

**4.1 Health and headers**
```powershell
$U = "https://lablink-xxxxx-el.a.run.app"   # your Service URL
curl.exe -s "$U/api/healthz"                                 # status ok, storage memory, ai_enabled true, model gemini-3.5-flash
curl.exe -sI "$U/" | findstr /i "content-security strict-transport x-frame"
curl.exe -s -o NUL -w "%{http_code}`n" "$U/api/docs"         # 404
```
`ai_enabled` must be **true**.

**4.2 Browser walkthrough** (incognito, exactly what judges see)
1. Open `$U` → login page with persona cards.
2. **Aarav (Student)** → Discover → AI search *"measure 2.4 GHz signals for my antenna project"* → spectrum analyser first, with a reason and the AI badge.
3. Open an instant-booking item → keyboard: Tab into the grid, arrow keys, Enter → Book → confirmed.
4. **Dr. Meera (Faculty)** → Approvals (AI summary loads) → Conflicts → spectrum analyser → **Recommend** → **Apply**.
5. **Sneha** → My bookings → Needs action → accept an alternative.
6. **Ravi (Lab admin)** → Analytics (AI insights) → Manage equipment → Audit log.
7. Reload a deep link such as `/conflicts/cf-demo-spectrum`. It must load.

**4.3 Confirm Gemini is really used.** Chrome DevTools → Network → the `search` request → its response must contain `"source":"ai"`. Check the conflict recommend and insights calls too. If you see `"fallback"`, go to 4.4.

**4.4 Logs**
```powershell
gcloud run services logs read lablink --region $R --limit 50
```
Look for `AI request failed (feature=..., error=...)` or `AI initialization failed`.

**4.5 Lighthouse** (Chrome DevTools → Lighthouse → Mobile) on `/login`, `/discover`, `/conflicts/cf-demo-spectrum`. Target Accessibility 100, Performance ≥ 90.

---

## Step 5: Fill in the README placeholders

In `README.md`, replace:
- `<CLOUD_RUN_URL>` → your Service URL
- `<user>` in the CI badge URL → your GitHub username

```powershell
git add README.md
git commit -m "docs: add live demo link and CI badge"
```
Optional tidy-up: `AGENT_FIX_TASKS.md` was an internal agent brief. Remove it from the repo if you prefer a cleaner root: `git rm AGENT_FIX_TASKS.md; git commit -m "chore: remove internal agent brief"`.

---

## Step 6: Publish to GitHub

Briefing rules: **public**, URL ends in **`.git`**, **exactly one branch**, **under 10 MB**.

1. On GitHub create a new **public, empty** repo named `lablink` (no README, no licence, no .gitignore).
2. Push:
```powershell
git branch                        # only: * main
git status                        # clean
git remote add origin https://github.com/<your-username>/lablink.git
git push -u origin main
git branch -a                     # main and remotes/origin/main only
```
3. On GitHub: **Actions** tab → CI run must be green. Repo **Settings** → size well under 10 MB.
4. Submission link: `https://github.com/<your-username>/lablink.git`.

---

## Step 7: Submit

- [ ] Signed in on the platform with the exact registration email
- [ ] GitHub `.git` URL (public, one branch, < 10 MB, CI green)
- [ ] Cloud Run URL (works in incognito, `/api/healthz` ok, AI `source: "ai"`)
- [ ] LinkedIn post (template: `docs/BUILD_SPEC.md` §21.3) linking the repo and live demo
- [ ] Brief project description (template: `docs/BUILD_SPEC.md` §21.2)
- [ ] Remember: **2 attempts, the latest score counts**. Only resubmit if the feedback shows clear, fixable gaps.

---

## Operations

| Task | Command |
|---|---|
| Redeploy after a code change | the Step 3 command again |
| View logs | `gcloud run services logs read lablink --region asia-south1 --limit 100` |
| Roll back | `gcloud run revisions list --service lablink --region asia-south1` then `gcloud run services update-traffic lablink --region asia-south1 --to-revisions <REVISION>=100` |
| Reset demo data | redeploy (memory mode reseeds on start). The admin reset button also works |
| Switch model without rebuilding | `gcloud run services update lablink --region asia-south1 --update-env-vars GEMINI_MODEL=gemini-3.8-flash` |
| Emergency: turn AI off (app keeps working on fallbacks) | `gcloud run services update lablink --region asia-south1 --update-env-vars AI_ENABLED=false` |
| After the event | `gcloud run services update lablink --region asia-south1 --min-instances 0` |

Don't redeploy during judging: a new revision resets the in-memory demo data. Set a **budget alert** in Billing → Budgets (e.g. ₹500).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Cloud Build fails on `npm ci` | lockfile out of sync | locally: `cd frontend; npm install; cd ..`, commit `package-lock.json`, redeploy |
| Container crashes with `ZoneInfoNotFoundError` | timezone data missing | make sure `tzdata` is in `backend/requirements.txt` (it is, as of commit `f5cd72f`) |
| Container crashes with `SyntaxError` at `def transact[T]` | base image older than 3.12 | keep `FROM python:3.12-slim` |
| `SESSION_SECRET must contain at least 32 bytes` | secret not mounted | check `--set-secrets` and the accessor role (Step 2) |
| Cloud Build permission error on `--source` | new-project build account lacks rights | grant `roles/cloudbuild.builds.builder` to the project's default compute service account, or deploy from Cloud Shell |
| `/api/healthz` shows `ai_enabled:false` | `GCP_PROJECT` missing / AI init failed | set env var, check logs |
| AI responses say `"fallback"` | model unavailable in location, missing IAM role, API not enabled | logs → try `GEMINI_MODEL=gemini-3.8-flash` or `GEMINI_LOCATION=us-central1` |
| Users see different data | more than one instance | `--max-instances 1` |
| Deep link 404 | SPA not copied into the image | check the Dockerfile `COPY --from=web` line |
| Repo over 10 MB | something large committed | `git rm -r --cached <path>`, fix `.gitignore`; if it's already in history, recreate the repo from a fresh single commit |
