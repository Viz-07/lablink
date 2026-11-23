# LabLink — Deployment Implementation Plan

> **Purpose:** take the code currently in `C:\projects\LabLink` to a working, public **Google Cloud Run** deployment plus a clean **public GitHub repo**. These are the two links the PromptWars briefing requires. Do the steps in order. Every command is copy-paste ready.
>
> **Written:** 23 Nov 2026, after verifying the code (Section 1).
> **Companion doc:** `LABLINK_BUILD_SPEC.md` (product/architecture spec).

---

## 1. Verification results (what was actually tested)

The backend and frontend were run in a Linux sandbox with Python 3.12.16 and Node 22, using a scratch copy so your folder stayed untouched. Results:

### 1.1 Passed ✅

| Area | Check | Result |
|---|---|---|
| Startup | `create_app()` boots, seeds the demo, `/api/healthz` → 200 | ✅ |
| Seed | 40 equipment items, 11 labs, 8 departments, 19 users, 4 projects, 156 bookings, 2 open conflicts | ✅ |
| Auth | 7 personas listed; demo sign-in → 200; cookie is `HttpOnly; Secure; SameSite=Lax; Max-Age=28800` in production mode | ✅ |
| CSRF | POST without `X-Requested-With: LabLink` → **403** | ✅ |
| Authorisation | student → `/api/analytics/overview` **403**, student → `/api/approvals` **403** | ✅ |
| Catalogue | list (`total 40`), detail, availability, suggest slots | ✅ |
| AI search (fallback mode) | "measure 2.4 GHz antenna signals" → Keysight spectrum analyser ranked first, `source: "fallback"` | ✅ |
| Booking | auto-confirm on a free unit → `201 confirmed`; cancel → 200; purpose `"x"` → 422; unknown extra field → 422 | ✅ |
| Fair allocation | demo conflict `cf-demo-spectrum`: recommend → Aarav 0.8194 wins Unit 1, Sneha 0.60 and Kabir 0.2778 lose with reason `CAPACITY`; each gets **3 alternatives** (equivalent R&S analyser in the Comm Lab + same analyser at a nearby time) | ✅ |
| Apply conflict | apply → `resolved`; apply again → **409** | ✅ |
| Reallocation | Sneha's booking becomes `reallocated` with 3 alternatives (shown under `?when=action` in My Bookings, by design) | ✅ |
| Faculty/admin | approvals, conflicts, analytics, AI insights (fallback), audit log → 200 | ✅ |
| Production mode (`APP_ENV=production`) | `/`, `/discover`, `/conflicts/:id` serve the SPA; `/api/docs` → 404; unknown `/api/*` → JSON 404; hashed assets `Cache-Control: public, max-age=31536000, immutable`; `index.html` `no-cache` | ✅ |
| Security headers | CSP (no `unsafe-inline`), HSTS, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` all present | ✅ |
| CSP compatibility | built `index.html` has no inline scripts/styles; no `style={{…}}` in the source | ✅ |
| Frontend bundle (after the fix in Step 1) | builds in ~1 s; main JS 239 KB (**78 KB gzip**), CSS 6.8 KB gzip, every page lazy-loaded, `dist` = 364 KB | ✅ |

### 1.2 Blocking problems found ❌ (fixed by the steps below)

| # | Problem | Impact | Fixed in |
|---|---|---|---|
| B1 | `npm run build` fails: 3 uses of `Array.prototype.at()` with TS `lib: ES2020` (`ui.tsx:15`, `ConflictsPage.tsx:71`, `DiscoverPage.tsx:102`) | No frontend build → no deploy | Step 1 |
| B2 | No `backend/requirements.txt` | Container cannot install deps | Step 2 |
| B3 | **Default model `gemini-2.5-flash` has passed its retirement date** (Vertex AI lists it with retirement **20 Oct 2026**; recommended upgrades are `gemini-3.8-flash` / `gemini-3.5-flash-lite`) | Every AI feature would silently fall back | Step 3 |
| B4 | AI client sets `max_output_tokens=800` with no thinking control; on "thinking" models, reasoning tokens can use up that budget, which truncates the JSON → fallback | AI often shows `source: "fallback"` | Step 3 |
| B5 | No `Dockerfile`, `.dockerignore`, `.gitignore` | Cannot build the image; `node_modules` (Windows binaries) would be committed | Step 4 |
| B6 | Code uses **Python 3.12-only syntax** (`def transact[T](...)`, PEP 695) and 3.11+ APIs (`StrEnum`, `datetime.UTC`) | Must use a `python:3.12` base image (3.10/3.11 crash at import) | Step 4 |
| B7 | Git repo has **no commits** and no remote | Nothing to submit | Step 9 |

### 1.3 Important risks (not blocking, but they decide the deployment mode)

| # | Finding | Decision |
|---|---|---|
| R1 | `FirestoreRepository` loads **every document of every collection on every request** (`read()` streams 13 collections) and again inside every write transaction. Fresh seed = **~251 docs / 117 KB**, and it grows with each booking (slot locks), notification and audit entry. | ≈ 250–600 Firestore reads **per page request**, plus whole-database transactions that will contend and abort under concurrent judges. **Do not use Firestore for judging.** |
| R2 | Firestore transactions are limited to 500 writes; `demo/reset` deletes and rewrites everything | Reset will fail in Firestore mode once data grows |
| R3 | `memory` mode keeps state in one process | Must run **exactly one instance** (`--max-instances 1`), or users would see different data on different instances |
| R4 | No automated tests exist (`backend/tests/` is empty; `frontend` `test` script points to `tests/*.test.mjs`, which does not exist) | Not a deployment blocker, but **Testing** is a scored criterion. Step 10 adds a smoke suite + CI so the repo has evidence; a fuller suite is separate work |
| R5 | Python packages have no `__init__.py` (namespace packages) | Works with `uvicorn app.main:app` from `/app`; pytest needs `pythonpath = ["."]` (Step 10) |

### 1.4 ✅ Chosen deployment mode

**Cloud Run, one service, in-memory storage, exactly one always-on instance, Gemini through Vertex AI.**

- `STORAGE_BACKEND=memory`, `--min-instances 1 --max-instances 1`: fast (no DB round-trips), consistent, zero Firestore cost, and the demo reseeds itself (dates relative to "now") whenever a new revision starts. That is ideal for judges.
- Gemini via Vertex AI with the service account: **no API key anywhere**.
- `SESSION_SECRET` from Secret Manager, so sessions survive restarts.
- Firestore stays in the code as the documented "production path"; making it efficient is optional work (Step 12) and **must not** be switched on before judging unless re-verified.

---

## 2. Prerequisites (on your Windows PC)

| Tool | Why | Install / check |
|---|---|---|
| Git | push the repo | `git --version` |
| Node 22 LTS | build check | `node -v` |
| Python 3.12 | run/test backend locally | `py -3.12 --version` (install from python.org if missing; **3.10/3.11 will not work**) |
| Google Cloud CLI | deploy | https://cloud.google.com/sdk/docs/install → then `gcloud --version` |
| Docker Desktop *(optional)* | test the container locally | `docker --version` |
| A GCP project with **billing enabled** | Cloud Run, Cloud Build, Vertex AI | console.cloud.google.com |

> **About the sandbox problem you hit:** the Windows sandbox began rejecting commands right after `git init`. Run every command in this document in **your own PowerShell window** (not inside the agent sandbox). If the sandbox is needed again, restart it after Git initialisation; the `.git` folder itself is fine (44 KB, no commits).

All commands below are **PowerShell** unless marked `bash`. Run them from `C:\projects\LabLink` unless stated otherwise.

---

## 3. Step-by-step

### Step 1: Fix the frontend build (B1)

Replace the three `.at(-1)` calls (ES2022) with ES2020-safe equivalents. These are the exact edits that were verified to make `npm run build` pass.

`frontend/src/components/ui.tsx`, line 15:
```diff
- word(field.field.split('.').at(-1) || field.field)
+ word(field.field.split('.').slice(-1)[0] || field.field)
```
`frontend/src/pages/ConflictsPage.tsx`, line 71:
```diff
- Assigned unit {row.unit_id.split('-').at(-1)}
+ Assigned unit {row.unit_id.split('-').slice(-1)[0]}
```
`frontend/src/pages/DiscoverPage.tsx`, line 102:
```diff
- const cursor = previous.at(-1);
+ const cursor = previous[previous.length - 1];
```
(Do not raise `lib` to ES2022 instead: the fix above keeps the configured ES2020 target and needs no other changes.)

Verify:
```powershell
cd frontend
npm ci
npm run build          # must end with "✓ built in …"
cd ..
```

### Step 2: Create the backend dependency files (B2)

`backend/requirements.txt` (versions verified working together on Python 3.12):
```
fastapi==0.165.0
uvicorn==0.54.0
google-cloud-firestore==2.34.1
google-genai==3.6.1
```
(`pydantic 2.14.x` and `starlette 1.10.x` come in through FastAPI; JWT signing is done with the standard library `hmac`, so no PyJWT is needed.)

`backend/requirements-dev.txt`:
```
-r requirements.txt
httpx==0.28.1
pytest==9.2.0
```

`backend/pyproject.toml`:
```toml
[project]
name = "lablink-backend"
version = "1.0.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "-q"
```

Verify locally:
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:STORAGE_BACKEND="memory"; $env:AI_ENABLED="false"
python -m uvicorn app.main:app --port 8080
# new window: curl http://127.0.0.1:8080/api/healthz  -> {"status":"ok",...}
cd ..
```

### Step 3: Fix the Gemini model and output budget (B3, B4)

**3a. Change the default model** in `backend/app/core/config.py`:
```diff
-    gemini_model: str = "gemini-2.5-flash"
+    gemini_model: str = "gemini-3.5-flash"
```
At deploy time we set `GEMINI_MODEL` explicitly anyway (Step 7). Use **`gemini-3.8-flash`** (Google's recommended upgrade) or **`gemini-3.5-flash`** (GA since May 2026, supported to at least May 2027). Before deploying, open **Vertex AI → Model Garden** in your project and confirm the model is listed; if a call fails with "model not found", try `GEMINI_LOCATION=us-central1`.

**3b. Give the model room to answer** in `backend/app/ai/client.py`, `generate()`:
```diff
             config=types.GenerateContentConfig(
                 system_instruction=system, response_mime_type="application/json",
-                response_schema=schema, temperature=.2, max_output_tokens=800,
+                response_schema=schema, temperature=.2, max_output_tokens=2048,
             ),
```
Why: newer Gemini models reason ("think") before answering, and on some of them those tokens count toward the output budget. With only 800 tokens the JSON can be cut off; `model_validate_json` then fails and every feature quietly falls back. 2048 is still small and cheap.

Optional (latency): newer Gemini models let you lower the reasoning effort through a thinking setting in `GenerateContentConfig`. The field name and allowed values differ between model generations, so check the chosen model's page in the Vertex AI docs before adding it, and wrap it so an unsupported field can never break the call. Not required for correctness.

**3c. Test it** after deploying (Step 8.3): AI responses must say `"source": "ai"`.

### Step 4: Add `.gitignore`, `.dockerignore`, `Dockerfile` (B5, B6)

`.gitignore` (repo root):
```gitignore
# dependencies / builds
node_modules/
frontend/dist/
dist/
build/
backend/app/static/
# python
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
coverage/
# secrets / local
.env
.env.*
!.env.example
*.log
.DS_Store
Thumbs.db
# briefing PDF (2.2 MB, not part of the product)
Briefing*.pdf
```

`.dockerignore` (repo root):
```
**/node_modules
**/dist
**/.venv
**/venv
**/__pycache__
**/.pytest_cache
backend/tests
.git
.github
docs
*.md
*.pdf
.env
.env.*
```

`Dockerfile` (repo root). **Python must be 3.12** (B6):
```dockerfile
# ---------- Stage 1: build the React frontend ----------
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    APP_ENV=production
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=web /web/dist ./app/static
RUN useradd --uid 10001 --no-create-home appuser
USER 10001
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
```
Why it works with the existing code: `app/main.py` serves `app/static` when it exists (verified: `bundled = Path(__file__).parent / "static"`), so copying `dist` there is all that is needed.

`backend/.env.example` (documentation only, no real values):
```
APP_ENV=development
STORAGE_BACKEND=memory
GCP_PROJECT=
AI_ENABLED=true
AI_PROVIDER=vertex
GEMINI_MODEL=gemini-3.5-flash
GEMINI_LOCATION=global
SESSION_SECRET=
DEMO_MODE=true
SEED_DEMO_DATA=true
```

### Step 5: Test the container locally (optional, recommended if Docker Desktop is installed)

```powershell
docker build -t lablink .
$secret = python -c "import secrets;print(secrets.token_urlsafe(48))"
docker run --rm -p 8080:8080 -e SESSION_SECRET=$secret -e STORAGE_BACKEND=memory -e AI_ENABLED=false lablink
```
Open http://localhost:8080, sign in as Aarav, browse, book. Note: locally over `http://`, the `Secure` cookie may be dropped by some browsers. If sign-in does not stick locally, that is expected; it works on Cloud Run (HTTPS). For a local session use `-e APP_ENV=development`.

