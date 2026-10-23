"""School Hack – FastAPI app (teacher + student portals)."""
from __future__ import annotations

import random
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import agent, db, llm
from .questions import PASS_MARK, SKILLS, TOPICS, build_test, grade

BASE = Path(__file__).resolve().parent
app = FastAPI(title="School Hack")
app.add_middleware(SessionMiddleware, secret_key="chemtutor-hackathon-demo", max_age=60 * 60 * 12)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
tpl = Jinja2Templates(directory=BASE / "templates")

# Demo credentials (same for both portals, as requested). Replace before real use.
USERS = {"student": {"admin": "admin"}, "teacher": {"admin": "admin"}}

SUBJECTS = [
    {"slug": "chemie", "name": "Chemie", "icon": "⚗️", "active": True, "desc": "Säuren & Laugen, Mol, Alkane"},
    {"slug": "mathematik", "name": "Mathematik", "icon": "∑", "active": False, "desc": "Bald verfügbar"},
    {"slug": "biologie", "name": "Biologie", "icon": "🧬", "active": False, "desc": "Bald verfügbar"},
    {"slug": "physik", "name": "Physik", "icon": "⚛", "active": False, "desc": "Bald verfügbar"},
]


@app.on_event("startup")
def _startup() -> None:
    db.init()


def role(request: Request) -> str | None:
    return request.session.get("role")


def need(request: Request, r: str):
    if role(request) != r:
        return RedirectResponse(f"/login/{r}", status_code=303)
    return None


def render(request: Request, name: str, **ctx):
    return tpl.TemplateResponse(request, name, {"role": role(request), "llm": llm.available(), **ctx})


# ---------------------------------------------------------------------------
# public + auth
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return render(request, "landing.html")


@app.get("/login/{who}", response_class=HTMLResponse)
def login_page(request: Request, who: str):
    if who not in USERS:
        return RedirectResponse("/", 303)
    return render(request, "login.html", who=who, error=None)


@app.post("/login/{who}")
def login(request: Request, who: str, username: str = Form(...), password: str = Form(...)):
    if who in USERS and USERS[who].get(username) == password:
        request.session.clear()
        request.session.update(role=who, user=username)
        return RedirectResponse("/teacher" if who == "teacher" else "/student", 303)
    return render(request, "login.html", who=who, error="Benutzername oder Passwort falsch.")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", 303)


# ---------------------------------------------------------------------------
# student portal
# ---------------------------------------------------------------------------
@app.get("/student", response_class=HTMLResponse)
def student_home(request: Request):
    if (r := need(request, "student")):
        return r
    return render(request, "student_home.html", subjects=SUBJECTS)


@app.get("/student/chemie", response_class=HTMLResponse)
def chemie(request: Request):
    if (r := need(request, "student")):
        return r
    sid = db.student_id()
    m = db.get_mastery(sid)
    nodes = [{"id": k, "name": v["name"], "topic": v["topic"], "pre": v["pre"], "p": round(m.get(k, 0.3), 2)}
             for k, v in SKILLS.items()]
    return render(request, "chemie.html", nodes=nodes, topics=TOPICS, tests=db.student_tests(sid),
                  pass_mark=PASS_MARK)


@app.post("/student/test/new")
def new_test(request: Request):
    if (r := need(request, "student")):
        return r
    sid = db.student_id()
    qs = build_test(random.randrange(10**9), 30, db.get_mastery(sid))
    tid = db.create_test(sid, [q.to_dict() for q in qs])
    return RedirectResponse(f"/student/test/{tid}", 303)


def _round_state(test: dict) -> tuple[int, list[dict], list[dict]]:
    """Return (current_round, questions_for_round, answers)."""
    ans = db.answers_for(test["id"])
    qs = {q["id"]: q for q in test["questions"]}
    if not ans:
        return 1, test["questions"], ans
    last = max(a["round"] for a in ans)
    wrong = [a["qid"] for a in ans if a["round"] == last and not a["correct"]]
    return last + 1, [qs[q] for q in wrong], ans


