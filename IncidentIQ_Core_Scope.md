# IncidentIQ — Core Scope

## Purpose

IncidentIQ is an AI-powered incident investigation platform for simulated production systems.

The goal is to build one coherent, interview-ready system that demonstrates:

- Backend engineering
- Observability
- Distributed tracing
- AI agent engineering
- RAG and information retrieval
- Evidence-grounded reasoning
- Evaluation of AI systems
- Full-stack product development

This document is the **scope contract for Core IncidentIQ**. We should refer to it whenever there is uncertainty about what to build. We will build the core scope first and will NOT add the advanced/optional technologies listed at the end unless the scope is explicitly revisited.

---

# 1. High-Level Architecture

```text
                 Simulated Production System
              ┌──────────────────────────────┐
              │ Order Service                │
              │ Payment Service              │
              │ Database / Dependencies      │
              └──────────────┬───────────────┘
                             │
                       OpenTelemetry
                             │
                    ┌────────┴────────┐
                    │ OTel Collector  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
            Logs          Metrics          Traces
            Loki        Prometheus         Jaeger
              └──────────────┼──────────────┘
                             ↓
                       IncidentIQ Backend
                             │
                       Incident Engine
                             │
                  AI Investigation Agent
                             │
        ┌────────────┬───────┼────────┬────────────┐
        ↓            ↓       ↓        ↓            ↓
      Logs        Metrics   Traces  Deployments  Knowledge
      Tool         Tool      Tool      Tool        Base
        └────────────┴───────┼────────┴────────────┘
                             ↓
                    Evidence Collection
                             ↓
                         RAG / Retrieval
                             ↓
                   Hypothesis + Reasoning
                             ↓
                    Root Cause Report
                             ↓
                     Next.js Dashboard
```

---

# 2. Simulated Production Environment

We will maintain a small, realistic production-like environment rather than creating many microservices.

## Services

### Order API
- FastAPI
- Receives order requests
- Calls Payment Service
- Propagates request/trace context
- Produces logs, metrics and traces

### Payment Service
- FastAPI
- Processes payments
- Can simulate controlled failures
- Produces logs, metrics and traces

### Dependencies

We may simulate a database or external dependency when useful for producing realistic incidents.

We do NOT need a large microservice ecosystem.

## Failure scenarios

We will implement approximately 4–5 meaningful incident types:

1. Database connection timeout
2. Payment service failure
3. High latency
4. Dependency unavailable
5. Bad deployment/configuration

The failure scenarios exist to create realistic investigation cases and an evaluation dataset.

---

# 3. Observability Layer

## OpenTelemetry

OpenTelemetry is the unified instrumentation/telemetry layer.

It will collect:

- Logs
- Metrics
- Traces

Applications send telemetry to the OpenTelemetry Collector.

## OpenTelemetry Collector

The Collector will act as the central telemetry pipeline.

```text
Services
   ↓
OTel Collector
   ├── Metrics → Prometheus
   ├── Logs    → Loki
   └── Traces  → Jaeger
```

The Collector is responsible for receiving, processing/batching and exporting telemetry.

## Storage / observability backends

### Prometheus
Used for metrics.

Examples:

- Request rate
- Error rate
- Failure count
- Latency
- Service health

### Loki
Used for logs.

Examples:

- Error messages
- Structured application logs
- Request IDs
- Service information

### Jaeger
Used for distributed traces.

Examples:

- Request flow across services
- Span durations
- Failed spans
- Service/dependency relationships

### Grafana
Used for dashboards and visualization.

We will build a useful incident-oriented dashboard containing information such as:

- Request rate
- Error rate
- P95 latency
- Payment failures
- Service health

Grafana is not being added just for the technology name; it provides an operational view of the system and another way to inspect incident evidence.

---

# 4. Distributed Correlation

The system must allow an investigation to correlate:

```text
Incident
   ↓
Trace
   ↓
Request
   ↓
Logs
```

