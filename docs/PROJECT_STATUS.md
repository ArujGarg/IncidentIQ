# IncidentIQ — Project Status

_Last updated: 2026-10-13. The scope contract is [`IncidentIQ_Core_Scope.md`](../IncidentIQ_Core_Scope.md); this file records what actually exists._

## Architecture (current)

```
traffic_generator.py ──GET /orders──► Order API :8000
                                        │  X-Request-ID + W3C traceparent
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
              Inventory Service :8003        Payment Service :8001 ──POST /deployments──┐
                         └──────── OTLP gRPC :14317 ───┘                                 │
                                        ▼                                                │
                          OTel Collector (batch processor)                               │
              traces ▼            metrics ▼ (:8889, scraped 5s)    logs ▼                │
              Jaeger :16686       Prometheus :9090         Loki :3100                    │
                                        └──────── httpx queries ───┘                     │
                                                  ▼                                      │
                              IncidentIQ Backend :8002 (FastAPI) ◄───────────────────────┘
                              ├─ detector loop (every 10s, 4 detectors)
                              ├─ incidents → Postgres + pgvector :5432
                              └─ deployments → Postgres (survives restart)

Not built: investigation tools → LangGraph agent → RAG (pgvector + BM25 + reranker)
           → evidence-grounded report → evaluation → Next.js UI
```

**How to run it:** `docker compose up -d` starts the six infrastructure containers (Postgres+pgvector, Prometheus, Loki, Jaeger, OTel Collector, Grafana :3000). The apps run on the host with `uv run uvicorn <module>:app --port <port>`, where the module is `backend.main` (8002) or `services.{order_api,payment_service,inventory_service}.main` (8000/8001/8003). Then run `uv run python services/traffic_generator.py`. Start the backend after Postgres is up, because it creates tables when it is imported.

## Implementation status

"Verified" means checked at runtime on 2026-10-13. The project has no automated tests.

| Component | Status | Notes |
|---|---|---|
| Docker Compose infrastructure | Verified | All 6 containers healthy, Collector v0.161.0, Prometheus target UP. Images use `latest` tags. |
| Cross-service tracing | Verified | One trace: `order_api → inventory_service → payment_service → db.save_payment`. |
| Payment logs → Loki | Verified | Structured metadata includes `trace_id`/`span_id`; the log body includes `request_id`. |
| Payment metrics → Prometheus | Verified | `payment_requests_total`, `payment_request_duration_seconds_*`. Failure counters appear only after the first failure. |
| Order API / Inventory logs | Missing | Order API logs go to stdout only. Inventory has no logging. Order API crashes without logging when Inventory returns 503. |
| Scenario: DB timeout (`/admin/db-failure`) | Verified | Detected, but recorded by the *payment-failure* detector (see the dedup issue below). |
| Scenario: dependency unavailable (inventory `/admin/failure`) | Verified | Creates an `inventory_service` incident. |
| Scenarios: payment failure, high latency, bad deploy | Unverified | Blocked by the open `payment_service` incident. Payment `FAILURE_MODE` has no recover endpoint. |
| Incident API (`POST/GET /incidents`, `GET /incidents/{id}`, `PATCH /incidents/{id}/resolve`) | Verified | Incidents record `trigger` and `observed_value`. Resolve returns 404/409 for unknown/already-resolved. No `/timeline`, no `/investigate`. |
| Detection loop | Verified (partial) | Dedup is by service only (one open incident per service). Resolve is manual; no automatic resolution yet. `trigger` shows which signal crossed its threshold *first*, which is timing-dependent, not the root cause. |
| Deployment records | Verified | `Deployment` table in Postgres; `POST/GET /deployments` (optional `service` filter) survive a backend restart. |
| pgvector | Available, not installed | `CREATE EXTENSION vector` has not been run. |
| Grafana | Container only | No data sources or dashboards. |
| Metrics tool | Stub (uncommitted) | `backend/tools/metrics.py` accepts raw PromQL. It has no summary and no tests. |
| Logs / Traces / Deployments / KB tools | Not started | |
| LangGraph agent, LLM, RAG, hybrid retrieval, reranking, report, evaluation, Next.js UI | Not started | Phases 6–11. |
| Tests, README | Not started | `test/` is empty and `README.md` is empty. |

