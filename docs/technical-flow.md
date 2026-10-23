# Technical Flow

## Runtime architecture

```mermaid
flowchart LR
    Browser[Browser / PWA] -->|HTTP pages and API calls| FastAPI[FastAPI app]
    FastAPI --> Routes[Route handlers and role checks]
    Routes --> Templates[Jinja2 templates]
    Routes --> Domain[Question generation and grading]
    Routes --> Agent[Teacher gap-finder]
    Routes --> DB[(SQLite database)]
    Domain --> DB
    Agent --> DB
    Agent -. optional summary .-> LLM[Claude API wrapper]
    LLM -. no key or API failure .-> Fallback[Built-in hints and summary]
    FastAPI --> Static[Bundled static assets and PWA files]
    Browser --> Static
```

## Student request and persistence sequence

```mermaid
sequenceDiagram
    actor Student
    participant Browser
    participant API as FastAPI routes
    participant Questions as Question engine
    participant DB as SQLite
    participant Tutor as Optional LLM wrapper

    Student->>Browser: Sign in and start a test
    Browser->>API: POST /student/test/new
    API->>DB: Load current mastery
    API->>Questions: Build 30-question test using mastery
    API->>DB: Save test and questions
    API-->>Browser: Redirect to test page
    Student->>Browser: Submit answers
    Browser->>API: POST /student/test/{id}
    API->>Questions: Grade each response
    API->>DB: Save answers and update mastery
    API-->>Browser: Redirect to result/retry flow
    opt Student requests a hint
        Browser->>API: POST /api/hint
        API->>Questions: Determine feedback for current answer
        API->>Tutor: Generate Socratic hint when configured
        Tutor-->>API: Hint or built-in fallback
        API-->>Browser: Return hint
    end
```

## Teacher-analysis sequence

```mermaid
sequenceDiagram
    actor Teacher
    participant Browser
    participant API as FastAPI routes
    participant Agent as app.agent.run
    participant DB as SQLite
    participant Tutor as Optional LLM wrapper

    Teacher->>Browser: Open teacher dashboard and choose class
    Browser->>API: GET /api/teacher/overview?klasse=...
    API->>DB: Aggregate students, tests, mastery, and skill statistics
    DB-->>API: Class overview
    API-->>Browser: Dashboard data
    Teacher->>Browser: Start gap analysis
    Browser->>API: POST /api/agent?klasse=...
    API->>Agent: Run five-step gap-finder workflow
    Agent->>DB: Read class overview
    DB-->>Agent: Student mastery and assessment statistics
    opt ANTHROPIC_API_KEY is configured
        Agent->>Tutor: Request concise teacher summary
        Tutor-->>Agent: Summary or fallback on failure
    end
    Agent-->>API: Gaps, prerequisite causes, groups, actions, trace
    API-->>Browser: Analysis result
```

## Components and responsibilities

- `backend-python/app/main.py`: FastAPI app, page/API routes, role checks, and startup database initialization.
- `backend-python/app/questions.py`: skill graph, adaptive test assembly, answer grading, and feedback.
- `backend-python/app/db.py`: SQLite schema, demo seeding, persistence, mastery updates, and class analytics.
- `backend-python/app/agent.py`: explainable teacher gap-finder and suggested interventions.
- `backend-python/app/llm.py`: optional Claude integration with local fallback behavior.
- `backend-python/app/templates/` and `backend-python/app/static/`: server-rendered pages and bundled styles, charts, icons, and PWA assets.
- `website/index.html`: standalone browser-based version; no backend/build step required.

## Local request lifecycle

The Python version is served by Uvicorn on port 8000. FastAPI renders Jinja templates and serves the static/PWA assets. On startup, the app initializes SQLite and seeds demo records when the student table is empty. The optional Anthropic integration is disabled unless `ANTHROPIC_API_KEY` is provided; core grading and fallback explanations work without it.
