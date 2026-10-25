"""Per-student learning profile.

Everything here is derived from data the grader already writes — no model is
involved, so the profile is as trustworthy as the grading:

* mastery per skill (``update_mastery``, Elo-style, plus attempt counters)
* first-round answers of the full tests (trend: last 14 days vs. before)
* the test history (score, pass, example grade key)
* wrong answers that still carry their question text
* how often the student asked the chemistry chat about a skill

Thresholds match the rest of the app: the colours of the home radar (``tone``)
and the gap finder's ``WEAK`` line, so a skill reads the same everywhere.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import db
from .agent import WEAK
from .questions import (PASS_MARK, SKILLS, SUBTOPIC_ORDER, SUBTOPIC_TITLES,
                        VISIBLE_SKILLS, VISIBLE_TOPICS, note_for)

GAP = 0.45      # below: red "Lücke"
SECURE = 0.7    # from here: green "sicher" (same as "Bausteine sicher" on home)
TREND_DAYS = 14
TREND_MIN_ANSWERS = 4
TREND_FLAT = 5  # percentage points that still count as "stabil"
DEFAULT_P = 0.3
UNTOUCHED = ("#f8fafc", "#e2e8f0", "#64748b")  # never practised: no evidence yet


def tone(p: float) -> tuple[str, str, str]:
    """(background, border, foreground) for a mastery value."""
    if p < GAP:
        return "#fef2f2", "#fecaca", "#dc2626"
    if p < SECURE:
        return "#fffbeb", "#fde68a", "#d97706"
    return "#f0fdf4", "#bbf7d0", "#16a34a"


def _status(p: float) -> str:
    return "Lücke" if p < GAP else "im Aufbau" if p < SECURE else "sicher"


def _title(skill: str) -> str:
    return SUBTOPIC_TITLES.get(skill) or SKILLS.get(skill, {}).get("name", skill)


def _parse(ts: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None


def _date(ts: str | None) -> str:
    d = _parse(ts)
    return d.strftime("%d.%m.") if d else ""


def _trends(answers: list[dict]) -> dict[str, dict]:
    """First-attempt hit rate per skill: last 14 days vs. the 4 weeks before.

    The window ends at the student's latest answer, not at "now", so an old
    database still shows how the student developed. Skills with fewer than
    four answers on either side get no trend instead of a noisy one; the
    sample sizes travel along so the UI can show them.
    """
    stamps = [d for d in (_parse(a["created"]) for a in answers) if d]
    if not stamps:
        return {}
    end = max(stamps)
    split = end - timedelta(days=TREND_DAYS)
    start = split - timedelta(days=2 * TREND_DAYS)
    recent: dict[str, list[int]] = {}
    before: dict[str, list[int]] = {}
    for a in answers:
        d = _parse(a["created"])
        if not d or d < start:
            continue
        (recent if d > split else before).setdefault(a["skill"], []).append(int(a["correct"]))
    out = {}
    for skill, now in recent.items():
        then = before.get(skill, [])
        if len(now) >= TREND_MIN_ANSWERS and len(then) >= TREND_MIN_ANSWERS:
            out[skill] = {"delta": round(100 * (sum(now) / len(now) - sum(then) / len(then))),
                          "n_recent": len(now), "n_before": len(then)}
    return out


def _trend_view(trend: dict | None) -> dict | None:
    if not trend:
        return None
    delta = trend["delta"]
    sample = f"aus {trend['n_recent']} neuen vs. {trend['n_before']} älteren Antworten"
    if delta >= TREND_FLAT:
        view = {"dir": "up", "arrow": "▲", "label": f"+{delta} Pkt."}
    elif delta <= -TREND_FLAT:
        view = {"dir": "down", "arrow": "▼", "label": f"−{abs(delta)} Pkt."}
    else:
        view = {"dir": "flat", "arrow": "▶", "label": "stabil"}
    return {**view, "delta": delta, "sample": sample}


def build(sid: int) -> dict | None:
    student = db.get_student(sid)
    if not student:
        return None

    detail = db.mastery_detail(sid)
    trends = _trends(db.first_attempts(sid))
    chats = db.chat_counts(sid)

    skills: dict[str, dict] = {}
    for skill, meta in VISIBLE_SKILLS.items():
        d = detail.get(skill, {})
        p = max(0.0, min(1.0, d.get("p", DEFAULT_P)))
        attempts, correct = d.get("attempts", 0), d.get("correct", 0)
        practised = attempts > 0
        bg, border, fg = tone(p) if practised else UNTOUCHED
        skills[skill] = {
            "id": skill, "title": _title(skill), "name": meta["name"], "topic": meta["topic"],
            "p": p, "pc": round(100 * p), "practised": practised,
            "status": _status(p) if practised else "noch nicht geübt",
            "bg": bg, "border": border, "fg": fg,
            "attempts": attempts, "correct": correct,
            "hit": round(100 * correct / attempts) if practised else None,
            "trend": _trend_view(trends.get(skill)),
            "chat": chats.get(skill, 0),
            "pre": [_title(x) for x in meta["pre"] if x in VISIBLE_SKILLS],
        }

    # Weak = the gap finder's line, weakest first, and only with evidence: a
    # skill nobody practised yet still sits at the 0.3 default and is not a gap.
    # A weak, practised prerequisite is the likely cause, like the class analysis.
    def is_weak(s: dict) -> bool:
        return s["practised"] and s["p"] < WEAK

    weak = []
    for row in sorted((s for s in skills.values() if is_weak(s)), key=lambda s: s["p"])[:4]:
        pre_weak = [x for x in VISIBLE_SKILLS[row["id"]]["pre"]
                    if x in skills and skills[x]["practised"] and skills[x]["p"] < WEAK + 0.05]
        root = min(pre_weak, key=lambda x: skills[x]["p"]) if pre_weak else None
        weak.append({**row, "root": skills[root]["title"] if root else None})

    strong = sorted((s for s in skills.values() if s["practised"] and s["p"] >= SECURE),
                    key=lambda s: -s["p"])[:3]
    untouched = [s for s in skills.values() if not s["practised"]]

    topics = []
    for topic in VISIBLE_TOPICS:
        rows = sorted((s for s in skills.values() if s["topic"] == topic),
                      key=lambda s: SUBTOPIC_ORDER.get(s["id"], len(SUBTOPIC_ORDER)))
        if not rows:
            continue
        pc = round(sum(s["pc"] for s in rows) / len(rows))
        bg, border, fg = tone(pc / 100)
        topics.append({"name": topic, "pc": pc, "fg": fg, "bg": bg, "skills": rows,
                       "gaps": sum(1 for s in rows if is_weak(s))})

    all_tests = db.student_tests(sid, limit=500)
    history = []
    for t in reversed(all_tests[:6]):
        if t["first_score"] is None:
            continue
        history.append({"id": t["id"], "date": _date(t["created"]), "score": t["first_score"],
                        "passed": t["first_score"] >= PASS_MARK, "note": note_for(t["first_score"]),
                        "pc": round(100 * t["first_score"] / 30)})
    latest = history[-1] if history else None

    mistakes = [{**m, "title": _title(m["skill"]), "date": _date(m["created"])}
                for m in db.recent_mistakes(sid)]

    if weak and weak[0]["root"]:
        next_step = (f"Erst „{weak[0]['root']}“ wiederholen – darauf baut "
                     f"„{weak[0]['title']}“ auf.")
    elif weak:
        next_step = (f"„{weak[0]['title']}“ gezielt üben – die 5 Zusatzfragen im nächsten Test "
                     f"fallen bevorzugt auf schwache Bausteine.")
    elif untouched:
        next_step = (f"Keine Lücke unter {round(100 * WEAK)} % – {len(untouched)} Bausteine sind aber "
                     f"noch nicht geübt. Ein neuer Test deckt alle ab.")
    else:
        next_step = f"Keine Lücke unter {round(100 * WEAK)} % – weiter so und die sicheren Bausteine wach halten."

    values = [s["p"] for s in skills.values()]
    return {
        "student": student,
        "overall": round(100 * sum(values) / len(values)) if values else 0,
        "secure": sum(1 for s in skills.values() if s["practised"] and s["p"] >= SECURE),
        "gaps": sum(1 for s in skills.values() if is_weak(s)),
        "untouched": len(untouched),
        "total": len(values),
        "weak": weak, "strong": strong, "topics": topics,
        "history": history, "latest": latest,
        "tests": sum(1 for t in all_tests if t["first_score"] is not None),
        "mistakes": mistakes, "next_step": next_step,
        "weak_line": round(100 * WEAK), "trend_days": TREND_DAYS,
        "pass_mark": PASS_MARK,
    }
