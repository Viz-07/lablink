# Architecture

~~~text
Browser (React SPA)
        |
        v
Cloud Run container
  Uvicorn -> FastAPI -> routes -> domain and services
                 |                   |
                 |                   +--> Repository -> memory or Firestore
                 |                   +--> AI service -> Vertex AI Gemini
                 |
                 +--> built frontend and fingerprinted assets
~~~

FastAPI serves the API under `/api` and the static frontend at the same origin. Frontend routes such as `/discover` resolve to the SPA entry point. The entry point revalidates, fingerprinted assets are immutable for one year, and API responses use `no-store`. Vite proxies API requests during development.

Routes validate requests and enforce role and record scope. Domain code handles time intervals, priority scores, and allocation. Services coordinate bookings, review decisions, notifications, audit entries, and analytics through the repository. Timestamps are stored in UTC and scheduling uses campus time (IST).

The repository provides snapshot reads and atomic updates. Memory mode copies state under a process-local lock and seeds the demo on startup. The single-instance demo keeps all users on one shared state. Firestore mode reads collections inside transactions and writes changed records. A revision document serializes writes across instances. Whole-state reads make this implementation suitable for the demo-sized dataset.

Gemini calls use structured output, a bounded worker pool, timeouts, and a bounded cache. The AI layer can return local search rankings, draft text, summaries, explanations, and insights. The scheduling services compute and apply booking decisions.

See the [build specification](BUILD_SPEC.md) for the original design and the [deployment guide](../implementation.md) for operating the demo.
