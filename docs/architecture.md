# Architecture

## System Overview

```mermaid
C4Context
    title OmniMigrate — System Architecture

    Person(user, "Engineer", "Submits legacy code for migration")
    Person(admin, "Admin", "Manages org, users, billing")

    System(omnimigrate, "OmniMigrate", "AI-powered legacy code migration engine")

    System_Ext(github, "GitHub", "Source code repositories")
    System_Ext(stripe, "Stripe", "Payment processing")
    System__ext(openai, "OpenAI", "LLM refactoring provider")
    System_Ext(otel, "OTel Collector", "Traces & metrics export")

    Rel(user, omnimigrate, "Submits code, reviews PRs")
    Rel(admin, omnimigrate, "Manages users, views billing")
    Rel(omnimigrate, github, "Clones repos, pushes branches, opens PRs")
    Rel(omnimigrate, stripe, "Creates checkout sessions, webhooks")
    Rel(omnimigrate, openai, "Code refactoring & self-healing")
    Rel(omnimigrate, otel, "Exports traces & metrics")
```

## Backend Layer Architecture

```mermaid
graph TB
    subgraph "API Layer"
        A[FastAPI Application]
        B[Rate Limiter Middleware]
        C[CORS Middleware]
    end

    subgraph "Auth & Security"
        D[JWT Auth + Redis Blocklist]
        E[RBAC — Org Roles]
        F[SSRF Hardening]
        G[Token Encryption — Fernet]
    end

    subgraph "Business Logic"
        H[Migration Engine]
        I[Autonomous Orchestrator]
        J[Billing Service]
        K[Organization Service]
    end

    subgraph "AI Pipeline"
        L[AST Parser — LibCST]
        M[LLM Agent — OpenAI]
        N[Rule Engine — Deterministic]
        O[Sandbox Verifier]
    end

    subgraph "Data Layer"
        P[(PostgreSQL)]
        Q[(Redis)]
    end

    subgraph "Observability"
        R[Structlog]
        S[Prometheus Metrics]
        T[OpenTelemetry Tracing]
    end

    A --> B --> C
    A --> D
    A --> E
    A --> H
    A --> I
    A --> J
    A --> K
    H --> L
    H --> M
    H --> N
    H --> O
    I --> M
    I --> N
    I --> O
    H --> P
    J --> P
    K --> P
    D --> Q
    A --> R
    A --> S
    A --> T
```

## Migration Pipeline Flow

```mermaid
flowchart TD
    A[Submit legacy code] --> B[AST Analysis — LibCST]
    B --> C{LLM key available?}
    C -->|Yes| D[LLM Refactoring — OpenAI]
    C -->|No| E[Deterministic Rule Engine]
    D --> F[Sandbox Verification]
    E --> F
    F --> G{Tests pass?}
    G -->|Yes| H[Generate Diff + Metrics]
    G -->|No| I{Heal attempts < 3?}
    I -->|Yes| J[Self-Heal — LLM or Rules]
    J --> F
    I -->|No| K[Mark Failed]
    H --> L[Complete]
```

## Autonomous Git Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant API as API
    participant O as Orchestrator
    participant S as Sandbox
    participant G as GitHub

    U->>API: POST /autonomous/run {repo_url}
    API->>O: execute_full_pipeline()
    O->>S: clone_repository()
    O->>S: run_tests() [baseline]
    loop Refactor + Heal
        O->>S: process_directory()
        O->>S: run_tests()
        alt Tests fail
            O->>S: heal_code_with_error()
        end
    end
    O->>G: commit_and_push()
    O->>G: create_pull_request()
    O->>API: PipelineResult {pr_url}
    API-->>U: {status: completed, pr_url: ...}
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Compose / Kubernetes"
        FE[Frontend — Vite Build]
        API[Backend — FastAPI + Uvicorn]
        W[Worker — Arq]
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    subgraph "External"
        GH[GitHub]
        ST[Stripe]
        LLM[OpenAI API]
    end

    FE -->|/api/*| API
    API --> PG
    API --> RD
    W --> PG
    W --> RD
    API --> GH
    API --> ST
    API --> LLM
    W --> GH
    W --> LLM
```
