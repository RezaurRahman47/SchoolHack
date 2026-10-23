# ⚙️ Technical flow

How School Hack is built and where data goes. These diagrams match the **Technical** lens of the in-app Archify view. Open [`website/index.html#archify/tech`](../website/index.html) and press **Play**, or **Simulate an answer** to see a real generated question go through the real grader.

![Technical lens of the Archify view](images/archify-tech.png)

## Two versions, one design

| | `website/` | `backend-python/` |
|---|---|---|
| Runs as | One `index.html`, no build step | FastAPI + Uvicorn on port 8000 |
| Storage | Browser `localStorage`, per device | SQLite in `backend-python/data/` |
| Accounts | Demo login `admin / admin` | Demo login `admin / admin`, student and teacher portals |
| Test | Every skill twice, shuffled | Every skill twice, weighted toward weak skills |
| AI (optional) | Claude when the page runs on claude.ai | Claude when `ANTHROPIC_API_KEY` is set |
| Without AI | Built-in hints and summary | Built-in hints and summary |

## Runtime architecture

```mermaid
flowchart LR
    classDef people fill:#f1ecff,stroke:#6c4bf4,color:#1d2550
    classDef logic fill:#e3f1ff,stroke:#5cc8ff,color:#1d2550
    classDef data fill:#ddf8ec,stroke:#22c58b,color:#1d2550
    classDef back fill:#fff4cc,stroke:#e0a400,color:#1d2550

    subgraph P["People"]
        student["🧒 Student<br/>quiz in the browser"]
        teacher["👩‍🏫 Teacher<br/>dashboard + charts"]
    end
    subgraph L["App logic"]
        engine["🧪 Question engine<br/>buildTest · T"]
        grader["✅ Grader<br/>grade() · in code"]
        tutor["💡 Hint helper<br/>tip()"]
        agent["🤖 Gap finder<br/>analyse() · 5 steps"]
    end
    subgraph DA["Data & AI"]
        skills["🕸️ Skill graph<br/>SKILLS · prerequisites"]
        store[("💾 Progress<br/>localStorage")]
        claude["✨ Claude (optional)<br/>only phrases text"]
        klass["📊 Class data<br/>24 demo students + you"]
    end
    subgraph B["Behind the scenes"]
        rlp["📘 Berlin curriculum"]
        server[("🐍 Python version<br/>FastAPI + SQLite")]
        fallback["📦 Built-in hints<br/>TIPS"]
    end

    student -- "start" --> engine
    engine -- "questions" --> student
    student -- "answer" --> grader
    grader -- "feedback" --> student
    student -- "hint?" --> tutor
    skills -- "skills" --> engine
    grader -- "saves" --> store
    tutor -- "asks" --> claude
    claude -. "no Claude?" .-> fallback
    rlp -- "based on" --> skills
    store -. "or" .-> server
    teacher -- "analyse" --> agent
    klass -- "loads" --> agent
    agent -. "summary" .-> claude
    agent -- "gaps" --> teacher

    class student,teacher people
    class engine,grader,tutor,agent logic
    class skills,store,claude,klass data
    class rlp,server,fallback back
```

<details open>
<summary><b>📝 Taking a test</b>: build → show → grade → feedback → save</summary>
<br>

```mermaid
sequenceDiagram
    autonumber
    actor S as 🧒 Student
    participant E as 🧪 Question engine
    participant G as ✅ Grader
    participant P as 💾 Progress

    S->>E: Start test
    E->>E: Each of 15 skills twice → 30 questions with random values
    E-->>S: Question (multiple choice or number)
    S->>G: Answer
    G->>G: Choices exact · numbers ±2 % · known mistakes ("traps")
    G-->>S: 🎉 +10 ⭐ or 🤔 targeted explanation
    G->>P: Mastery: right closes 22 % of the gap, wrong −18 %
    Note over S,P: Wrong questions come back in the next round
```

</details>

<details>
<summary><b>💡 Getting a hint</b>: Claude when available, built-in hints otherwise</summary>
<br>

```mermaid
sequenceDiagram
    autonumber
    actor S as 🧒 Student
    participant H as 💡 Hint helper
    participant C as ✨ Claude (optional)
    participant F as 📦 Built-in hints

    S->>H: "Atomi, give me a hint!"
    alt Claude is available (claude.ai, or API key in Python)
        H->>C: Question + answer computed by code + method, "do not reveal the answer"
        C-->>H: 2 friendly sentences with a guiding question
    else Local or no permission
        H->>F: Fixed hint for this skill
        F-->>H: Hint
    end
    H-->>S: 💡 Hint (second tap: the method)
```

No name or score is ever sent with a hint.

</details>

<details>
<summary><b>🤖 Teacher gap finder</b>: five explainable steps</summary>
<br>

```mermaid
sequenceDiagram
    autonumber
    actor T as 👩‍🏫 Teacher
    participant A as 🤖 Gap finder
    participant K as 📊 Class data
    participant SG as 🕸️ Skill graph
    participant C as ✨ Claude (optional)

    T->>A: Run analysis (all · 9a · 9b)
    A->>K: Load mastery and answers per skill
    A->>A: Weak = mastery < 60 % or > 40 % wrong
    A->>SG: Prerequisite below 65 %? → likely cause
    A->>A: Groups by each student's weakest skill, actions
    opt Claude is available
        A->>C: Skill names + percentages only (no names)
        C-->>A: Two-sentence summary
    end
    A-->>T: Gaps · causes · groups · what to do next
```

In the Python version the same flow runs on the server: `GET /api/teacher/overview` then `POST /api/agent`.

</details>

<details>
<summary><b>🐍 Python version</b>: request routes</summary>
<br>

```mermaid
sequenceDiagram
    autonumber
    actor S as Browser / PWA
    participant API as FastAPI (main.py)
    participant Q as questions.py
    participant DB as SQLite (db.py)
    participant LLM as llm.py (optional)

    S->>API: POST /student/test/new
    API->>DB: Load mastery
    API->>Q: build_test(weights = mastery)
    API->>DB: Save test and questions
    S->>API: POST /student/test/{id}
    API->>Q: Grade each answer
    API->>DB: Save answers, update mastery
    opt Hint
        S->>API: POST /api/hint
        API->>LLM: tutor_hint() when a key is set
        LLM-->>API: Hint or built-in fallback
    end
```

</details>

## Where data lives

| Data | Website | Python version | Sent to Claude? |
|---|---|---|---|
| Stars, streak, mastery, tests | `localStorage` (`sh_state_v1`) | SQLite | ❌ |
| Language choice | `localStorage` (`sh_lang`) | n/a | ❌ |
| Student names | Demo names in code | SQLite | ❌ never |
| Question, answer, method (for a hint) | in memory | in memory | ✅ only if Claude is available |
| Skill names + class percentages (summary) | in memory | in memory | ✅ only if Claude is available |

## Components

| File | Responsibility |
|---|---|
| `website/index.html` | The whole standalone app: UI, `SKILLS`, templates `T`, `grade`, gap finder `analyse`, and the Archify view (`ARCH`). |
| `backend-python/app/main.py` | FastAPI app, page and API routes, role checks, startup database setup. |
| `backend-python/app/questions.py` | Skill graph, adaptive test assembly, grading and feedback. |
| `backend-python/app/db.py` | SQLite schema, demo seeding, persistence, mastery updates, class analytics. |
| `backend-python/app/agent.py` | Explainable teacher gap finder and suggested actions. |
| `backend-python/app/llm.py` | Optional Claude integration with local fallback. |
| `backend-python/app/templates/`, `static/` | Server-rendered pages, styles, charts, icons and PWA files. |
