"""Gap-finder agent for teachers.

Runs a small, explainable workflow over class data:
  1. load class data  2. detect weak skills  3. trace root causes in the skill graph
  4. form support groups  5. recommend actions (+ optional model summary)
Every step is returned as a trace so the dashboard can show the workflow.
"""
from __future__ import annotations

from . import db, llm
from .questions import SKILLS, VISIBLE_SKILLS

WEAK = 0.6


def run(klasse: str | None = None) -> dict:
    trace = []
    data = db.class_overview(klasse)
    students = [s for s in data["students"] if s["mastery"]]
    trace.append({"step": "Klassendaten laden",
                  "detail": f"{len(students)} Schüler·innen, {data['kpi']['tests']} Tests, {len(VISIBLE_SKILLS)} Skills"})

    # 2. weak skills: class mean mastery + error rate on first attempts
    skill_rows = []
    for s, meta in VISIBLE_SKILLS.items():
        vals = [st["mastery"].get(s, 0.3) for st in students]
        mean = sum(vals) / max(len(vals), 1)
        st = data["skill_stats"][s]
        n = st["correct"] + st["wrong"]
        err = st["wrong"] / n if n else 0
        below = [x for x in students if x["mastery"].get(s, 0.3) < WEAK]
        skill_rows.append({"skill": s, "name": meta["name"], "topic": meta["topic"], "mean": mean,
                           "error_rate": err, "below": below})
    weak = sorted([r for r in skill_rows if r["mean"] < WEAK or r["error_rate"] > 0.4],
                  key=lambda r: r["mean"])
    trace.append({"step": "Schwächen erkennen",
                  "detail": f"{len(weak)} Skills unter {int(WEAK * 100)} % Beherrschung oder > 40 % Fehlerquote"})

    # 3. root causes: a weak skill whose prerequisite is also weak -> fix the prerequisite first
    by = {r["skill"]: r for r in skill_rows}
    gaps = []
    for r in weak[:5]:
        weak_pre = [p for p in VISIBLE_SKILLS[r["skill"]]["pre"] if by[p]["mean"] < WEAK + 0.05]
        root = min(weak_pre, key=lambda p: by[p]["mean"]) if weak_pre else None
        gaps.append({
            "skill": r["skill"], "name": r["name"], "topic": r["topic"],
            "mastery": round(100 * r["mean"]), "error_rate": round(100 * r["error_rate"]),
            "students_below": len(r["below"]),
            "root_cause": SKILLS[root]["name"] if root else None,
            "severity": "hoch" if r["mean"] < 0.45 else "mittel",
        })
    roots = sum(1 for g in gaps if g["root_cause"])
    trace.append({"step": "Ursachen im Skill-Graph suchen",
                  "detail": f"{roots} Lücke(n) gehen auf eine schwache Voraussetzung zurück"})

    # 4. support groups: students sharing the same weakest skill
    groups: dict[str, list[str]] = {}
    for st in students:
        worst = min(st["mastery"], key=st["mastery"].get)
        if st["mastery"][worst] < WEAK:
            groups.setdefault(SKILLS[worst]["name"], []).append(st["name"])
    groups_list = sorted(({"skill": k, "students": v} for k, v in groups.items()),
                         key=lambda g: -len(g["students"]))[:4]
    trace.append({"step": "Fördergruppen bilden", "detail": f"{len(groups_list)} Gruppen nach schwächstem Skill"})

    # 5. actions
    actions = []
    for g in gaps[:3]:
        if g["root_cause"]:
            actions.append(f"Vor „{g['name']}“ 10 Minuten Wiederholung zu „{g['root_cause']}“ einplanen "
                           f"({g['students_below']} Schüler·innen betroffen).")
        else:
            actions.append(f"„{g['name']}“ im Plenum mit einem Beispiel neu erklären, dann 5 Übungsaufgaben "
                           f"(Fehlerquote {g['error_rate']} %).")
    at_risk = [s["name"] for s in data["students"] if s["passed"] is False]
    if at_risk:
        actions.append(f"{len(at_risk)} Schüler·innen unter 20/30 Punkten: Wiederholungstest automatisch zuweisen.")

    summary = llm.ask(
        "Du bist ein pädagogischer Assistent für Chemielehrkräfte (Klasse 9, Berlin). Fasse die Analyse in "
        "3 kurzen Sätzen auf Deutsch zusammen und nenne die wichtigste Maßnahme für die nächste Stunde.",
        f"Lücken: {gaps}\nGruppen: {groups_list}\nMaßnahmen: {actions}", 350)
    if not summary:
        top = gaps[0] if gaps else None
        summary = (f"Größte Lücke: „{top['name']}“ ({top['mastery']} % Beherrschung)."
                   + (f" Ursache liegt vermutlich bei „{top['root_cause']}“." if top and top["root_cause"] else "")
                   + f" Bestehensquote aktuell {data['kpi']['pass_rate']} %.") if top else "Keine größeren Lücken gefunden."
    trace.append({"step": "Maßnahmen empfehlen",
                  "detail": "Zusammenfassung vom KI-Modell" if llm.available() else "Regelbasiert (kein API-Key gesetzt)"})

    return {"summary": summary, "gaps": gaps, "groups": groups_list, "actions": actions, "trace": trace,
            "llm": llm.available()}