### Step 6: One-time Google Cloud setup

Replace `YOUR_PROJECT_ID` once:
```powershell
$P = "YOUR_PROJECT_ID"
$R = "asia-south1"                       # Mumbai
gcloud auth login
gcloud config set project $P
gcloud config set run/region $R

# APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com `
  aiplatform.googleapis.com secretmanager.googleapis.com

# Least-privilege runtime service account
gcloud iam service-accounts create lablink-run --display-name "LabLink Cloud Run"
$SA = "lablink-run@$P.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding $P --member "serviceAccount:$SA" --role roles/aiplatform.user
gcloud projects add-iam-policy-binding $P --member "serviceAccount:$SA" --role roles/logging.logWriter

# Session secret (48 random bytes) in Secret Manager
python -c "import secrets;print(secrets.token_urlsafe(48), end='')" | Out-File -Encoding ascii -NoNewline secret.txt
gcloud secrets create lablink-session-secret --data-file secret.txt
Remove-Item secret.txt
gcloud secrets add-iam-policy-binding lablink-session-secret `
  --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor
```
(Firestore is **not** needed for this deployment mode, so it is not enabled here.)

### Step 7: Deploy to Cloud Run

From the repo root (where the `Dockerfile` is):
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
Notes:
- `GCP_PROJECT` **must** be set even in memory mode. `build_ai_service()` enables Gemini only when a project id is present; without it every AI feature falls back.
- `--max-instances 1` is mandatory in memory mode (R3). `--min-instances 1` keeps it warm during judging (no cold starts; small cost).
- The first deploy asks to create an Artifact Registry repo: answer **Y**.
- The command prints the **Service URL** (`https://lablink-xxxxx-el.a.run.app`). That is the "Deployed Project" link.

