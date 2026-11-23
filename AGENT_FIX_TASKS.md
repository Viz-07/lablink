# AGENT_FIX_TASKS.md: Fix-up brief for the coding agent (v2, updated 23 Nov 2026 14:40 IST)

> **Who this is for:** the AI coding agent working in `C:\projects\LabLink`.
> **Not for:** deployment. Deploying to Google Cloud and pushing to GitHub are done by the human using `implementation.md`. **Do not run `gcloud`, `git push`, or create GitHub repos/branches.**
>
> **v2 note:** a previous session already completed Tasks 1–6 and the backend half of Task 7 directly in this folder (verified; see "Progress" below). **Do not redo them.** Start at Task 0 (environment check), then continue from Task 7.5.

---

## Progress so far (verified by the previous session)

| Task | Status | Evidence |
|---|---|---|
| 1 Frontend `.at()` build fix | ✅ done | 3 replacements applied; `npm run build` passed (78 KB gzip main bundle) |
| 2 Backend packaging | ✅ done | `backend/requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `__init__.py` in every package incl. `tests/` |
| 3 Gemini model + output budget | ✅ done | default `gemini-3.5-flash` in `core/config.py`; `MAX_OUTPUT_TOKENS = 2048` in `ai/client.py`; AI warnings now log `feature=` + exception type |
| 4 Container + ignore files | ✅ done | `Dockerfile`, `.dockerignore`, `.gitignore`, `backend/.env.example` at the listed paths (Docker build not run: no Docker in that sandbox) |
| 5 Startup logging | ✅ done | lifespan logs config summary + memory-mode single-instance warning; `/api/healthz` also returns `model` |
| 6 Small correctness | ✅ done | `demo/reset` returns `409 RESET_UNSUPPORTED` when storage is Firestore; `ruff check .` clean, `ruff format --check .` clean, `bandit -q -r app` clean (seeded `Random(42)` marked `# noqa: S311  # nosec B311`); no bare excepts swallowing errors; no `dangerouslySetInnerHTML` / inline styles |
| 7.1–7.4 Backend tests | ✅ done | `backend/tests/`: `conftest.py`, `test_smoke.py`, `test_domain.py`, `test_allocator.py`, `test_auth_and_access.py`, `test_bookings.py`, `test_workflows.py`, `test_ai.py`, `test_security.py` → **70 passed, coverage 90.6 %** (gate set to 85 % in `pyproject.toml`; `firestore_repo.py` omitted from coverage) |
| 7.5 Frontend tests | ⚠️ written and passing in a scratch copy, **not yet in this folder** | 38 tests passed in scratch (`vitest run`); the files are reproduced exactly in **Appendix A**. `tsc --noEmit` on the test files still needed the type fix that is already included in Appendix A; re-verify |
| 8 CI | ❌ todo | |
| 9 Docs + README + LICENSE | ❌ todo | |
| 10 Accessibility pass | ❌ todo | |
| 11 Final verification + commit | ❌ todo | nothing committed yet (`git log` → no commits; everything is untracked) |
| 12 `AGENT_STATUS.md` | ❌ todo | |