We will use OpenTelemetry trace context and request IDs where appropriate.

The goal is to understand a request across services:

```text
Order API
    │
    └── Payment Service
```

The trace should contain the relevant spans from both services.

We should be able to connect:

- incident time window
- affected service
- trace
- individual spans
- corresponding logs
- request ID

This is a core part of IncidentIQ.

---

# 5. Incident Engine

The Incident Engine is the bridge between observability and AI.

It will create and manage structured incidents.

An incident should contain information such as:

```text
Incident
├── ID
├── Severity
├── Affected services
├── Start time
├── End time
├── Symptoms
└── Investigation status
```

The backend should provide APIs for operations such as:

```text
POST /incidents
GET  /incidents/:id
GET  /incidents/:id/timeline
POST /incidents/:id/investigate
```

The exact API design can evolve during implementation, but the Incident Engine should remain simple.

We are NOT building a complete enterprise incident-management platform.

The purpose is to provide a well-defined investigation problem to the AI system.

---

# 6. AI Investigation Agent

This is the central AI component.

We will use LangGraph to implement a controlled investigation workflow.

The agent should NOT be an unrestricted autonomous loop.

Instead, the application will control the overall investigation process while the LLM performs reasoning and selects/uses appropriate tools.

Conceptually:

```text
Incident
   ↓
Investigation State
   ↓
Generate hypotheses
   ↓
Gather evidence
   ↓
Evaluate evidence
   ↓
Update hypotheses
   ↓
Check contradictory evidence
   ↓
Produce root-cause report
```

## Why bounded orchestration?

The design should be explainable in interviews.

A controlled workflow provides:

- Easier evaluation
- Better reproducibility
- Easier debugging
- Better cost control
- More predictable tool usage
- Less risk of an uncontrolled agent loop

We still use an LLM for reasoning and tool usage where appropriate.

---

# 7. Investigation Tools

The agent will have a small, purposeful set of tools.

We do NOT want dozens of artificial tools.

## Tool 1 — Metrics

Conceptually:

```text
query_metrics()
```

Used for questions such as:

- What happened to the payment error rate?
- Did latency increase?
- When did the anomaly begin?
- Which service has abnormal metrics?

## Tool 2 — Logs

Conceptually:

```text
search_logs()
```

Used for:

- Searching errors
- Finding specific error messages
- Filtering by service
- Filtering by incident time window
- Finding correlated request IDs

## Tool 3 — Traces

Conceptually:

```text
get_trace()
```

Used for:

- Inspecting failed requests
- Finding the service where a request failed
- Examining span duration
- Following downstream dependencies

## Tool 4 — Deployments

Conceptually:

```text
get_recent_deployments()
```

Used for:

- Finding recent deployments
- Checking whether a deployment preceded an incident
- Providing deployment context to the investigation

This can initially use simulated deployment data.

## Tool 5 — Knowledge Base

Conceptually:

```text
search_runbooks()
```

Used for:

- Runbooks
- Architecture documentation
- Known failure modes
- Previous incident information
- Operational documentation

Five purposeful tools are preferred over a larger collection of unnecessary tools.

---

# 8. Knowledge Base and RAG

IncidentIQ will contain operational knowledge relevant to investigating incidents.

Example structure:

```text
docs/
├── runbooks/
│   ├── database-timeouts.md
│   ├── payment-service.md
│   └── high-latency.md
│
├── architecture/
│   ├── services.md
│   └── dependencies.md
│
└── incidents/
    ├── incident-001.md
    ├── incident-002.md
    └── incident-003.md
```

The exact documents will be created as the system develops.

The purpose of RAG is to give the investigator grounded operational knowledge rather than asking the LLM to rely only on its pretrained knowledge.

---

# 9. PostgreSQL + pgvector

PostgreSQL will be the primary application database.

We will use pgvector for vector search.

