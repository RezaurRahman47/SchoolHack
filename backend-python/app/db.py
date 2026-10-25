"""SQLite storage + demo class seed data."""
from __future__ import annotations

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .questions import SKILLS, SUBTOPIC_TITLES, VISIBLE_SKILLS, PASS_MARK, note_for

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chemtutor.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE, klasse TEXT, is_demo INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS mastery (
    student_id INTEGER, skill TEXT, p REAL, attempts INTEGER DEFAULT 0, correct INTEGER DEFAULT 0,
    PRIMARY KEY (student_id, skill));
CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY, student_id INTEGER, created TEXT, questions TEXT,
    first_score INTEGER, final_round INTEGER DEFAULT 1, status TEXT DEFAULT 'open',
    kind TEXT DEFAULT 'test');
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY, test_id INTEGER, round INTEGER, qid TEXT, skill TEXT,
    given TEXT, correct INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY, student_id INTEGER, skill TEXT, role TEXT, message TEXT,
    sources TEXT, images TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS tutor_conversations (
    id INTEGER PRIMARY KEY, student_id INTEGER, subject TEXT DEFAULT 'science',
    title TEXT DEFAULT 'Neue Unterhaltung', created TEXT, updated TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS tutor_messages (
    id INTEGER PRIMARY KEY, conversation_id INTEGER, role TEXT, message TEXT,
    question TEXT, sources TEXT, images TEXT, created TEXT);
CREATE INDEX IF NOT EXISTS idx_tutor_conv_student ON tutor_conversations(student_id, updated);
CREATE INDEX IF NOT EXISTS idx_tutor_msg_conv ON tutor_messages(conversation_id, id);
"""

FIRST = ["Lena", "Jonas", "Mia", "Elias", "Emilia", "Noah", "Hannah", "Paul", "Lea", "Ben", "Sophie", "Finn",
         "Amira", "Luca", "Zeynep", "Leon", "Clara", "Yusuf", "Marie", "Tim", "Aylin", "Felix", "Nora", "Can"]
LAST = "ABCDEFGHIKLMNOPRSTUVWZYJ"


def conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    c = conn()
    c.executescript(SCHEMA)
    # Migration for databases created before image-bearing chat messages.
    cols = {row["name"] for row in c.execute("PRAGMA table_info(chat_messages)").fetchall()}
    if "images" not in cols:
        c.execute("ALTER TABLE chat_messages ADD COLUMN images TEXT")
    conv_cols = {row["name"] for row in c.execute("PRAGMA table_info(tutor_conversations)").fetchall()}
    if "sort_order" not in conv_cols:
        c.execute("ALTER TABLE tutor_conversations ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
    if "skill" not in conv_cols:
        # A conversation tied to one curriculum subtopic (sidebar group "Chemie").
        # NULL = a free chat, shown under "Allgemein".
        c.execute("ALTER TABLE tutor_conversations ADD COLUMN skill TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tutor_conv_skill ON tutor_conversations(student_id, skill)")
    test_cols = {row["name"] for row in c.execute("PRAGMA table_info(tests)").fetchall()}
    if "kind" not in test_cols:
        c.execute("ALTER TABLE tests ADD COLUMN kind TEXT DEFAULT 'test'")
    if c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        _seed(c)
    c.commit()
    c.close()


def _seed(c: sqlite3.Connection) -> None:
    rng = random.Random(9)
    # the logged-in demo student
    c.execute("INSERT INTO students (name, klasse, is_demo) VALUES ('admin', '9b', 0)")
    sid = c.execute("SELECT id FROM students WHERE name='admin'").fetchone()[0]
    for s in VISIBLE_SKILLS:
        c.execute("INSERT INTO mastery VALUES (?,?,?,0,0)", (sid, s, 0.3))

    # class-wide difficulty: some skills are systematically harder (gives the agent real gaps to find)
    difficulty = {s: 0.0 for s in SKILLS}
    difficulty.update({"konzentration": -0.28, "ph_rechnen": -0.32, "stoffmenge": -0.18,
                       "neutralisation": -0.22, "salzformel": -0.15, "alkan_name": -0.05,
                       "ester": -0.28, "fette": -0.22, "aminosaeuren": -0.20,
                       "carbonsaeure_eigenschaften": -0.15, "alkohol_herstellung": -0.10,
                       "ph_skala": 0.18, "indikator": 0.12, "alkan_formel": 0.08})
    now = datetime.now()
    for i, fn in enumerate(FIRST):
        name = f"{fn} {LAST[i]}."
        klasse = "9a" if i % 2 == 0 else "9b"
        ability = rng.uniform(0.5, 0.95)
        c.execute("INSERT INTO students (name, klasse) VALUES (?,?)", (name, klasse))
        stid = c.execute("SELECT id FROM students WHERE name=?", (name,)).fetchone()[0]
        probs = {}
        for s in VISIBLE_SKILLS:
            p = min(0.97, max(0.05, ability + difficulty[s] + rng.uniform(-0.12, 0.12)))
            probs[s] = p
            att = rng.randint(4, 10)
            cor = sum(rng.random() < p for _ in range(att))
            c.execute("INSERT INTO mastery VALUES (?,?,?,?,?)", (stid, s, round(p, 3), att, cor))
        # 6 weekly tests, slight improvement over time (30 questions each)
        plan = list(VISIBLE_SKILLS) * 2
        while len(plan) < 30:
            plan.append(rng.choice(list(VISIBLE_SKILLS)))
        for w in range(6):
            boost = w * 0.025
            score = sum(rng.random() < min(0.98, probs[s] + boost) for s in plan)
            score = min(30, score)
            created = (now - timedelta(weeks=5 - w, days=rng.randint(0, 2))).isoformat(timespec="minutes")
            c.execute("INSERT INTO tests (student_id, created, questions, first_score, final_round, status) "
                      "VALUES (?,?,?,?,?,?)", (stid, created, "[]", score, 1 + (score < 30), "done"))
            tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            for i, s in enumerate(plan):  # one answer per question
                ok = int(rng.random() < min(0.98, probs[s] + boost))
                c.execute("INSERT INTO answers (test_id, round, qid, skill, given, correct, created) "
                          "VALUES (?,?,?,?,?,?,?)", (tid, 1, f"{s}{i}", s, "", ok, created))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def student_id(name: str = "admin") -> int:
    c = conn()
    r = c.execute("SELECT id FROM students WHERE name=?", (name,)).fetchone()
    c.close()
    return r[0]


def get_mastery(sid: int) -> dict[str, float]:
    c = conn()
    rows = c.execute("SELECT skill, p FROM mastery WHERE student_id=?", (sid,)).fetchall()
    c.close()
    return {r["skill"]: r["p"] for r in rows}


def update_mastery(sid: int, skill: str, correct: bool) -> None:
    """Simple Elo-style update: move p toward 1 on correct, toward 0 on wrong."""
    c = conn()
    r = c.execute("SELECT p FROM mastery WHERE student_id=? AND skill=?", (sid, skill)).fetchone()
    p = r["p"] if r else 0.3
    p = p + 0.22 * (1 - p) if correct else p - 0.18 * p
    c.execute("INSERT INTO mastery (student_id, skill, p, attempts, correct) VALUES (?,?,?,1,?) "
              "ON CONFLICT(student_id, skill) DO UPDATE SET p=?, attempts=attempts+1, correct=correct+?",
              (sid, skill, p, int(correct), p, int(correct)))
    c.commit()
    c.close()


def create_test(sid: int, questions: list[dict], kind: str = "test") -> int:
    c = conn()
    c.execute("INSERT INTO tests (student_id, created, questions, kind) VALUES (?,?,?,?)",
              (sid, datetime.now().isoformat(timespec="minutes"),
               json.dumps(questions, ensure_ascii=False), kind))
    tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return tid


def get_test(tid: int) -> dict | None:
    c = conn()
    r = c.execute("SELECT * FROM tests WHERE id=?", (tid,)).fetchone()
    c.close()
    if not r:
        return None
    d = dict(r)
    d["questions"] = json.loads(d["questions"])
    return d


def save_answers(tid: int, rnd: int, rows: list[tuple[str, str, str, bool]]) -> None:
    c = conn()
    now = datetime.now().isoformat(timespec="minutes")
    c.executemany("INSERT INTO answers (test_id, round, qid, skill, given, correct, created) VALUES (?,?,?,?,?,?,?)",
                  [(tid, rnd, q, s, g, int(ok), now) for q, s, g, ok in rows])
    c.commit()
    c.close()


def answers_for(tid: int) -> list[dict]:
    c = conn()
    rows = c.execute("SELECT * FROM answers WHERE test_id=? ORDER BY round, id", (tid,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def update_test(tid: int, **kw) -> None:
    c = conn()
    sets = ", ".join(f"{k}=?" for k in kw)
    c.execute(f"UPDATE tests SET {sets} WHERE id=?", (*kw.values(), tid))
    c.commit()
    c.close()


def student_tests(sid: int, limit: int = 10) -> list[dict]:
    c = conn()
    rows = c.execute("SELECT id, created, first_score, final_round, status FROM tests "
                     "WHERE student_id=? AND kind='test' ORDER BY id DESC LIMIT ?", (sid, limit)).fetchall()
    c.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# per-student profile data (read-only; the profile itself is built in profile.py)
# ---------------------------------------------------------------------------
def get_student(sid: int) -> dict | None:
    c = conn()
    r = c.execute("SELECT id, name, klasse, is_demo FROM students WHERE id=?", (sid,)).fetchone()
    c.close()
    return dict(r) if r else None


def mastery_detail(sid: int) -> dict[str, dict]:
    """Mastery p plus the attempt counters update_mastery keeps per skill."""
    c = conn()
    rows = c.execute("SELECT skill, p, attempts, correct FROM mastery WHERE student_id=?", (sid,)).fetchall()
    c.close()
    return {r["skill"]: {"p": r["p"], "attempts": r["attempts"] or 0, "correct": r["correct"] or 0}
            for r in rows}


def first_attempts(sid: int) -> list[dict]:
    """Every first-round answer of the full tests, oldest first (for trends)."""
    c = conn()
    rows = c.execute("SELECT a.skill, a.correct, a.created FROM answers a JOIN tests t ON a.test_id=t.id "
                     "WHERE t.student_id=? AND t.kind='test' AND a.round=1 ORDER BY a.created, a.id",
                     (sid,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def recent_mistakes(sid: int, limit: int = 6, skill: str | None = None) -> list[dict]:
    """Latest wrong first-round answers that still have their question text.

    Seeded example tests store no questions, so they never show up here.
    ``fixed`` says whether a later round of the same test got it right.
    ``skill`` narrows it to one curriculum subtopic (for the tutor chat).
    """
    c = conn()
    rows = c.execute(
        "SELECT a.test_id, a.qid, a.skill, a.given, a.created, t.questions, "
        "EXISTS(SELECT 1 FROM answers b WHERE b.test_id=a.test_id AND b.qid=a.qid "
        "       AND b.round>1 AND b.correct=1) AS fixed "
        "FROM answers a JOIN tests t ON a.test_id=t.id "
        "WHERE t.student_id=? AND a.round=1 AND a.correct=0 AND t.questions != '[]' "
        "AND (? IS NULL OR a.skill=?) "
        "ORDER BY a.created DESC, a.id DESC LIMIT ?", (sid, skill, skill, limit * 4)).fetchall()
    c.close()
    out = []
    for r in rows:
        try:
            questions = {q["id"]: q for q in json.loads(r["questions"] or "[]")}
        except (TypeError, ValueError, KeyError):
            continue
        q = questions.get(r["qid"])
        if not q:
            continue
        out.append({"skill": r["skill"], "prompt": q.get("prompt", ""), "given": r["given"],
                    "answer": q.get("answer", ""), "unit": q.get("unit", ""),
                    "created": r["created"], "fixed": bool(r["fixed"])})
        if len(out) >= limit:
            break
    return out


def chat_counts(sid: int) -> dict[str, int]:
    """How often the student asked the chemistry chat about each skill."""
    c = conn()
    rows = c.execute("SELECT skill, COUNT(*) n FROM chat_messages WHERE student_id=? AND role='user' "
                     "GROUP BY skill", (sid,)).fetchall()
    c.close()
    return {r["skill"]: r["n"] for r in rows}


def save_chat_message(sid: int, skill: str, role: str, message: str,
                      sources: list | None = None, images: list | None = None) -> int:
    c = conn()
    now = datetime.now().isoformat(timespec="seconds")
    src_json = json.dumps(sources or [], ensure_ascii=False)
    img_json = json.dumps(images or [], ensure_ascii=False)
    c.execute(
        "INSERT INTO chat_messages (student_id, skill, role, message, sources, images, created) "
        "VALUES (?,?,?,?,?,?,?)",
        (sid, skill, role, message, src_json, img_json, now)
    )
    msg_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return msg_id


def get_chat_history(sid: int, skill: str, limit: int = 50) -> list[dict]:
    c = conn()
    # Take the newest messages, then restore chronological order for display.
    rows = c.execute(
        "SELECT * FROM ("
        "  SELECT id, student_id, skill, role, message, sources, images, created "
        "  FROM chat_messages WHERE student_id=? AND skill=? ORDER BY id DESC LIMIT ?"
        ") ORDER BY id ASC",
        (sid, skill, limit)
    ).fetchall()
    c.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["sources"] = json.loads(d["sources"]) if d["sources"] else []
        except Exception:
            d["sources"] = []
        try:
            d["images"] = json.loads(d["images"]) if d["images"] else []
        except Exception:
            d["images"] = []
        result.append(d)
    return result


def clear_chat_history(sid: int, skill: str) -> None:
    c = conn()
    c.execute("DELETE FROM chat_messages WHERE student_id=? AND skill=?", (sid, skill))
    c.commit()
    c.close()


# ---------------------------------------------------------------------------
# AI tutor conversations
# ---------------------------------------------------------------------------
def create_tutor_conversation(sid: int, subject: str = "science",
                              title: str = "Neue Unterhaltung", skill: str | None = None) -> int:
    c = conn()
    now = datetime.now().isoformat(timespec="seconds")
    position = c.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM tutor_conversations WHERE student_id=?",
        (sid,)
    ).fetchone()[0]
    c.execute("INSERT INTO tutor_conversations (student_id, subject, title, created, updated, sort_order, skill) "
              "VALUES (?,?,?,?,?,?,?)", (sid, subject, title, now, now, position, skill))
    cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return cid


def find_skill_conversation(sid: int, skill: str) -> int | None:
    """The student's conversation for one curriculum subtopic, if it exists."""
    c = conn()
    row = c.execute("SELECT id FROM tutor_conversations WHERE student_id=? AND skill=? "
                    "ORDER BY id LIMIT 1", (sid, skill)).fetchone()
    c.close()
    return row["id"] if row else None


def list_tutor_conversations(sid: int, limit: int = 50) -> list[dict]:
    c = conn()
    rows = c.execute(
        "SELECT c.id, c.title, c.subject, c.skill, c.created, c.updated, "
        "  (SELECT m.message FROM tutor_messages m "
        "   WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS preview "
        "FROM tutor_conversations c WHERE c.student_id=? "
        "ORDER BY c.sort_order DESC, c.updated DESC, c.id DESC LIMIT ?",
        (sid, limit)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def reorder_tutor_conversations(sid: int, ids: list[int]) -> None:
    c = conn()
    total = len(ids)
    for index, cid in enumerate(ids):
        c.execute("UPDATE tutor_conversations SET sort_order=? WHERE id=? AND student_id=?",
                  (total - index, cid, sid))
    c.commit()
    c.close()


def _parse_tutor_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in ("question", "sources", "images"):
        try:
            d[key] = json.loads(d[key]) if d.get(key) else (None if key == "question" else [])
        except Exception:
            d[key] = None if key == "question" else []
    return d


def get_tutor_messages(cid: int, sid: int, limit: int = 50) -> list[dict]:
    c = conn()
    owned = c.execute("SELECT 1 FROM tutor_conversations WHERE id=? AND student_id=?",
                      (cid, sid)).fetchone()
    if not owned:
        c.close()
        return []
    rows = c.execute(
        "SELECT * FROM ("
        "  SELECT id, conversation_id, role, message, question, sources, images, created "
        "  FROM tutor_messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?"
        ") ORDER BY id ASC", (cid, limit)
    ).fetchall()
    c.close()
    return [_parse_tutor_row(r) for r in rows]


def get_tutor_conversation(cid: int, sid: int) -> dict | None:
    c = conn()
    row = c.execute(
        "SELECT id, student_id, subject, skill, title, created, updated "
        "FROM tutor_conversations WHERE id=? AND student_id=?", (cid, sid)
    ).fetchone()
    c.close()
    if not row:
        return None
    conversation = dict(row)
    conversation["messages"] = get_tutor_messages(cid, sid)
    return conversation


def add_tutor_message(cid: int, role: str, message: str, question: dict | None = None,
                      sources: list | None = None, images: list | None = None) -> int:
    c = conn()
    now = datetime.now().isoformat(timespec="seconds")
    c.execute(
        "INSERT INTO tutor_messages (conversation_id, role, message, question, sources, images, created) "
        "VALUES (?,?,?,?,?,?,?)",
        (cid, role, message,
         json.dumps(question, ensure_ascii=False) if question else None,
         json.dumps(sources or [], ensure_ascii=False),
         json.dumps(images or [], ensure_ascii=False), now)
    )
    mid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("UPDATE tutor_conversations SET updated=? WHERE id=?", (now, cid))
    c.commit()
    c.close()
    return mid


def update_tutor_conversation(cid: int, sid: int, subject: str | None = None,
                              title: str | None = None) -> None:
    sets, args = ["updated=?"], [datetime.now().isoformat(timespec="seconds")]
    if subject is not None:
        sets.append("subject=?")
        args.append(subject)
    if title is not None:
        sets.append("title=?")
        args.append(title[:80])
    args.extend([cid, sid])
    c = conn()
    c.execute(f"UPDATE tutor_conversations SET {', '.join(sets)} WHERE id=? AND student_id=?", args)
    c.commit()
    c.close()


def delete_tutor_conversation(cid: int, sid: int) -> None:
    c = conn()
    owned = c.execute("SELECT 1 FROM tutor_conversations WHERE id=? AND student_id=?",
                      (cid, sid)).fetchone()
    if owned:
        c.execute("DELETE FROM tutor_messages WHERE conversation_id=?", (cid,))
        c.execute("DELETE FROM tutor_conversations WHERE id=? AND student_id=?", (cid, sid))
        c.commit()
    c.close()


# ---------------------------------------------------------------------------
# class analytics for the teacher dashboard
# ---------------------------------------------------------------------------
def class_overview(klasse: str | None = None) -> dict:
    c = conn()
    where, args = ("WHERE s.klasse=?", (klasse,)) if klasse else ("", ())
    students = [dict(r) for r in c.execute(f"SELECT * FROM students s {where} ORDER BY name", args)]
    ids = [s["id"] for s in students]
    q = ",".join("?" * len(ids)) or "NULL"

    # latest finished test per student
    latest = {r["student_id"]: dict(r) for r in c.execute(
        f"SELECT t.* FROM tests t JOIN (SELECT student_id, MAX(id) mid FROM tests "
        f"WHERE status='done' AND kind='test' GROUP BY student_id) x ON t.id = x.mid "
        f"WHERE t.student_id IN ({q})", ids)}

    mastery: dict[int, dict[str, float]] = {}
    practised: dict[int, set[str]] = {}
    for r in c.execute(f"SELECT student_id, skill, p, attempts FROM mastery WHERE student_id IN ({q})", ids):
        mastery.setdefault(r["student_id"], {})[r["skill"]] = r["p"]
        if r["attempts"]:
            practised.setdefault(r["student_id"], set()).add(r["skill"])

    skill_stats = {s: {"correct": 0, "wrong": 0} for s in VISIBLE_SKILLS}
    for r in c.execute(f"SELECT a.skill, SUM(a.correct) c, COUNT(*) n FROM answers a JOIN tests t ON a.test_id=t.id "
                       f"WHERE t.student_id IN ({q}) AND t.kind='test' AND a.round=1 GROUP BY a.skill", ids):
        if r["skill"] in skill_stats:
            skill_stats[r["skill"]] = {"correct": r["c"], "wrong": r["n"] - r["c"]}

    # weekly pass rate trend
    trend = []
    for r in c.execute(f"SELECT strftime('%Y-%W', created) wk, AVG(first_score >= ?) pr, AVG(first_score) avg "
                       f"FROM tests WHERE status='done' AND kind='test' AND student_id IN ({q}) "
                       f"GROUP BY wk ORDER BY wk", (PASS_MARK, *ids)):
        trend.append({"week": r["wk"], "pass_rate": round(100 * r["pr"]), "avg": round(r["avg"], 1)})
    c.close()

    rows = []
    for s in students:
        t = latest.get(s["id"])
        m = mastery.get(s["id"], {})
        visible = {k: v for k, v in m.items()
                   if k in VISIBLE_SKILLS and k in practised.get(s["id"], set())}
        weakest = min(visible, key=visible.get) if visible else None
        rows.append({"id": s["id"], "name": "Du (admin)" if s["name"] == "admin" else s["name"],
                     "klasse": s["klasse"], "score": t["first_score"] if t else None,
                     "passed": (t["first_score"] >= PASS_MARK) if t else None,
                     "note": note_for(t["first_score"]) if t else None,
                     "weakest": ({"skill": weakest,
                                  "name": SUBTOPIC_TITLES.get(weakest) or SKILLS[weakest]["name"],
                                  "p": round(100 * visible[weakest])} if weakest else None),
                     "mastery": m, "avg_mastery": round(100 * sum(m.values()) / max(len(m), 1)),
                     # Same "Lernstand" as the home radar and the profile: all
                     # visible skills, untouched ones at the 0.3 start value.
                     "lernstand": round(100 * sum(m.get(k, 0.3) for k in VISIBLE_SKILLS)
                                        / max(len(VISIBLE_SKILLS), 1))})
    scored = [r for r in rows if r["score"] is not None]
    passed = sum(1 for r in scored if r["passed"])
    return {
        "students": rows,
        "skill_stats": skill_stats,
        "trend": trend[-6:],
        "kpi": {
            "students": len(rows),
            "tests": len(scored),
            "pass_rate": round(100 * passed / max(len(scored), 1)),
            "avg_score": round(sum(r["score"] for r in scored) / max(len(scored), 1), 1),
            "passed": passed, "failed": len(scored) - passed,
            "at_risk": sum(1 for r in scored if r["score"] < PASS_MARK),
        },
    }