@app.get("/student/test/{tid}", response_class=HTMLResponse)
def take_test(request: Request, tid: int):
    if (r := need(request, "student")):
        return r
    test = db.get_test(tid)
    if not test:
        return RedirectResponse("/student/chemie", 303)
    rnd, qs, ans = _round_state(test)
    if not qs:
        return RedirectResponse(f"/student/test/{tid}/result", 303)
    # in retry rounds, show the previous wrong answer + error feedback
    prev = {}
    if rnd > 1:
        for a in ans:
            if a["round"] == rnd - 1:
                q = next(q for q in test["questions"] if q["id"] == a["qid"])
                prev[a["qid"]] = {"given": a["given"], "feedback": grade(q, a["given"])[1]}
    return render(request, "test.html", test=test, round=rnd, questions=qs, prev=prev, skills=SKILLS)


@app.post("/student/test/{tid}")
async def submit_test(request: Request, tid: int):
    if (r := need(request, "student")):
        return r
    test = db.get_test(tid)
    rnd, qs, _ = _round_state(test)
    form = await request.form()
    sid = db.student_id()
    rows = []
    for q in qs:
        given = str(form.get(q["id"], ""))
        ok, _ = grade(q, given)
        rows.append((q["id"], q["skill"], given, ok))
        db.update_mastery(sid, q["skill"], ok)
    db.save_answers(tid, rnd, rows)
    if rnd == 1:
        db.update_test(tid, first_score=sum(ok for *_, ok in rows), status="done")
    db.update_test(tid, final_round=rnd)
    return RedirectResponse(f"/student/test/{tid}/result", 303)


@app.get("/student/test/{tid}/result", response_class=HTMLResponse)
def result(request: Request, tid: int):
    if (r := need(request, "student")):
        return r
    test = db.get_test(tid)
    ans = db.answers_for(tid)
    if not ans:
        return RedirectResponse(f"/student/test/{tid}", 303)
    qs = {q["id"]: q for q in test["questions"]}
    last = max(a["round"] for a in ans)
    last_rows = [a for a in ans if a["round"] == last]
    wrong = [a for a in last_rows if not a["correct"]]
    first = test["first_score"] or 0
    by_skill: dict[str, list[int]] = {}
    for a in ans:
        if a["round"] == 1:
            by_skill.setdefault(a["skill"], []).append(a["correct"])
    skill_rows = sorted(({"name": SKILLS[s]["name"], "correct": sum(v), "total": len(v)} for s, v in by_skill.items()),
                        key=lambda x: x["correct"] / x["total"])
    review = [{"q": qs[a["qid"]], "given": a["given"], "feedback": grade(qs[a["qid"]], a["given"])[1]} for a in wrong]
    return render(request, "result.html", test=test, first=first, passed=first >= PASS_MARK, pass_mark=PASS_MARK,
                  round=last, remaining=len(wrong), last_total=len(last_rows), review=review, skill_rows=skill_rows)


@app.post("/api/hint")
async def hint(request: Request):
    if role(request) != "student":
        return JSONResponse({"error": "login"}, 401)
    body = await request.json()
    test = db.get_test(int(body["test_id"]))
    q = next((q for q in test["questions"] if q["id"] == body["qid"]), None)
    if not q:
        return JSONResponse({"error": "not found"}, 404)
    given = body.get("given") or None
    err = grade(q, given)[1] if given else None
    return {"hint": llm.tutor_hint(q, given, int(body.get("attempt", 1)), err)}


# ---------------------------------------------------------------------------
# teacher portal
# ---------------------------------------------------------------------------
@app.get("/teacher", response_class=HTMLResponse)
def teacher(request: Request):
    if (r := need(request, "teacher")):
        return r
    return render(request, "teacher.html", skills=SKILLS, pass_mark=PASS_MARK)


@app.get("/api/teacher/overview")
def overview(request: Request, klasse: str | None = None):
    if role(request) != "teacher":
        return JSONResponse({"error": "login"}, 401)
    data = db.class_overview(klasse or None)
    data["skills"] = {k: v["name"] for k, v in SKILLS.items()}
    data["pass_mark"] = PASS_MARK
    return data


@app.post("/api/agent")
def run_agent(request: Request, klasse: str | None = None):
    if role(request) != "teacher":
        return JSONResponse({"error": "login"}, 401)
    return agent.run(klasse or None)


# ---------------------------------------------------------------------------
# PWA: installable on laptop + phone
# ---------------------------------------------------------------------------
@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(BASE / "static" / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(BASE / "static" / "sw.js", media_type="application/javascript")