### Step 8: Verify the live deployment (do all of it)

**8.1 Health and headers**
```powershell
$U = "https://lablink-xxxxx-el.a.run.app"   # your Service URL
curl.exe -s "$U/api/healthz"                 # {"status":"ok","storage":"memory","ai_enabled":true}
curl.exe -sI "$U/" | findstr /i "content-security strict-transport x-frame"
curl.exe -s -o NUL -w "%{http_code}`n" "$U/api/docs"    # 404 (hidden in production)
```
`ai_enabled` must be **true**. If false, `GCP_PROJECT` is missing or the AI client failed to initialise (check the logs, Step 8.4).

**8.2 Browser walkthrough** (incognito window, so it is exactly what judges see)
1. Open `$U` → login page with persona cards.
2. **Aarav (Student)** → Discover → AI search *"measure 2.4 GHz signals for my antenna project"* → the spectrum analyser is first, with a reason and the ✦ AI badge (no "AI unavailable" note).
3. Open an `auto` equipment item → keyboard: Tab into the grid, arrows, Enter, Shift+↓ → Book → confirmed.
4. Switch to **Dr. Meera (Faculty)** → Approvals (AI summary loads) → Conflicts → spectrum analyser → **Recommend** → table with scores + explanation → **Apply**.
5. Switch to **Sneha** → My bookings → "Needs action" → accept an alternative.
6. Switch to **Ravi (Lab admin)** → Analytics → AI insights; Manage equipment; Audit log.
7. Reload any deep link (e.g. `/conflicts/cf-demo-spectrum`): it must load, not 404.

**8.3 Confirm Gemini is really used**
In Chrome DevTools → Network, click the `search` request → Response must contain `"source":"ai"`. Repeat for the conflict recommend call (`explanation_source` / `source` field) and the insights call.
If you see `"fallback"` → check the logs (8.4). The usual causes are: the model name is not available in `GEMINI_LOCATION`, the IAM role is missing, or the Vertex API is not enabled.

**8.4 Logs**
```powershell
gcloud run services logs read lablink --region $R --limit 50
```
Look for `AI initialization failed` or timeout/validation warnings. Fix, then redeploy (Step 7 command again).

**8.5 Lighthouse**: Chrome DevTools → Lighthouse → Mobile → Accessibility / Best practices / Performance on `/login`, `/discover`, `/conflicts/cf-demo-spectrum`. Target Accessibility 100, Performance ≥ 90.

### Step 9: Create the public GitHub repo (B7)

Rules from the briefing: **public, URL ends in `.git`, exactly one branch, under 10 MB.**

```powershell
cd C:\projects\LabLink
git checkout -B main
git add .
git status                        # make sure NO node_modules, dist, .venv, .env, Briefing PDF are listed
git commit -m "feat: LabLink campus lab sharing platform with fair allocation and Gemini"
```
Create an **empty public** repo on GitHub named `lablink` (no README/licence, so there is no second history), then:
```powershell
git remote add origin https://github.com/<your-username>/lablink.git
git push -u origin main
git branch -a                     # only: main, remotes/origin/main
git count-objects -vH             # size-pack must be well under 10 MB
```
Submission link format: `https://github.com/<your-username>/lablink.git`.

