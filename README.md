# LabLink

![CI](https://github.com/<user>/lablink/actions/workflows/ci.yml/badge.svg)

Live demo: <CLOUD_RUN_URL>

LabLink helps students find and book specialist equipment, development kits, and workstations across campus. Faculty review project access and resolve competing bookings with an auditable priority score. Lab administrators can see where demand exceeds capacity and which equipment has room for more use.

## Try it in 60 seconds

1. Sign in as **Aarav Shetty**. In **Discover**, ask AI Search “measure 2.4 GHz antenna signals.”
2. Use **Switch persona** to sign in as **Dr. Meera Kulkarni**. Open **Conflicts**, select the spectrum analyser conflict, then choose **Recommend fair allocation** and **Apply allocation**.
3. Switch to **Sneha Pai**. Open **My bookings** → **Needs action** and accept an alternative to the contested slot.
4. Switch to **Ravi**. Open **Analytics** to view utilisation and generate insights.

## How LabLink solves the problem statement

| Campus need | LabLink feature | Where |
| --- | --- | --- |
| Discover resources across departments | Search a shared catalogue with filters for department, lab, equipment type, availability, and training. AI Search matches a description to catalogue items. | `/discover` |
| Understand and get access | See lab hours, training requirements, approval rules, and live availability before requesting a slot. | `/equipment/:id` |
| Find and book feasible slots | Browse the 14-day calendar or ask Smart Slot Finder for openings by duration, date, and time of day. Eligible free slots can confirm immediately. | `/equipment/:id`, `/bookings` |
| Request access for a project | Create a project and request equipment and hours. The drafting assistant proposes a justification and equipment. | `/projects`, `/projects/new-request` |
| Review project access | Faculty review scoped requests, see risk flags and optional summaries, and approve with an access grant or decline. | `/approvals` |
| Resolve competing requests | Detect contention, rank feasible requests, and offer substitute slots after a reviewer applies an allocation. | `/conflicts`, `/bookings` |
| Allocate fairly | Show five weighted factors alongside the assignment and explain capacity and eligibility outcomes. | `/conflicts/:id` |
| Improve resource utilisation | Compare utilisation and demand, examine peak booking times and no-show rates, and review suggested actions. | `/analytics` |

## How fairness works

| Factor | Weight |
| --- | ---: |
| Deadline urgency | 35% |
| Fairness based on recent usage and no-shows | 25% |
| Project type | 20% |
| Prior approval | 10% |
| Time waiting | 10% |

The project factor is 1.00 for capstone, 0.90 for research, 0.85 for competition, 0.80 for course, 0.40 for personal, and 0.30 with no project. The service checks availability, training, lab hours, project deadlines, duration, weekly limits, and user overlap. The greedy allocator orders requests by descending score, earlier request time, then booking ID. It assigns the first feasible available unit and offers up to three alternatives when possible.

The algorithm decides, Gemini explains. The reviewer applies the proposal, and the backend rechecks feasibility inside a transaction. Local explanations and alternatives are available with AI disabled. See the [formula and seeded example](docs/ALLOCATION.md).

## Architecture

~~~text
Browser
  |
  v
Cloud Run container
  React SPA + FastAPI /api
           |
           +--> In-memory repository (Firestore optional)
           |
           +--> Vertex AI Gemini (optional)
~~~

The frontend and API share one origin. The demo uses one Cloud Run instance so all users share one in-memory repository. See [architecture](docs/ARCHITECTURE.md) and the [original build specification](docs/BUILD_SPEC.md).

## Tech stack and why

| Layer | Choice | Purpose |
| --- | --- | --- |
| UI | React, TypeScript, Vite | Typed views, per-route bundles, and a static build |
| API | FastAPI, Pydantic, Python 3.12 | Validate requests and keep scheduling rules on the server |
| Data | In-memory repository, optional Firestore | Fast seeded demo with an interchangeable persistence interface |
| AI | Vertex AI Gemini | Structured search, drafts, summaries, explanations, and insights |
| Runtime | Cloud Run, Uvicorn | Serve the SPA and API from one container |

## Security, accessibility, efficiency, and testing

### Security

Signed cookies, CSRF checks, role- and record-level authorization, request limits, and security headers protect the API. Vertex AI uses the Cloud Run service account in production. See [security controls](docs/SECURITY.md).

### Accessibility

The app has a skip link, named controls, a keyboard-operable availability grid with a list view, text status labels, reduced-motion styling, and table alternatives for charts. See [accessibility](docs/ACCESSIBILITY.md).

### Efficiency

Routes are lazy-loaded, catalogue results are paginated, and fingerprinted assets use long-lived caching. The backend puts time and concurrency bounds on Gemini calls and reuses cached responses.

### Testing

The suite has **70 backend tests** and **90.64% backend coverage** (85% required), plus **38 frontend tests** including axe and light/dark WCAG contrast checks. Run these commands from the indicated directories after installing dependencies.

~~~text
backend/   ruff check .
           ruff format --check .
           bandit -q -r app
           pip-audit -r requirements.txt
           pytest

frontend/  npm run typecheck
           npm test
           npm run build
           npm audit --omit=dev --audit-level=high
~~~

## Run locally

Use Python 3.12 and Node 22.22.2 or a newer Node 22 patch release. In PowerShell, start the API in one terminal from the repository root.

~~~powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install tzdata
$env:AI_ENABLED = 'false'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8080
~~~

The local Windows `tzdata` install supplies the IANA time-zone database. The demo seeds itself on startup and remains usable with the deterministic AI fallbacks.

In a second terminal, from the repository root, start Vite and open the URL it prints. Vite proxies API requests to port 8080.

~~~text
cd frontend
npm ci
npm run dev
~~~

## Deploy to Cloud Run

Follow the [deployment guide](implementation.md). The demo uses a single instance with memory storage and Vertex AI through its runtime service account.

## Project structure

~~~text
backend/app/         API, domain, services, repositories, seed data, and AI
backend/tests/       Backend unit, integration, and security tests
frontend/src/       React pages, components, styles, and tests
docs/               Architecture, security, accessibility, and allocation
.github/workflows/  Continuous integration
Dockerfile          Multi-stage frontend build and API runtime
~~~

## Responsible AI

Gemini suggestions are labelled **AI-generated**, and local equivalents are labelled **Rules-based**. Structured outputs and known IDs ground AI features in the catalogue and computed results. User-entered queries or project text can be sent for the requested feature, and people are represented by first name where the explanation or summary needs one. Booking writes, approvals, and eligibility remain under server-side rules and authorized users.

## Licence

LabLink is available under the [MIT licence](LICENSE).
