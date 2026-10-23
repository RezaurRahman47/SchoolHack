# 💼 Business flow

How School Hack creates value for students, teachers and the school. These diagrams match the **Business** lens of the in-app Archify view. Open [`website/index.html#archify/biz`](../website/index.html) and press **Play**, or **Simulate a school week**.

![Business lens of the Archify view](images/archify-biz.png)

## The whole loop at a glance

```mermaid
flowchart LR
    classDef student fill:#f1ecff,stroke:#6c4bf4,color:#1d2550
    classDef atomi fill:#ffe5ef,stroke:#ff8fb3,color:#1d2550
    classDef teacher fill:#ddf8ec,stroke:#22c58b,color:#1d2550
    classDef school fill:#fff4cc,stroke:#e0a400,color:#1d2550

    subgraph S["🧒 Student"]
        login["🔑 Sign in"] --> stars["⭐ Stars per topic"] --> test["📝 30-question test"] --> result["🏁 Result<br/>pass at 20 / 30"]
    end
    subgraph A["💡 Atomi helps"]
        progress["📈 Progress<br/>every answer counts"]
        help["💡 Hints<br/>never the answer"]
        again["🔁 Practise again<br/>only wrong ones"]
    end
    subgraph T["👩‍🏫 Teacher"]
        dash["📊 Class dashboard"] -- "1 click" --> gapf["🤖 Gap finder"] --> groups["👥 Support groups"] --> lesson["🗓️ Next lesson"]
    end
    subgraph SC["🏫 School"]
        rlp["📘 Berlin curriculum"]
        privacy["🔒 Privacy"]
        easy["🧰 One file, no server"]
    end

    test -- "hint?" --> help
    test -- "counts" --> progress
    result -- "mistakes" --> again
    again -- "again" --> test
    progress -- "shows" --> gapf
    lesson -- "practise" --> again
    rlp -- "skills" --> dash
    gapf -- "no names" --> privacy

    class login,stars,test,result student
    class progress,help,again atomi
    class dash,gapf,groups,lesson teacher
    class rlp,privacy,easy school
```

<details open>
<summary><b>🧒 Student journey</b>: sign in → test → hints → result → practise mistakes</summary>
<br>

```mermaid
journey
    title A student's chemistry session
    section Start
      Sign in (admin / admin): 4: Student
      Pick Chemistry, see stars per topic: 5: Student
    section Test
      Answer 30 fresh questions: 3: Student
      Ask Atomi for a hint: 4: Student, Atomi
      Get instant feedback and stars: 5: Student
    section Result
      See score, pass at 20 of 30: 4: Student
      Repeat only the wrong questions: 4: Student, Atomi
```

| Step | What happens | Where in the code |
|---|---|---|
| 1. Sign in | Pick *Student*, log in, open Chemistry. Stars per topic show what is already solid. | `viewLogin`, `viewChem` |
| 2. Fresh test | 30 new questions every start, two per skill, from templates with random values. | `buildTest`, `T` |
| 3. Hints | First hint is a nudge without the answer; the second shows the method. | `tip`, `TIPS` |
| 4. Result | Every answer updates mastery straight away. Pass with **20 of 30** in round 1, with confetti on success. | `answer`, `viewRoundResult` |
| 5. Practise mistakes | Only wrong questions come back, round after round, with the method from round 2. | `quiz.wrong` |

</details>

<details open>
<summary><b>👩‍🏫 Teacher journey</b>: dashboard → gap finder → groups → next lesson</summary>
<br>

```mermaid
flowchart TD
    classDef teacher fill:#ddf8ec,stroke:#22c58b,color:#1d2550
    classDef agent fill:#1d2550,stroke:#1d2550,color:#ffffff

    A["👩‍🏫 Teacher signs in"] --> B["📊 Dashboard<br/>pass rate · avg. points · below 20"]
    B --> C{"Class filter<br/>all · 9a · 9b"}
    C --> D["🤖 Run gap finder"]
    D --> E["1. Load class data"]
    E --> F["2. Find weak skills<br/>mastery < 60 % or > 40 % wrong"]
    F --> G["3. Trace causes<br/>prerequisite < 65 % in the skill graph"]
    G --> H["4. Form support groups<br/>by each student's weakest skill"]
    H --> I["5. Give tips<br/>revise the prerequisite first · retest below 20"]
    I --> J["🔁 Students practise the gap"]
    J -. "new answers" .-> B

    class A,B,C,J teacher
    class D,E,F,G,H,I agent
```

The summary at the top of the result uses Claude only when it is available (on claude.ai, or with `ANTHROPIC_API_KEY` in the Python version). Otherwise the code writes it. Either way, Claude only receives skill names and percentages, never student names.

</details>

<details>
<summary><b>🏫 Who gains what</b></summary>
<br>

| Who | What they get |
|---|---|
| 🧒 **Students** | Practice without fear: hints instead of answers, stars and streaks, mistakes simply come back. |
| 👩‍🏫 **Teachers** | No marking 30 questions × 24 students. Gaps, likely causes, groups and next steps in one click. |
| 🏫 **School** | Content from the Berlin-Brandenburg curriculum (grade 9 chemistry), German and English. |
| 🔒 **Privacy** | The website stores data only in the browser. AI is optional, never grades and never sees names. |
| 🧰 **Getting started** | One HTML file, no build step, no server. New subjects are added as new skills and templates. |

</details>

## Demo boundaries

> [!NOTE]
> - Both roles use the demo login `admin / admin`. Login is a demo, not a production user system.
> - The teacher dashboard shows **24 made-up students** (marked as example data) plus your own last test.
> - School Hack has no pricing model yet. Nothing on this page is a business figure.