Do **not** commit `LABLINK_BUILD_SPEC.md` at the root if you want a cleaner repo; moving it to `docs/BUILD_SPEC.md` is fine (153 KB). Keep this `implementation.md` in `docs/DEPLOYMENT.md` for the same reason.

### Step 10: Minimum test + CI evidence (Testing criterion, R4)

Create `backend/tests/test_smoke.py`. Every assertion below was verified against the current code:
```python
"""End-to-end smoke tests for the LabLink API (in-memory storage, AI fallback)."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

CSRF = {"X-Requested-With": "LabLink"}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    monkeypatch.setenv("AI_ENABLED", "false")
    with TestClient(create_app()) as test_client:
        yield test_client


def login(client: TestClient, persona: str) -> None:
    client.cookies.clear()
    response = client.post("/api/auth/demo", json={"persona_id": persona}, headers=CSRF)
    assert response.status_code == 200


def test_health(client: TestClient) -> None:
    assert client.get("/api/healthz").json()["status"] == "ok"


def test_security_headers(client: TestClient) -> None:
    headers = client.get("/api/healthz").headers
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"


def test_post_without_csrf_header_is_rejected(client: TestClient) -> None:
    assert client.post("/api/auth/demo", json={"persona_id": "u-aarav"}).status_code == 403


def test_student_cannot_open_faculty_pages(client: TestClient) -> None:
    login(client, "u-aarav")
    assert client.get("/api/approvals").status_code == 403
    assert client.get("/api/analytics/overview?range_days=7").status_code == 403


def test_catalogue_and_search(client: TestClient) -> None:
    login(client, "u-aarav")
    assert client.get("/api/equipment?limit=5").json()["total"] == 40
    hits = client.post("/api/ai/search", json={"query": "measure 2.4 GHz antenna signals"}, headers=CSRF).json()
    assert hits["results"][0]["equipment_id"] == "eq-spectrum-keysight"


def test_invalid_booking_input_is_rejected(client: TestClient) -> None:
    login(client, "u-diya")
    days = client.get("/api/equipment/eq-spectrum-rs/availability?days=5").json()["days"]
    slot = next(s for d in days for s in d["slots"] if s["state"] == "free")
    body = {"equipment_id": "eq-spectrum-rs", "start": slot["start"], "end": slot["end"], "purpose": "x"}
    assert client.post("/api/bookings", json=body, headers=CSRF).status_code == 422


def test_book_and_cancel(client: TestClient) -> None:
    login(client, "u-diya")
    days = client.get("/api/equipment/eq-spectrum-rs/availability?days=5").json()["days"]
    slot = next(s for d in days for s in d["slots"] if s["state"] == "free")
    body = {"equipment_id": "eq-spectrum-rs", "start": slot["start"], "end": slot["end"], "purpose": "Prototype test run"}
    booking = client.post("/api/bookings", json=body, headers=CSRF)
    assert booking.status_code == 201 and booking.json()["status"] == "confirmed"
    assert client.post(f"/api/bookings/{booking.json()['id']}/cancel", json={}, headers=CSRF).status_code == 200


def test_fair_allocation_resolves_demo_conflict(client: TestClient) -> None:
    login(client, "u-meera")
    detail = client.post("/api/conflicts/cf-demo-spectrum/recommend", headers=CSRF).json()
    ranking = detail["recommendation"]
    assert ranking[0]["student"] == "Aarav Shetty" and ranking[0]["unit_id"]
    assert all(row["reason"] == "CAPACITY" and len(row["alternatives"]) == 3 for row in ranking[1:])
    assert client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF).json()["status"] == "resolved"
    assert client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF).status_code == 409


def test_loser_receives_alternatives(client: TestClient) -> None:
    login(client, "u-meera")
    client.post("/api/conflicts/cf-demo-spectrum/recommend", headers=CSRF)
    client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF)
    login(client, "u-sneha")
    items = client.get("/api/bookings/mine?when=action").json()["items"]
    assert items[0]["status"] == "reallocated" and len(items[0]["alternatives"]) == 3
```
Run: `cd backend; .\.venv\Scripts\Activate.ps1; pytest`.