We do NOT need a separate vector database initially.

This keeps the architecture simpler and gives us a concrete tradeoff to explain:

> PostgreSQL + pgvector is sufficient for the scale and workload of this project, so introducing another database would add operational complexity without a clear benefit.

---

# 10. Hybrid Retrieval

The knowledge-base retrieval system will use both lexical and semantic search.

```text
                 Query
                   │
            ┌──────┴──────┐
            ↓             ↓
          BM25       Vector Search
            │             │
            └──────┬──────┘
                   ↓
            Hybrid Results
                   ↓
                Reranker
                   ↓
              Top Evidence
```

## Why hybrid retrieval?

Incident investigation contains both:

### Exact technical information

Examples:

- Error messages
- Error codes
- Service names
- Database names
- Configuration keys

BM25/lexical search is useful for these.

### Semantic questions

Examples:

- What normally causes payment database failures?
- What runbook applies to connection pool exhaustion?

Vector search is useful for these.

Therefore hybrid retrieval has a concrete architectural purpose.

---

# 11. Reranking

Retrieved documents will be reranked before being passed to the reasoning stage.

Conceptually:

```text
100 retrieved candidates
        ↓
     Reranker
        ↓
  Top relevant evidence
```

The purpose is to improve retrieval precision and reduce irrelevant context reaching the LLM.

We should be able to evaluate retrieval approaches such as:

- BM25
- Vector search
- Hybrid retrieval
- Hybrid + reranking

This is part of the AI engineering learning objective.

---

# 12. Evidence-Grounded Investigation

The AI should not simply output:

> "The database is the problem."

It should produce a conclusion supported by evidence.

Example:

```text
Root Cause:
Database connection exhaustion

Evidence:
1. Payment error rate increased sharply.
2. Failed traces terminate at the database operation.
3. Logs contain repeated database connection timeout errors.
4. The increase began shortly after deployment X.
5. The runbook associates this pattern with connection exhaustion.
```

The system should distinguish between:

- Observed evidence
- Hypotheses
- Conclusions
- Uncertainty

The agent should also look for contradictory evidence before finalizing a hypothesis.

---

# 13. Root-Cause Report

The final investigation result should contain something similar to:

```text
Incident
Severity
Affected Services
Incident Timeline

Root Cause
Confidence / supporting evidence

Evidence
├── Metrics
├── Logs
├── Traces
├── Deployment
└── Documentation

Investigation Steps

Alternative Hypotheses
Contradicting Evidence

Recommended Next Investigation / Action
```

The exact format can evolve, but the important requirement is that the report is evidence-grounded and explainable.

---

# 14. Evaluation Framework

Evaluation is a core part of IncidentIQ, not an optional extra.

We will create a known set of incidents with known root causes.

Example:

```text
Incident A → Database timeout
Incident B → Payment service failure
Incident C → Dependency outage
Incident D → Bad deployment
```

The expected root cause is known in advance.

We will evaluate:

## Retrieval

Potential metrics:

- Recall@K
- MRR / ranking quality

## Investigation

Potential metrics:

- Root-cause accuracy
- Evidence grounding
- Contradiction rate

## System

Potential metrics:

- Investigation latency
- Number of tool calls
- Token usage

The exact evaluation metrics can be refined once the first working agent exists.

---

# 15. Next.js Frontend

The final product will have a Next.js frontend.

The UI should focus on investigation rather than being a generic chatbot.

An incident page should show things such as:

```text
Incident #42
SEV-2

Root Cause
Database connection exhaustion

Timeline
────────────────────────
14:32 Deployment started
14:32 Latency increased
14:33 Errors increased
14:33 DB timeout detected

Evidence
├── Logs
├── Metrics
├── Traces
├── Deployment
└── Runbook

AI Investigation
────────────────────────
Step 1: Detected elevated errors
Step 2: Correlated payment failures
Step 3: Investigated database errors
Step 4: Validated against runbook
```

