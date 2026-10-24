"""SQLite storage + demo class seed data."""
from __future__ import annotations

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .questions import SKILLS, PASS_MARK

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chemtutor.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE, klasse TEXT, is_demo INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS mastery (
    student_id INTEGER, skill TEXT, p REAL, attempts INTEGER DEFAULT 0, correct INTEGER DEFAULT 0,
    PRIMARY KEY (student_id, skill));
CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY, student_id INTEGER, created TEXT, questions TEXT,
    first_score INTEGER, final_round INTEGER DEFAULT 1, status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY, test_id INTEGER, round INTEGER, qid TEXT, skill TEXT,
    given TEXT, correct INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY, student_id INTEGER, skill TEXT, role TEXT, message TEXT,
    sources TEXT, images TEXT, created TEXT);
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
    if c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        _seed(c)
    c.commit()
    c.close()


def _seed(c: sqlite3.Connection) -> None:
    rng = random.Random(9)
    # the logged-in demo student
    c.execute("INSERT INTO students (name, klasse, is_demo) VALUES ('admin', '9b', 0)")
    sid = c.execute("SELECT id FROM students WHERE name='admin'").fetchone()[0]
    for s in SKILLS:
        c.execute("INSERT INTO mastery VALUES (?,?,?,0,0)", (sid, s, 0.3))

    # class-wide difficulty: some skills are systematically harder (gives the agent real gaps to find)
    difficulty = {s: 0.0 for s in SKILLS}
    difficulty.update({"konzentration": -0.28, "ph_rechnen": -0.32, "stoffmenge": -0.18,
                       "neutralisation": -0.22, "salzformel": -0.15, "alkan_name": -0.05,
                       "ph_skala": 0.18, "indikator": 0.12, "alkan_formel": 0.08})
    now = datetime.now()
    for i, fn in enumerate(FIRST):
        name = f"{fn} {LAST[i]}."
        klasse = "9a" if i % 2 == 0 else "9b"
        ability = rng.uniform(0.5, 0.95)
        c.execute("INSERT INTO students (name, klasse) VALUES (?,?)", (name, klasse))
        stid = c.execute("SELECT id FROM students WHERE name=?", (name,)).fetchone()[0]
        probs = {}
        for s in SKILLS:
            p = min(0.97, max(0.05, ability + difficulty[s] + rng.uniform(-0.12, 0.12)))
            probs[s] = p
            att = rng.randint(4, 10)
            cor = sum(rng.random() < p for _ in range(att))
            c.execute("INSERT INTO mastery VALUES (?,?,?,?,?)", (stid, s, round(p, 3), att, cor))
        # 6 weekly tests, slight improvement over time
        for w in range(6):
            boost = w * 0.025
            score = sum(rng.random() < min(0.98, probs[s] + boost) for s in list(SKILLS) * 2)
            score = min(30, score)
            created = (now - timedelta(weeks=5 - w, days=rng.randint(0, 2))).isoformat(timespec="minutes")
            c.execute("INSERT INTO tests (student_id, created, questions, first_score, final_round, status) "
                      "VALUES (?,?,?,?,?,?)", (stid, created, "[]", score, 1 + (score < 30), "done"))
            tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            for s in SKILLS:  # 2 answers per skill per test
                for k in range(2):
                    ok = int(rng.random() < min(0.98, probs[s] + boost))
                    c.execute("INSERT INTO answers (test_id, round, qid, skill, given, correct, created) "
                              "VALUES (?,?,?,?,?,?,?)", (tid, 1, f"{s}{k}", s, "", ok, created))


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


def create_test(sid: int, questions: list[dict]) -> int:
    c = conn()
    c.execute("INSERT INTO tests (student_id, created, questions) VALUES (?,?,?)",
              (sid, datetime.now().isoformat(timespec="minutes"), json.dumps(questions, ensure_ascii=False)))
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
    rows = c.execute("SELECT id, created, first_score, final_round, status FROM tests WHERE student_id=? "
                     "ORDER BY id DESC LIMIT ?", (sid, limit)).fetchall()
    c.close()
    return [dict(r) for r in rows]


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
    rows = c.execute(
        "SELECT id, student_id, skill, role, message, sources, images, created FROM chat_messages "
        "WHERE student_id=? AND skill=? ORDER BY id ASC LIMIT ?",
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
        f"SELECT t.* FROM tests t JOIN (SELECT student_id, MAX(id) mid FROM tests WHERE status='done' "
        f"GROUP BY student_id) x ON t.id = x.mid WHERE t.student_id IN ({q})", ids)}

    mastery: dict[int, dict[str, float]] = {}
    for r in c.execute(f"SELECT student_id, skill, p FROM mastery WHERE student_id IN ({q})", ids):
        mastery.setdefault(r["student_id"], {})[r["skill"]] = r["p"]

    skill_stats = {s: {"correct": 0, "wrong": 0} for s in SKILLS}
    for r in c.execute(f"SELECT a.skill, SUM(a.correct) c, COUNT(*) n FROM answers a JOIN tests t ON a.test_id=t.id "
                       f"WHERE t.student_id IN ({q}) AND a.round=1 GROUP BY a.skill", ids):
        if r["skill"] in skill_stats:
            skill_stats[r["skill"]] = {"correct": r["c"], "wrong": r["n"] - r["c"]}

    # weekly pass rate trend
    trend = []
    for r in c.execute(f"SELECT strftime('%Y-%W', created) wk, AVG(first_score >= ?) pr, AVG(first_score) avg "
                       f"FROM tests WHERE status='done' AND student_id IN ({q}) GROUP BY wk ORDER BY wk",
                       (PASS_MARK, *ids)):
        trend.append({"week": r["wk"], "pass_rate": round(100 * r["pr"]), "avg": round(r["avg"], 1)})
    c.close()

    rows = []
    for s in students:
        t = latest.get(s["id"])
        m = mastery.get(s["id"], {})
        rows.append({"id": s["id"], "name": "Du (admin)" if s["name"] == "admin" else s["name"],
                     "klasse": s["klasse"], "score": t["first_score"] if t else None,
                     "passed": (t["first_score"] >= PASS_MARK) if t else None,
                     "mastery": m, "avg_mastery": round(100 * sum(m.values()) / max(len(m), 1))})
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