In `frontend/package.json`, change the broken test script (no `tests/` folder exists) until real tests are added:
```diff
-    "test": "node --test tests/*.test.mjs"
+    "test": "tsc --noEmit"
```

Create `.github/workflows/ci.yml` (the folder already exists and is empty):
```yaml
name: CI
on:
  push: { branches: [main] }
permissions: { contents: read }
jobs:
  backend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: backend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip, cache-dependency-path: backend/requirements-dev.txt }
      - run: pip install -r requirements-dev.txt
      - run: pytest
  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npm run build
      - run: npm audit --omit=dev --audit-level=high
```
Commit and push; check the Actions tab is green; add the badge to the README.

> The full test plan (allocator unit tests, authorisation matrix, axe accessibility tests, etc.) is in `LABLINK_BUILD_SPEC.md` §15. The smoke suite above is the minimum evidence; expand it before using your scored attempt if time allows.

### Step 11: README essentials (needed for the problem-alignment and code-quality scores)
The `docs/` folder is empty and there is no README. At minimum add `README.md` with: the live URL, a 60-second judge tour (Step 8.2 condensed), the problem-statement → feature table (spec §2.2), "How fairness works" (5 factors + weights), an architecture diagram, the deployment summary (this file), how to run tests, and the security/accessibility notes. Template: spec §19.