Files the previous session changed in the application code (for review only, don't revert): `app/core/config.py`, `app/ai/client.py`, `app/ai/ai_service.py`, `app/main.py`, `app/api/routes/health.py`, `app/api/routes/admin.py`, `app/seed/demo_data.py`, `app/seed/catalogue.py` (`×` → `x` in spec strings), `app/services/analytics_service.py` (`zip(..., strict=True)`), `app/services/booking_state.py` (collapsed nested if), `app/services/conflict_service.py` (`l` → `lock`), plus `ruff format` across `app/` (formatting only; behaviour re-verified with the smoke flows), and `frontend/src/components/ui.tsx`, `pages/ConflictsPage.tsx`, `pages/DiscoverPage.tsx` (`.at()` fixes).

---

## 0. Rules

1. **Do not change product behaviour.** Fix, add, tidy; no redesign.
2. **Do not edit** `implementation.md`, `LABLINK_BUILD_SPEC.md` content, or `Briefing (1).pdf`.
3. **Only branch `main`.** You may `git add` / `git commit`; never create branches; never push.
4. **Sandbox safety:** keep commands short and non-interactive; never start `npm run dev`/`uvicorn` without a timeout and always stop them. If the sandbox starts rejecting commands, **stop and write progress to `AGENT_STATUS.md`** (or, if writing fails, report it in chat) instead of retrying in a loop.
5. **Python 3.12 is required** (PEP 695 generics, `StrEnum`, `datetime.UTC`). Use `py -3.12` on Windows.
6. **Lean dependencies**: only the packages named here.
7. **Repo < 10 MB**: never commit `node_modules`, `dist`, `.venv`, `backend/app/static`, `.coverage`, or the PDF (already in `.gitignore`).
8. After each task, run its Verify commands, then commit with a conventional message.

---

## Task 0: Environment check (new sandbox)

```
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
bandit -q -r app
pytest                      # expect: 70 passed, coverage ≥ 85 %
cd ..\frontend
npm ci                      # Windows-native install; the old node_modules may be stale. Delete it first if npm ci complains.
npm run build               # expect: ✓ built
```
If anything here fails, fix that first (it was green in the previous session) and note it in `AGENT_STATUS.md`.

Then make the first commit so the work so far is safe:
```
cd ..
git add -A
git status                  # verify: no node_modules / dist / .venv / .coverage / PDF
git commit -m "build: packaging, model update, container files and backend test suite"
```

---

## Task 7.5: Frontend tests (copy from Appendix A)

1. In `frontend/`, install the dev dependencies at these exact versions (they resolved together; `vitest@5` is required by `@testing-library/jest-dom@8`):
   ```
   npm install -D --save-exact vitest@5.1.1 jsdom@31.0.1 @testing-library/react@16.3.3 @testing-library/user-event@14.6.13 @testing-library/jest-dom@8.0.0 vitest-axe@0.1.0
   ```
2. In `frontend/package.json` set `"test": "vitest run"` (replaces the broken `node --test tests/*.test.mjs`).
3. Create every file in Appendix A exactly.
4. Generate the JSON fixtures (Appendix A.9). They are real API responses from the seeded demo.
5. Verify:
   ```
   npm run typecheck     # tsc --noEmit must pass including src/__tests__
   npm test              # expect: 5 files, 38 tests passed
   npm run build
   ```
   The jsdom message "Not implemented: HTMLCanvasElement's getContext()" printed by axe is harmless.
   If `tsc` still complains about matcher types (`toHaveNoViolations`, `toBeInTheDocument`), keep `src/__tests__/test-types.d.ts` and, if needed, add `"types": ["vite/client"]` to `tsconfig.json` `compilerOptions`, or exclude `src/__tests__` from `tsconfig.json` and add a `tsconfig.test.json` that includes it. **Do not** weaken `strict`.
6. Commit: `test: frontend unit, accessibility and contrast tests`.

---

## Task 8: CI

Create `.github/workflows/ci.yml` (the folder exists and is empty):
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
      - run: ruff check .
      - run: ruff format --check .
      - run: bandit -q -r app
      - run: pip-audit -r requirements.txt
      - run: pytest
  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npm run typecheck
      - run: npm test
      - run: npm run build
      - run: npm audit --omit=dev --audit-level=high
```
Run each step locally first. If `pip-audit` reports a vulnerable pinned version, bump to the nearest fixed version, re-run `pytest`, and note it. Commit: `ci: lint, security scan, tests and build`.

---

## Task 9: Documentation (Problem-alignment + Code-quality)

1. Move the spec: `git mv LABLINK_BUILD_SPEC.md docs/BUILD_SPEC.md`. Keep `implementation.md` and this file at the root.
2. Create `README.md` (root):
   - Title + one-paragraph pitch; CI badge placeholder `![CI](https://github.com/<user>/lablink/actions/workflows/ci.yml/badge.svg)`; `Live demo: <CLOUD_RUN_URL>` placeholder.
   - **Try it in 60 seconds**: Aarav → AI search "measure 2.4 GHz antenna signals" → Dr. Meera → Conflicts → spectrum analyser → Recommend → Apply → Sneha → My bookings → Needs action → accept alternative → Ravi → Analytics.
   - **How LabLink solves the problem statement**: table from `docs/BUILD_SPEC.md` §2.2, adjusted to what actually exists.
   - **How fairness works**: weights from `app/domain/constants.py` (deadline 0.35, fairness 0.25, project type 0.20, approval 0.10, waiting 0.10; project weights capstone 1.0 / research 0.9 / competition 0.85 / course 0.8 / personal 0.4); hard constraints; greedy allocation by score → earlier request → id; "the algorithm decides, Gemini explains"; deterministic fallbacks.
   - Architecture (ASCII: browser → single Cloud Run container [FastAPI API + built React SPA] → in-memory store (Firestore optional) + Vertex AI Gemini).
   - Tech stack and why; Security; Accessibility; Efficiency; Testing (commands + "70 backend tests, 90 % coverage; 38 frontend tests incl. axe + WCAG contrast"); Run locally; Deploy → link `implementation.md`; Project structure; Responsible AI; Licence.
3. `docs/ARCHITECTURE.md`, `docs/SECURITY.md` (threat → control table describing what the code really does: Pydantic `extra="forbid"`, CSRF header, HMAC-signed HttpOnly/Secure/SameSite cookie, CSP without `unsafe-inline`, HSTS, rate limits (auth 10/min/IP, AI 10/min & 100/day/user, writes 60/min), 64 KB body limit, generic 500s with request id, AI ID allow-list + delimited USER_TEXT, no API keys (Vertex via service account), non-root container), `docs/ACCESSIBILITY.md` (only what is implemented), `docs/ALLOCATION.md` (formula + worked example matching the seeded conflict: Aarav 0.8194 wins; Sneha 0.6000 and Kabir 0.2778 get 3 alternatives each).
4. `LICENSE`: MIT, 2026, `<Your Name>` placeholder.
5. One-line docstrings for public functions/classes that lack them (no noise comments).
Commit: `docs: README, architecture, security, accessibility and allocation docs`.

---

## Task 10: Accessibility pass (code-level, minimal changes)

Check and fix: one `<h1>` per page and ordered headings; `<main id="main">` + skip link first; visible labels on every input; errors via `aria-invalid` + `aria-describedby`; status badges include text; `:focus-visible` outline in `base.css` (no bare `outline: none`); `@media (prefers-reduced-motion: reduce)` disables transitions/animations; charts have a text alternative or table toggle; route change updates `document.title` and focuses the `<h1>`. The axe tests must still pass. Commit: `fix: accessibility pass`.

---

## Task 11: Final verification (all must pass)

```
cd backend && .venv\Scripts\activate
ruff check . && ruff format --check . && bandit -q -r app && pytest
cd ..\frontend
npm ci && npm run typecheck && npm test && npm run build
cd ..
git status
```
Production-mode spot check (short; stop it afterwards; don't leave `backend/app/static` behind): in a one-off Python script, run the app via `create_app(static_dir=Path("../frontend/dist"))` behind `TestClient` with `Settings(production=True, session_secret="x"*48, ai_enabled=False)` and confirm: `/` and `/discover` → 200 HTML; `/api/healthz` → ok; `/api/docs` → 404; CSP + HSTS present; demo login cookie has `Secure` and `HttpOnly`.

Final commit if anything changed. **Do not push.**

---

## Task 12: `AGENT_STATUS.md` (git-ignored, for the human)

✅/❌ per task with verification output (test counts, coverage, build size), anything skipped and why (e.g. Docker not installed), files changed, and next human steps pointing to `implementation.md`: Step 6 GCP setup → Step 7 deploy → Step 8 verify → Step 9 GitHub (Steps 1–4 and 10 of `implementation.md` are already done in code).

---

## Definition of done

`ruff`/`bandit`/`pytest` (≥ 85 %) green · `npm run typecheck`, `npm test`, `npm run build` green · CI workflow, README, docs, LICENSE present · commits on `main` only, nothing pushed · `AGENT_STATUS.md` written.

---

## Appendix A: Frontend test files (passed 38/38 in the previous session)

### A.1 `frontend/vitest.config.ts`
```ts
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', setupFiles: ['./vitest.setup.ts'], include: ['src/**/*.test.{ts,tsx}'] },
});
```

### A.2 `frontend/vitest.setup.ts`
```ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, expect, vi } from 'vitest';
import * as matchers from 'vitest-axe/matchers';

expect.extend(matchers);
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false, media: query, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {},
    dispatchEvent: () => false,
  }),
});
HTMLDialogElement.prototype.showModal ??= function showModal(this: HTMLDialogElement) { this.open = true; };
HTMLDialogElement.prototype.close ??= function close(this: HTMLDialogElement) { this.open = false; };
```

### A.3 `frontend/src/__tests__/test-types.d.ts`
```ts
/// <reference types="vite/client" />
import '@testing-library/jest-dom/vitest';
import 'vitest-axe/extend-expect';
```

### A.4 `frontend/src/__tests__/helpers.tsx`
```tsx
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { AuthProvider, ToastProvider } from '../hooks';

type Reply = { status?: number; body?: unknown };

/** Stub fetch with a route table: keys are "METHOD /api/path" (query string ignored). */
export function mockApi(routes: Record<string, Reply | ((body: unknown) => Reply)>) {
  const calls: { method: string; path: string; headers: Record<string, string>; body: unknown }[] = [];
  const fetchMock = vi.fn(async (input: string, init: RequestInit = {}) => {
    const method = init.method || 'GET';
    const path = input.split('?')[0] ?? input;
    const body = typeof init.body === 'string' ? JSON.parse(init.body) : undefined;
    calls.push({ method, path, headers: (init.headers || {}) as Record<string, string>, body });
    const entry = routes[method + ' ' + path];
    const reply = typeof entry === 'function' ? entry(body) : entry ?? { status: 404, body: { error: { code: 'NOT_FOUND', message: 'Not found' } } };
    const status = reply.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(reply.body ?? {}), { status, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return calls;
}

export function renderAt(path: string, pattern: string, element: ReactElement) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><ToastProvider>
    <Routes><Route path={pattern} element={element}/><Route path="*" element={<p>Navigated away</p>}/></Routes>
  </ToastProvider></AuthProvider></MemoryRouter>);
}
```

### A.5 `frontend/src/__tests__/contrast.test.ts`
```ts
import { describe, expect, it } from 'vitest';
import css from '../styles/tokens.css?raw';

function tokens(block: string): Record<string, string> {
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map(m => [m[1], m[2]]));
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi! + 0.05) / (lo! + 0.05);
}

const light = tokens(css.split(':root[data-theme="dark"]')[0] ?? '');
const dark = tokens(css.split(':root[data-theme="dark"]')[1]?.split('@media')[0] ?? '');
const TEXT_PAIRS: [string, string][] = [
  ['text', 'surface'], ['text', 'bg'], ['text-muted', 'surface'], ['text-muted', 'surface-2'], ['on-primary', 'primary'],
  ['primary', 'surface'], ['accent', 'surface'], ['success', 'success-soft'], ['warning', 'warning-soft'],
  ['danger', 'danger-soft'], ['danger', 'surface'],
];
const UI_PAIRS: [string, string][] = [['focus', 'surface'], ['focus', 'bg'], ['border-strong', 'surface']];

describe.each([['light', light], ['dark', dark]])('%s theme contrast (WCAG 2.2 AA)', (_name, theme) => {
  it.each(TEXT_PAIRS)('%s on %s is at least 4.5:1', (fg, bg) => {
    expect(ratio(theme[fg]!, theme[bg]!)).toBeGreaterThanOrEqual(4.5);
  });
  it.each(UI_PAIRS)('%s on %s is at least 3:1', (fg, bg) => {
    expect(ratio(theme[fg]!, theme[bg]!)).toBeGreaterThanOrEqual(3);
  });
});
```
(The previous session ran this test with `node:fs`; the `?raw` import here is the tsc-friendly version. If `?raw` fails under vitest, revert to `readFileSync(new URL('../styles/tokens.css', import.meta.url), 'utf8')` and add `@types/node` as an exact dev dependency.)

### A.6 `frontend/src/__tests__/client.test.ts`
```ts
import { describe, expect, it, vi } from 'vitest';
import { ApiError, api, post } from '../api/client';
import { mockApi } from './helpers';

describe('api client', () => {
  it('sends the CSRF header and JSON body', async () => {
    const calls = mockApi({ 'POST /api/auth/demo': { body: { ok: true } } });
    await post('/auth/demo', { persona_id: 'u-aarav' });
    expect(calls[0]?.headers['X-Requested-With']).toBe('LabLink');
    expect(calls[0]?.body).toEqual({ persona_id: 'u-aarav' });
  });

  it('turns the error envelope into an ApiError', async () => {
    mockApi({ 'GET /api/bookings/x': { status: 409, body: { error: { code: 'SLOT_UNAVAILABLE', message: 'Taken', request_id: 'r1' } } } });
    const error = await api('/bookings/x').catch(e => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: 'SLOT_UNAVAILABLE', message: 'Taken', requestId: 'r1' });
  });

  it('announces an expired session on 401', async () => {
    mockApi({ 'GET /api/bookings/mine': { status: 401, body: { error: { code: 'UNAUTHORIZED', message: 'Sign in' } } } });
    const listener = vi.fn();
    window.addEventListener('lablink:expired', listener);
    await api('/bookings/mine').catch(() => undefined);
    expect(listener).toHaveBeenCalledOnce();
  });

  it('returns undefined for 204 responses', async () => {
    mockApi({ 'POST /api/auth/logout': { status: 204 } });
    await expect(post('/auth/logout')).resolves.toBeUndefined();
  });
});
```

### A.7 `frontend/src/__tests__/LoginPage.test.tsx`
```tsx
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import LoginPage from '../pages/LoginPage';
import personas from './fixtures/personas.json';
import session from './fixtures/session.json';
import { mockApi, renderAt } from './helpers';

describe('LoginPage', () => {
  it('lists personas with descriptive names and has no axe violations', async () => {
    mockApi({ 'GET /api/auth/personas': { body: personas }, 'GET /api/auth/me': { status: 401, body: {} } });
    const { container } = renderAt('/login', '/login', <LoginPage/>);
    expect(await screen.findByRole('button', { name: /Continue as Aarav Shetty, Student/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('signs in and leaves the login page', async () => {
    const calls = mockApi({
      'GET /api/auth/personas': { body: personas },
      'GET /api/auth/me': { body: session },
      'POST /api/auth/demo': { body: { user: session.user } },
    });
    renderAt('/login', '/login', <LoginPage/>);
    await userEvent.click(await screen.findByRole('button', { name: /Continue as Dr. Meera Kulkarni/ }));
    await waitFor(() => expect(screen.getByText('Navigated away')).toBeInTheDocument());
    expect(calls.some(c => c.method === 'POST' && c.body && (c.body as { persona_id: string }).persona_id === 'u-meera')).toBe(true);
  });
});
```

### A.8a `frontend/src/__tests__/AvailabilityGrid.test.tsx`
```tsx
import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { Day, Interval } from '../api/types';
import AvailabilityGrid from '../components/AvailabilityGrid';
import availability from './fixtures/availability.json';

const days = availability.days as Day[];

function Harness({ onSelect }: { onSelect: (value?: Interval) => void }) {
  const [selected, setSelected] = useState<Interval>();
  return <><h2 id="availability-title">Availability</h2>
    <AvailabilityGrid days={days} duration={30} selected={selected} onSelect={value => { setSelected(value); onSelect(value); }}/></>;
}

describe('AvailabilityGrid', () => {
  it('uses a roving tabindex and moves focus with arrow keys', () => {
    render(<Harness onSelect={() => {}}/>);
    const cells = screen.getAllByRole('gridcell').map(cell => cell.querySelector('button')!);
    expect(cells.filter(button => button.tabIndex === 0)).toHaveLength(1);
    const first = cells.find(button => button.tabIndex === 0)!;
    first.focus();
    fireEvent.keyDown(first, { key: 'ArrowDown' });
    expect(document.activeElement).not.toBe(first);
    expect((document.activeElement as HTMLButtonElement).tabIndex).toBe(0);
  });

  it('selects free slots and ignores closed or past ones', () => {
    const onSelect = vi.fn();
    render(<Harness onSelect={onSelect}/>);
    const buttons = screen.getAllByRole('gridcell').map(cell => cell.querySelector('button')!);
    const blocked = buttons.find(button => button.getAttribute('aria-disabled') === 'true')!;
    fireEvent.click(blocked);
    expect(onSelect).not.toHaveBeenCalled();
    const free = buttons.find(button => button.getAttribute('aria-disabled') === 'false')!;
    fireEvent.click(free);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ start: expect.any(String), end: expect.any(String) }));
    expect(screen.getByRole('status')).toHaveTextContent('Selected slot');
  });

  it('describes every cell for screen readers and passes axe', async () => {
    const { container } = render(<Harness onSelect={() => {}}/>);
    const labelled = screen.getAllByRole('gridcell').map(cell => cell.querySelector('button')!.getAttribute('aria-label'));
    expect(labelled.every(Boolean)).toBe(true);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

### A.8b `frontend/src/__tests__/ConflictsPage.test.tsx`
```tsx
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import ConflictsPage from '../pages/ConflictsPage';
import conflict from './fixtures/conflict.json';
import recommended from './fixtures/recommended.json';
import session from './fixtures/session.json';
import { mockApi, renderAt } from './helpers';

describe('ConflictsPage review', () => {
  it('shows the ranked fair allocation after Recommend and passes axe', async () => {
    mockApi({
      'GET /api/auth/me': { body: session },
      'GET /api/conflicts/cf-demo-spectrum': { body: conflict },
      'POST /api/conflicts/cf-demo-spectrum/recommend': { body: recommended },
    });
    const { container } = renderAt('/conflicts/cf-demo-spectrum', '/conflicts/:id', <ConflictsPage/>);
    await userEvent.click(await screen.findByRole('button', { name: /Recommend fair allocation/ }));
    const table = await screen.findByRole('table', { name: 'Ranked allocation' });
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent('Aarav Shetty');
    expect(rows[0]).toHaveTextContent('Assigned unit');
    expect(screen.getByRole('button', { name: 'Apply allocation' })).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

### A.9 Generate the fixtures (run from `backend/` with the venv active)
Save as a temporary script **outside the repo** (or delete it afterwards) and run it with `python <script>`:
```python
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app

H = {"X-Requested-With": "LabLink"}
out = Path("../frontend/src/__tests__/fixtures")
out.mkdir(parents=True, exist_ok=True)
with TestClient(create_app(settings=Settings(ai_enabled=False))) as c:
    c.post("/api/auth/demo", json={"persona_id": "u-meera"}, headers=H)
    dump = lambda name, data: (out / name).write_text(json.dumps(data, indent=1))
    dump("conflict.json", c.get("/api/conflicts/cf-demo-spectrum").json())
    dump("recommended.json", c.post("/api/conflicts/cf-demo-spectrum/recommend", headers=H).json())
    dump("session.json", c.get("/api/auth/me").json())
    dump("personas.json", c.get("/api/auth/personas").json())
    dump("availability.json", c.get("/api/equipment/eq-spectrum-rs/availability?days=2").json())
```
(Run with `PYTHONPATH=.` / `set PYTHONPATH=.` if `app` is not importable.) The five files total ~22 KB; commit them.