**Phases:** 1–3 are done (observability, correlation, scenarios). Phase 4 (Incident Engine) is partial. Phase 5 (Investigation Tools) has just started.

## Known defects

1. ~~Incidents are never resolved~~ Fixed: manual `PATCH /incidents/{id}/resolve`. Automatic resolution is still not implemented.
2. ~~Incidents don't record the detector~~ Fixed: `trigger` and `observed_value` columns.
3. The histogram uses the OTel default buckets (`0, 5, 10 … 10000`), which are millisecond-scale, but it records seconds. p95 is therefore meaningless.
4. The payment failure and bad-deploy branches return HTTP 200 and don't mark the span ERROR, so traces carry no evidence for these failures.
5. Payment `FAILURE_MODE` has no `/admin/recover`. One log line uses `service="payment-service"` (hyphen). `LAST_DEPLOYMENT` is never set.
6. If the backend is down, `/admin/deploy-bad-config` applies the bad config but fails to record the deployment.
7. Timestamps use `DateTime` without timezone. Config values (DB URL, service URLs) are hardcoded.
8. `docker/promtail/` is dead config (replaced by OTLP logs). Jaeger also exposes host port 4317, which bypasses the Collector.

## Outstanding tasks (in order)

**Step 3 — Evidence hardening (before tools)**
1. ~~Incident lifecycle: resolve endpoint and `trigger` field~~ Done 2026-10-13.
2. ~~Persist deployments in Postgres~~ Done 2026-10-13.
3. Set span status ERROR and return 5xx in the payment failure and bad-deploy branches.
4. Add a payment `/admin/recover` endpoint and fix the service label typo.
5. Add an OTel View with second-scale histogram buckets.
6. Send Order API and Inventory logs via OTLP, and log the inventory failure in Order API.

**Step 4 — Phase 5 tools (one at a time, each with pytest + `httpx.MockTransport`)**
- `query_metrics` (Prometheus), `search_logs` (Loki), `get_traces` (Jaeger HTTP API), `get_recent_deployments` (Postgres).
- `search_runbooks`: interface only now, implementation in Phase 7.

**Later:** Grafana data sources and dashboard, pinned image versions, README, Phases 6–12.

## Important decisions

- **Five purposeful tools, not many.** Each returns compact, structured evidence: a summary, key points, the exact query run (provenance), and an evidence ID for citation.
- **The Metrics tool uses a signal catalog, not raw PromQL.** The `signal` argument is an enum (e.g. `payment_error_rate`, `payment_latency_p95`) that maps to PromQL templates. The enum and its descriptions live in the tool schema, so no separate `list_metrics` tool is needed. Detectors reuse the same catalog.
- **Detection ≠ investigation.** An incident record is a pointer (service and time window). The investigation determines the cause.
- **Bounded LangGraph workflow**, not an open agent loop. It is reproducible, cost-bounded, and always checks contradicting evidence.
- **A deployment before a failure is correlation, not proof.** Causation needs matching error semantics, version-tagged failures, no competing explanations, and ideally recovery on rollback.
- **Postgres + pgvector** rather than a separate vector database. Infrastructure runs in Docker; apps run on the host with `uv` for fast iteration.
- Out of scope unless the scope document is revisited: Kafka, Kubernetes, multi-agent, a separate vector DB, MCP, model fine-tuning or serving.

## Exact next step

Step 3.3: **make payment failures visible in traces.** In `services/payment_service/main.py`, the `FAILURE_MODE` and bad-deploy (`PAYMENT_TIMEOUT`) branches return HTTP 200 and never mark the span as ERROR, so Jaeger carries no evidence for those scenarios. Record the exception and set the span status to ERROR in both branches (and return a 5xx), then verify in Jaeger that the failing trace is flagged `error=true`.
