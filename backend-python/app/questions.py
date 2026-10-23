"""Question engine for Klasse 9 Chemie (RLP Berlin-Brandenburg).

Every question is generated from a parameterised template and graded in code.
The LLM is only used for hints/explanations, never to decide correctness.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# Skill graph: id -> (name, topic, prerequisites)
# ---------------------------------------------------------------------------
SKILLS: dict[str, dict] = {
    "ionen":        {"name": "Ionenladung bestimmen",        "topic": "Grundlagen",          "pre": []},
    "salzformel":   {"name": "Salzformeln aufstellen",       "topic": "Grundlagen",          "pre": ["ionen"]},
    "ph_skala":     {"name": "pH-Skala einordnen",           "topic": "Säuren und Laugen",   "pre": []},
    "indikator":    {"name": "Indikatorfarben deuten",       "topic": "Säuren und Laugen",   "pre": ["ph_skala"]},
    "saeurebildung":{"name": "Säurebildung (Oxid + Wasser)", "topic": "Säuren und Laugen",   "pre": ["ionen"]},
    "laugenbildung":{"name": "Laugenbildung (Oxid + Wasser)","topic": "Säuren und Laugen",   "pre": ["ionen"]},
    "saeure_metall":{"name": "Säure + Metall / Carbonat",    "topic": "Säuren und Laugen",   "pre": ["saeurebildung"]},
    "neutralisation":{"name": "Neutralisation: Salz benennen","topic": "Säuren und Laugen",  "pre": ["salzformel", "saeurebildung", "laugenbildung"]},
    "molare_masse": {"name": "Molare Masse berechnen",       "topic": "Stoffmenge und Mol",  "pre": []},
    "stoffmenge":   {"name": "Stoffmenge n = m / M",         "topic": "Stoffmenge und Mol",  "pre": ["molare_masse"]},
    "konzentration":{"name": "Konzentration c = n / V",      "topic": "Stoffmenge und Mol",  "pre": ["stoffmenge"]},
    "ph_rechnen":   {"name": "pH-Wert berechnen",            "topic": "Säuren und Laugen",   "pre": ["konzentration", "ph_skala"]},
    "alkan_formel": {"name": "Alkane: Summenformel",         "topic": "Kohlenwasserstoffe",  "pre": []},
    "alkan_name":   {"name": "Alkane: Namen (IUPAC)",        "topic": "Kohlenwasserstoffe",  "pre": ["alkan_formel"]},
    "siedetrend":   {"name": "Siedepunkte & Van-der-Waals",  "topic": "Kohlenwasserstoffe",  "pre": ["alkan_formel"]},
}

TOPICS = ["Grundlagen", "Säuren und Laugen", "Stoffmenge und Mol", "Kohlenwasserstoffe"]

ATOMIC_MASS = {"H": 1.0, "C": 12.0, "N": 14.0, "O": 16.0, "Na": 23.0, "Mg": 24.3,
               "Al": 27.0, "S": 32.1, "Cl": 35.5, "K": 39.1, "Ca": 40.1}

ALKANES = ["Methan", "Ethan", "Propan", "Butan", "Pentan", "Hexan", "Heptan", "Octan", "Nonan", "Decan"]
BOILING = {"Methan": -162, "Ethan": -89, "Propan": -42, "Butan": -1, "Pentan": 36,
           "Hexan": 69, "Heptan": 98, "Octan": 126, "Nonan": 151, "Decan": 174}

CATIONS = [("Na", 1, "Natrium"), ("K", 1, "Kalium"), ("Mg", 2, "Magnesium"),
           ("Ca", 2, "Calcium"), ("Al", 3, "Aluminium")]
ANIONS = [("Cl", 1, "chlorid"), ("O", 2, "oxid"), ("S", 2, "sulfid")]

ACIDS = [  # name, formula, anion name (salt suffix), protons
    ("Salzsäure", "HCl", "chlorid", 1),
    ("Schwefelsäure", "H₂SO₄", "sulfat", 2),
    ("Salpetersäure", "HNO₃", "nitrat", 1),
    ("Kohlensäure", "H₂CO₃", "carbonat", 2),
]
BASES = [("Natronlauge", "Natrium"), ("Kalilauge", "Kalium"), ("Kalkwasser", "Calcium")]


@dataclass
class Question:
    id: str
    skill: str
    kind: str              # "mc" or "num"
    prompt: str
    answer: str            # canonical answer (string; numeric as str)
    options: list[str] = field(default_factory=list)
    tolerance: float = 0.0  # relative tolerance for numeric
    unit: str = ""
    explanation: str = ""
    # wrong answer -> error type, used for targeted feedback
    traps: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _sub(n: int) -> str:
    return "" if n == 1 else str(n).translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉"))


def _mc(options: list[str], answer: str, rng: random.Random) -> list[str]:
    opts = list(dict.fromkeys([answer] + [o for o in options if o != answer]))[:4]
    rng.shuffle(opts)
    return opts


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
def q_ionen(rng):
    sym, charge, name = rng.choice(CATIONS + [(a[0], -a[1], a[2]) for a in ANIONS])
    if charge > 0:
        ans = f"{sym}{'' if charge == 1 else charge}+"
        wrong = [f"{sym}{'' if charge == 1 else charge}-", f"{sym}{charge + 1}+", f"{sym}{max(1, charge - 1) if charge > 1 else 2}+"]
        expl = f"{name} steht in der {charge}. Hauptgruppe und gibt {charge} Außenelektron(en) ab."
    else:
        c = -charge
        ans = f"{sym}{'' if c == 1 else c}-"
        wrong = [f"{sym}{'' if c == 1 else c}+", f"{sym}{c + 1}-", f"{sym}{8 - c}-"]
        expl = f"{sym} nimmt {c} Elektron(en) auf, um das Oktett zu erreichen."
    return Question("", "ionen", "mc", f"Welches Ion bildet ein {sym}-Atom?", ans,
                    _mc(wrong, ans, rng), explanation=expl,
                    traps={wrong[0]: "Vorzeichen vertauscht: Metalle geben Elektronen ab (positiv), Nichtmetalle nehmen auf (negativ)."})


def q_salzformel(rng):
    (cs, cc, cn), (asym, ac, an) = rng.choice(CATIONS), rng.choice(ANIONS)
    l = math.lcm(cc, ac)
    nc, na = l // cc, l // ac
    ans = f"{cs}{_sub(nc)}{asym}{_sub(na)}"
    wrong = {f"{cs}{asym}{_sub(cc)}" if cc != 1 else f"{cs}{asym}₂": "Ladungen nicht ausgeglichen.",
             f"{cs}{_sub(ac)}{asym}{_sub(cc)}" if (ac, cc) != (nc, na) else f"{cs}₂{asym}₃": "Indizes falsch gekreuzt.",
             f"{cs}{asym}": "Ionenladungen nicht berücksichtigt."}
    wrong = {k: v for k, v in wrong.items() if k != ans}
    name = cn + an
    return Question("", "salzformel", "mc", f"Wie lautet die Formel von {name}?", ans,
                    _mc(list(wrong) + [f"{cs}₃{asym}₂"], ans, rng),
                    explanation=f"{cs}{'' if cc == 1 else cc}+ und {asym}{'' if ac == 1 else ac}-: Kleinstes gemeinsames Vielfaches {l} → {nc}:{na}.",
                    traps=wrong)


def q_ph_skala(rng):
    ph = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
    ans = "sauer" if ph < 7 else ("neutral" if ph == 7 else "basisch (alkalisch)")
    stuff = {1: "Magensäure", 2: "Zitronensaft", 3: "Cola", 4: "Orangensaft", 5: "Kaffee", 6: "Milch",
             7: "reines Wasser", 8: "Meerwasser", 9: "Natronlösung", 10: "Seifenlauge", 11: "Ammoniaklösung",
             12: "Kalkwasser", 13: "Rohrreiniger"}[ph]
    return Question("", "ph_skala", "mc", f"{stuff} hat einen pH-Wert von etwa {ph}. Wie reagiert die Lösung?", ans,
                    _mc(["sauer", "neutral", "basisch (alkalisch)"], ans, rng),
                    explanation="pH < 7 sauer, pH = 7 neutral, pH > 7 basisch.",
                    traps={"basisch (alkalisch)" if ph < 7 else "sauer": "Skala falsch herum gelesen: kleine pH-Werte sind sauer."})


def q_indikator(rng):
    ind, case = rng.choice([
        ("Universalindikator", ("sauer", "rot")), ("Universalindikator", ("neutral", "grün")),
        ("Universalindikator", ("basisch", "blau/violett")),
        ("Phenolphthalein", ("basisch", "pink")), ("Phenolphthalein", ("sauer", "farblos")),
        ("Rotkohlsaft", ("sauer", "rot")), ("Rotkohlsaft", ("basisch", "grün/gelb")),
    ])
    lsg, color = case
    all_colors = ["rot", "grün", "blau/violett", "pink", "farblos", "grün/gelb", "orange"]
    return Question("", "indikator", "mc", f"Welche Farbe zeigt {ind} in einer {lsg}en Lösung?", color,
                    _mc(rng.sample([c for c in all_colors if c != color], 3), color, rng),
                    explanation=f"{ind} färbt sich in {lsg}er Lösung {color}.")


def q_saeurebildung(rng):
    oxid, acid = rng.choice([("Schwefeldioxid (SO₂)", "Schweflige Säure (H₂SO₃)"),
                             ("Schwefeltrioxid (SO₃)", "Schwefelsäure (H₂SO₄)"),
                             ("Kohlenstoffdioxid (CO₂)", "Kohlensäure (H₂CO₃)")])
    opts = ["Schweflige Säure (H₂SO₃)", "Schwefelsäure (H₂SO₄)", "Kohlensäure (H₂CO₃)", "Natronlauge (NaOH)"]
    return Question("", "saeurebildung", "mc", f"{oxid} reagiert mit Wasser. Welche Lösung entsteht?", acid,
                    _mc(opts, acid, rng), explanation="Nichtmetalloxid + Wasser → saure Lösung.",
                    traps={"Natronlauge (NaOH)": "Nichtmetalloxide bilden Säuren, nur Metalloxide bilden Laugen."})


def q_laugenbildung(rng):
    oxid, base = rng.choice([("Natriumoxid (Na₂O)", "Natronlauge (NaOH)"),
                             ("Calciumoxid (CaO)", "Kalkwasser (Ca(OH)₂)"),
                             ("Kaliumoxid (K₂O)", "Kalilauge (KOH)")])
    opts = ["Natronlauge (NaOH)", "Kalkwasser (Ca(OH)₂)", "Kalilauge (KOH)", "Kohlensäure (H₂CO₃)"]
    return Question("", "laugenbildung", "mc", f"{oxid} reagiert mit Wasser. Welche Lösung entsteht?", base,
                    _mc(opts, base, rng), explanation="Metalloxid + Wasser → Hydroxid (Lauge).",
                    traps={"Kohlensäure (H₂CO₃)": "Metalloxide bilden Laugen, keine Säuren."})


def q_saeure_metall(rng):
    if rng.random() < 0.5:
        metal = rng.choice(["Zink", "Magnesium", "Eisen"])
        return Question("", "saeure_metall", "mc", f"{metal} reagiert mit Salzsäure. Welches Gas entsteht?", "Wasserstoff",
                        _mc(["Sauerstoff", "Kohlenstoffdioxid", "Chlor"], "Wasserstoff", rng),
                        explanation="Unedles Metall + Säure → Salz + Wasserstoff (Knallgasprobe).",
                        traps={"Sauerstoff": "Die Säure liefert H⁺-Ionen, daraus entsteht H₂, nicht O₂."})
    carb = rng.choice(["Kalk (Calciumcarbonat)", "Natron (Natriumhydrogencarbonat)"])
    return Question("", "saeure_metall", "mc", f"Säure tropft auf {carb}. Welches Gas sprudelt heraus?", "Kohlenstoffdioxid",
                    _mc(["Wasserstoff", "Sauerstoff", "Stickstoff"], "Kohlenstoffdioxid", rng),
                    explanation="Carbonat + Säure → Salz + Wasser + CO₂ (Kalkwassertrübung).",
                    traps={"Wasserstoff": "Wasserstoff entsteht mit Metallen; Carbonate setzen CO₂ frei."})


def q_neutralisation(rng):
    aname, _, anion, _ = rng.choice(ACIDS[:3])
    bname, cation = rng.choice(BASES)
    ans = f"{cation}{anion} + Wasser"
    wrong = {f"{cation}{anion} + Wasserstoff": "Bei der Neutralisation entsteht Wasser, kein Wasserstoff-Gas.",
             f"{cation}hydroxid + Wasser": "Das Hydroxid ist der Ausgangsstoff, nicht das Produkt.",
             f"{cation}oxid + Wasser": "Salze der Säure benennen, nicht das Oxid."}
    return Question("", "neutralisation", "mc", f"{aname} wird mit {bname} neutralisiert. Was entsteht?", ans,
                    _mc(list(wrong), ans, rng), explanation="Säure + Lauge → Salz + Wasser (H⁺ + OH⁻ → H₂O).",
                    traps=wrong)


def _molar_mass(formula: list[tuple[str, int]]) -> float:
    return sum(ATOMIC_MASS[e] * n for e, n in formula)


COMPOUNDS = [
    ("H₂O", [("H", 2), ("O", 1)]), ("CO₂", [("C", 1), ("O", 2)]), ("NaCl", [("Na", 1), ("Cl", 1)]),
    ("NaOH", [("Na", 1), ("O", 1), ("H", 1)]), ("CH₄", [("C", 1), ("H", 4)]), ("HCl", [("H", 1), ("Cl", 1)]),
    ("MgO", [("Mg", 1), ("O", 1)]), ("CaCO₃", [("Ca", 1), ("C", 1), ("O", 3)]), ("NH₃", [("N", 1), ("H", 3)]),
]


def _masses_hint():
    return "Atommassen: H=1, C=12, N=14, O=16, Na=23, Mg=24,3, Cl=35,5, Ca=40,1 (g/mol)"


def q_molare_masse(rng):
    f, parts = rng.choice(COMPOUNDS)
    M = _molar_mass(parts)
    naive = sum(ATOMIC_MASS[e] for e, _ in parts)
    traps = {}
    if abs(naive - M) > 0.05:
        traps[f"{naive:g}"] = "Indizes vergessen: jedes Atom zählt so oft, wie der Index angibt."
    return Question("", "molare_masse", "num", f"Berechne die molare Masse von {f}. ({_masses_hint()})",
                    f"{M:.2f}", tolerance=0.02, unit="g/mol",
                    explanation=" + ".join(f"{n}·{ATOMIC_MASS[e]:g}" for e, n in parts) + f" = {M:g} g/mol",
                    traps=traps)


def q_stoffmenge(rng):
    f, parts = rng.choice(COMPOUNDS)
    M = _molar_mass(parts)
    n = rng.choice([0.5, 1, 1.5, 2, 2.5, 3, 4])
    m = round(n * M, 2)
    return Question("", "stoffmenge", "num", f"Du hast {m:g} g {f} (M = {M:g} g/mol). Wie groß ist die Stoffmenge n?",
                    f"{n:g}", tolerance=0.02, unit="mol", explanation=f"n = m / M = {m:g} g / {M:g} g/mol = {n:g} mol",
                    traps={f"{round(m * M, 2):g}": "Multipliziert statt dividiert: n = m / M.",
                           f"{round(M / m, 3):g}": "Bruch umgedreht: n = m / M, nicht M / m."})


def q_konzentration(rng):
    n = rng.choice([0.1, 0.2, 0.25, 0.5, 1.0])
    V = rng.choice([0.25, 0.5, 1.0, 2.0])
    c = n / V
    Vml = int(V * 1000)
    return Question("", "konzentration", "num", f"{n:g} mol NaCl werden in Wasser zu {Vml} mL Lösung gelöst. Berechne c.",
                    f"{c:g}", tolerance=0.02, unit="mol/L",
                    explanation=f"V = {Vml} mL = {V:g} L → c = n / V = {n:g} / {V:g} = {c:g} mol/L",
                    traps={f"{n / Vml:g}": "Einheit vergessen: mL zuerst in L umrechnen.",
                           f"{n * V:g}": "Multipliziert statt dividiert: c = n / V."})


def q_ph_rechnen(rng):
    x = rng.choice([1, 2, 3, 4, 5])
    acid = rng.choice(["Salzsäure", "Salpetersäure"])
    return Question("", "ph_rechnen", "num", f"Eine {acid} hat c(H₃O⁺) = 10⁻{str(x).translate(str.maketrans('0123456789','⁰¹²³⁴⁵⁶⁷⁸⁹'))} mol/L. Welcher pH-Wert?",
                    f"{x}", tolerance=0.01, explanation=f"pH = −log₁₀(c) = −log₁₀(10^−{x}) = {x}",
                    traps={f"-{x}": "Vorzeichenfehler: pH = −log(c), deshalb positiv.",
                           f"{14 - x}": "pOH statt pH berechnet."})


def q_alkan_formel(rng):
    i = rng.randint(1, 10)
    name = ALKANES[i - 1]
    ans = f"C{_sub(i)}H{_sub(2 * i + 2)}"
    wrong = {f"C{_sub(i)}H{_sub(2 * i)}": "Das ist ein Alken (CₙH₂ₙ). Alkane: CₙH₂ₙ₊₂.",
             f"C{_sub(i)}H{_sub(2 * i - 2)}" if i > 1 else "CH₂": "Das ist ein Alkin. Alkane: CₙH₂ₙ₊₂.",
             f"C{_sub(i + 1)}H{_sub(2 * i + 4)}": "Kettenlänge verzählt (Präfix prüfen)."}
    return Question("", "alkan_formel", "mc", f"Wie lautet die Summenformel von {name}?", ans,
                    _mc(list(wrong), ans, rng), explanation=f"Alkane: CₙH₂ₙ₊₂ → n = {i}", traps=wrong)


def q_alkan_name(rng):
    i = rng.randint(1, 10)
    ans = ALKANES[i - 1]
    f = f"C{_sub(i)}H{_sub(2 * i + 2)}"
    others = [ALKANES[j] for j in (i - 2, i, i + 1) if 0 <= j < 10 and j != i - 1]
    if len(others) < 3:
        others += rng.sample([a for a in ALKANES if a != ans and a not in others], 3 - len(others))
    return Question("", "alkan_name", "mc", f"Benenne das Alkan {f}.", ans, _mc(others, ans, rng),
                    explanation=f"{i} C-Atome → Präfix '{ans[:-2]}' + Endung '-an'.")


def q_siedetrend(rng):
    a, b = rng.sample(ALKANES[:8], 2)
    hi = a if BOILING[a] > BOILING[b] else b
    return Question("", "siedetrend", "mc", f"Welches Alkan hat den höheren Siedepunkt: {a} oder {b}?", hi,
                    _mc([a, b, "Beide gleich"], hi, rng),
                    explanation="Längere Ketten → stärkere Van-der-Waals-Kräfte → höherer Siedepunkt.",
                    traps={("Beide gleich"): "Die Kettenlänge ändert die Van-der-Waals-Kräfte."})


TEMPLATES = {
    "ionen": q_ionen, "salzformel": q_salzformel, "ph_skala": q_ph_skala, "indikator": q_indikator,
    "saeurebildung": q_saeurebildung, "laugenbildung": q_laugenbildung, "saeure_metall": q_saeure_metall,
    "neutralisation": q_neutralisation, "molare_masse": q_molare_masse, "stoffmenge": q_stoffmenge,
    "konzentration": q_konzentration, "ph_rechnen": q_ph_rechnen, "alkan_formel": q_alkan_formel,
    "alkan_name": q_alkan_name, "siedetrend": q_siedetrend,
}


def generate(skill: str, rng: random.Random, qid: str) -> Question:
    q = TEMPLATES[skill](rng)
    q.id = qid
    # German decimal comma in what the student reads (grading accepts both)
    q.prompt = re.sub(r"(\d)\.(\d)", r"\1,\2", q.prompt)
    q.explanation = re.sub(r"(\d)\.(\d)", r"\1,\2", q.explanation)
    return q


def build_test(seed: int, n: int = 30, weights: dict[str, float] | None = None) -> list[Question]:
    """30 questions covering every skill twice, weighted toward weak skills if weights given."""
    rng = random.Random(seed)
    skills = list(SKILLS)
    plan = skills * (n // len(skills))
    while len(plan) < n:
        if weights:
            plan.append(rng.choices(skills, [1.0 - weights.get(s, 0.3) + 0.05 for s in skills])[0])
        else:
            plan.append(rng.choice(skills))
    rng.shuffle(plan)
    qs, seen = [], set()
    for i, s in enumerate(plan):
        for _ in range(10):  # avoid duplicate prompts
            q = generate(s, rng, f"q{i}")
            if q.prompt not in seen:
                break
        seen.add(q.prompt)
        qs.append(q)
    return qs


def _to_float(s: str) -> float | None:
    try:
        return float(str(s).strip().replace(",", ".").replace("−", "-"))
    except ValueError:
        return None


def grade(q: dict, given: str) -> tuple[bool, str | None]:
    """Return (correct, error_feedback)."""
    given = (given or "").strip()
    if q["kind"] == "num":
        g, a = _to_float(given), float(q["answer"])
        if g is None:
            return False, "Bitte eine Zahl eingeben (Komma oder Punkt)."
        tol = max(abs(a) * q["tolerance"], 0.01)
        if abs(g - a) <= tol:
            return True, None
        for trap, msg in q["traps"].items():
            t = _to_float(trap)
            if t is not None and abs(g - t) <= max(abs(t) * 0.02, 0.01):
                return False, msg
        return False, None
    if given == q["answer"]:
        return True, None
    return False, q["traps"].get(given)


PASS_MARK = 20