### Step 12 (optional, after the event or only if fully re-verified): Firestore mode
Do not switch before judging. To make Firestore viable:
1. Replace whole-state `read()`/`transact()` with per-collection, query-scoped methods (bookings by `equipment_id` + time window, notifications by `user_id`, etc.) so a request reads tens of docs, not hundreds.
2. Keep the slot-lock `transaction.create()` approach for double-booking safety, but lock only the affected equipment's docs.
3. Make `demo/reset` batch deletes in chunks of ≤ 400 writes.
4. Enable Firestore: `gcloud firestore databases create --location=asia-south1 --type=firestore-native`; grant `roles/datastore.user` to `$SA`; deploy rules that deny client access; redeploy with `STORAGE_BACKEND=firestore` and `--max-instances 3`.
5. Re-run Steps 8.1–8.3 and a concurrency check (two browsers booking the last unit at once → one 201, one 409).

---

## 4. Operations

| Task | Command |
|---|---|
| Redeploy after a code change | the Step 7 command again (same flags) |
| View logs | `gcloud run services logs read lablink --region asia-south1 --limit 100` |
| Roll back to the previous revision | `gcloud run revisions list --service lablink --region asia-south1` then `gcloud run services update-traffic lablink --region asia-south1 --to-revisions <REVISION>=100` |
| Reset demo data | sign in as Ravi → admin reset, or simply redeploy (memory mode reseeds on start) |
| Switch the AI model without rebuilding | `gcloud run services update lablink --region asia-south1 --update-env-vars GEMINI_MODEL=gemini-3.8-flash` |
| Turn AI off in an emergency (app keeps working on fallbacks) | `gcloud run services update lablink --region asia-south1 --update-env-vars AI_ENABLED=false` |
| After the event (stop paying for an idle instance) | `gcloud run services update lablink --region asia-south1 --min-instances 0` |