A useful feature is an evidence/"Why?" view that explains why the system reached its conclusion.

---

# 16. Backend / Infrastructure Choices

Core stack:

### Application

- Python
- FastAPI

### AI

- LangChain where useful
- LangGraph
- LLM API initially

### Database

- PostgreSQL
- pgvector

### Cache / supporting infrastructure

- Redis only where it provides a concrete purpose

### Observability

- OpenTelemetry
- OpenTelemetry Collector
- Prometheus
- Loki
- Jaeger
- Grafana

### Frontend

- Next.js
- React
- TypeScript

### Local infrastructure

- Docker

---

# 17. Architecture Principles

Throughout development, we should prefer:

### Simple over impressive

Do not add infrastructure just to put another technology on the resume.

### Purpose over technology

Every component should solve a real problem.

### Evaluability

AI behavior should be measurable wherever practical.

### Evidence over unsupported reasoning

The investigator should ground conclusions in logs, metrics, traces, deployments and documentation.

### Controlled agent behavior

Use deterministic application orchestration around LLM reasoning where it improves reliability.

### Minimal infrastructure

Avoid unnecessary distributed systems.

### Explainable tradeoffs

Every significant architectural decision should have a reason we can explain in an interview.

---

# 18. Explicitly Out of Core Scope

The following are NOT part of Core IncidentIQ.

Do not add them simply because they are popular technologies:

- Kafka
- Kubernetes
- Large microservice architectures
- Multi-agent architecture
- Separate vector database
- Complex event bus
- Excessive cloud infrastructure
- vLLM
- Quantization
- LoRA / QLoRA
- Model distillation
- MCP

These may be explored later as separate experiments, but they are not part of the Core IncidentIQ product.

---

# 19. Definition of Done

Core IncidentIQ is complete when:

1. Simulated services can generate realistic incidents.
2. Logs, metrics and traces are collected through OpenTelemetry.
3. Cross-service requests can be correlated.
4. Prometheus, Loki and Jaeger contain the relevant evidence.
5. Grafana provides useful operational dashboards.
6. Incidents can be created and represented through the backend.
7. The investigation agent can investigate an incident using bounded LangGraph orchestration.
8. The agent can query logs, metrics, traces and deployment information.
9. The agent can search operational documentation.
10. PostgreSQL + pgvector stores the knowledge base.
11. Hybrid BM25 + vector retrieval works.
12. A reranker improves/selects relevant evidence.
13. The agent produces an evidence-grounded root-cause report.
14. Known incidents can be used to evaluate the system.
15. The Next.js UI presents incidents, evidence, investigation steps and conclusions.
16. The entire core system can be run locally with Docker and documented clearly.

---

# 20. Development Order

We will build in this order:

```text
Phase 1
Observability
    ↓
Phase 2
Cross-service correlation
    ↓
Phase 3
Realistic incident scenarios
    ↓
Phase 4
Incident Engine
    ↓
Phase 5
Investigation Tools
    ↓
Phase 6
LangGraph Investigation Agent
    ↓
Phase 7
Knowledge Base + RAG
    ↓
Phase 8
Hybrid Retrieval + Reranking
    ↓
Phase 9
Evidence-grounded Root Cause Analysis
    ↓
Phase 10
Evaluation
    ↓
Phase 11
Next.js Investigation UI
    ↓
Phase 12
Docker + Documentation + Demo
```

---

# Final Rule

**Core IncidentIQ is the scope.**

If a new technology or feature comes up during development, ask:

1. Does it solve a real problem in IncidentIQ?
2. Does it materially improve the system?
3. Can we explain why we chose it?
4. Is the complexity justified?

If the answer is no, we do not add it.

The objective is not to build the project with the largest number of AI technologies.

The objective is to build a coherent AI incident-investigation system that we understand deeply enough to defend every important architectural decision in an interview.