**Cost estimate:** one always-on 1 vCPU / 512 MiB instance for a few days is roughly the price of a coffee per day; Gemini Flash calls are fractions of a cent each and cached for 15 minutes. Set a **budget alert** in Billing → Budgets (e.g. ₹500).

---

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `npm run build` → `Property 'at' does not exist` | Step 1 not applied | apply Step 1 |
| Container crashes: `SyntaxError` at `def transact[T]` or `ImportError: cannot import name 'UTC'` | base image older than Python 3.12 | use `python:3.12-slim` (Step 4) |
| Deploy fails: `SESSION_SECRET must contain at least 32 bytes` | the secret is not mounted | check `--set-secrets` and the accessor role (Step 6) |
| Deploy fails: `Firestore storage requires GCP_PROJECT` | `STORAGE_BACKEND=firestore` set by mistake | use `memory` |
| Cloud Build permission error on `--source` deploy | the default build service account lacks rights in new projects | grant `roles/cloudbuild.builds.builder` to the project's default compute service account, or deploy once from Cloud Shell |
| `/api/healthz` shows `ai_enabled:false` | `GCP_PROJECT` missing / AI init failed | set env, check logs |
| AI responses say `"fallback"` | model not available in the location, missing `roles/aiplatform.user`, API not enabled, JSON truncated | check the logs; try `GEMINI_MODEL=gemini-3.8-flash` or `GEMINI_LOCATION=us-central1`; confirm Step 3b |
| Users see different data / bookings "disappear" | more than one instance in memory mode | `--max-instances 1` |
| Data reset unexpectedly | a new revision or instance restart (memory mode) | expected; avoid redeploying during judging |
| Sign-in does not stick on `http://localhost` | the `Secure` cookie on plain HTTP | use `APP_ENV=development` locally |
| Deep link returns 404 | the SPA was not copied into `app/static` | check the Dockerfile `COPY --from=web` line |
| GitHub repo > 10 MB | `node_modules`/PDF committed | fix `.gitignore`, `git rm -r --cached frontend/node_modules`, and if it is already in history, recreate the repo with a fresh single commit |

---

## 6. Final checklist before using a scored attempt

- [ ] Step 1 applied; `npm run build` passes on your PC
- [ ] `requirements.txt`, `pyproject.toml`, `Dockerfile`, `.dockerignore`, `.gitignore` committed
- [ ] Model updated (Step 3); live AI calls return `"source":"ai"`
- [ ] Cloud Run URL works in an incognito window; `/api/healthz` ok; `min=max=1` instance
- [ ] Every step of Step 8.2 walkthrough done on the live URL
- [ ] Repo public, `.git` URL, only `main`, < 10 MB, no secrets, no `node_modules`/PDF
- [ ] `pytest` green locally and in GitHub Actions
- [ ] README with live link + judge tour + problem-alignment table
- [ ] LinkedIn post + project description ready (spec §21)
- [ ] Remember: **2 attempts, the latest score counts.**
