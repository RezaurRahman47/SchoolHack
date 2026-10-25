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
    "ph_skala":     {"name": "pH-Wert",                      "topic": "Säuren und Laugen",   "pre": []},
    "indikator":    {"name": "Indikatoren",                  "topic": "Säuren und Laugen",   "pre": ["ph_skala"]},
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
    # --- Curriculum 3.9–3.12: organic chemistry -----------------------------
    "saeure_base_begriff": {"name": "Säure-Base-Begriff (Brønsted)", "topic": "Säuren und Laugen", "pre": ["ph_skala"]},
    "vorkommen_verwendung": {"name": "Kohlenwasserstoffe: Vorkommen & Nutzung", "topic": "Kohlenwasserstoffe", "pre": []},
    "isomerie":     {"name": "Isomerie",                      "topic": "Kohlenwasserstoffe",  "pre": ["alkan_name"]},
    "verbrennung":  {"name": "Verbrennung von Kohlenwasserstoffen", "topic": "Kohlenwasserstoffe", "pre": ["alkan_formel"]},
    "ungesaettigt": {"name": "Ungesättigte Kohlenwasserstoffe", "topic": "Kohlenwasserstoffe", "pre": ["alkan_formel"]},
    "alkohol_herstellung": {"name": "Alkohole: Herstellung",   "topic": "Alkohole",            "pre": []},
    "alkohol_nomenklatur": {"name": "Alkohole: Struktur & Namen", "topic": "Alkohole",         "pre": ["alkan_name"]},
    "alkohol_eigenschaften": {"name": "Alkohole: Eigenschaften", "topic": "Alkohole",          "pre": ["alkohol_nomenklatur"]},
    "alkohol_wirkung": {"name": "Wirkung von Alkohol",         "topic": "Alkohole",            "pre": ["alkohol_eigenschaften"]},
    "alkanale":     {"name": "Alkanale",                      "topic": "Alkohole",            "pre": ["alkohol_nomenklatur"]},
    "carbonsaeure_struktur": {"name": "Carbonsäuren: Struktur", "topic": "Organische Säuren",  "pre": ["alkanale"]},
    "carbonsaeure_eigenschaften": {"name": "Carbonsäuren: Eigenschaften", "topic": "Organische Säuren", "pre": ["carbonsaeure_struktur"]},
    "aminosaeuren": {"name": "Aminosäuren",                   "topic": "Organische Säuren",   "pre": ["carbonsaeure_struktur"]},
    "ester":        {"name": "Ester: Struktur & Synthese",    "topic": "Ester",               "pre": ["alkohol_nomenklatur", "carbonsaeure_struktur"]},
    "fette":        {"name": "Fette, Fettsäuren & Seifen",    "topic": "Ester",               "pre": ["ester"]},
}

# ---------------------------------------------------------------------------
# Curriculum: the six units and their subchapters, in display order.
# ---------------------------------------------------------------------------
# Only subchapters with existing learning content (a SKILLS entry plus
# flashcards/practice in subtopics_data.py) are listed. Where one skill covers
# several curriculum subchapters, the extra titles go into "covers".
CURRICULUM_UNITS: list[dict] = [
    {
        "code": "Unit 1",
        "topic": "Stoffmenge und Mol",
        "title": "Klare Verhältnisse – Quantitative Betrachtungen",
        "cards": [
            {"id": "stoffmenge", "title": "Stoffmenge"},
            {"id": "molare_masse", "title": "Atommasse und molare Masse"},
            {"id": "konzentration", "title": "Stoffmengenkonzentration wässriger Lösungen"},
        ],
    },
    {
        "code": "Unit 2",
        "topic": "Säuren und Laugen",
        "title": "Säuren und Laugen – echt ätzend",
        "cards": [
            {"id": "indikator", "title": "Indikatoren"},
            {"id": "ph_skala", "title": "pH-Wert"},
            {"id": "saeure_base_begriff", "title": "Säure-Base-Begriff"},
            {"id": "saeurebildung", "title": "Bildung von sauren und alkalischen Lösungen"},
            {"id": "neutralisation", "title": "Neutralisationsreaktion"},
        ],
    },
    {
        "code": "Unit 3",
        "topic": "Kohlenwasserstoffe",
        "title": "Kohlenwasserstoffe – vom Campinggas zum Superbenzin",
        "cards": [
            {"id": "vorkommen_verwendung", "title": "Vorkommen und Verwendung"},
            {"id": "alkan_formel", "title": "Struktur und Eigenschaften gesättigter Kohlenwasserstoffe, homologe Reihe"},
            {"id": "isomerie", "title": "Isomerie"},
            {"id": "siedetrend", "title": "Zwischenmolekulare Wechselwirkungen: Van-der-Waals-Kräfte"},
            {"id": "alkan_name", "title": "Nomenklatur"},
            {"id": "verbrennung", "title": "Chemische Reaktionen (Verbrennung)"},
            {"id": "ungesaettigt", "title": "Ungesättigte Kohlenwasserstoffe"},
        ],
    },
    {
        "code": "Unit 4",
        "topic": "Alkohole",
        "title": "Alkohole – vom Holzgeist zum Glycerin",
        "cards": [
            {"id": "alkohol_herstellung", "title": "Herstellung von Methanol oder Ethanol"},
            {"id": "alkohol_nomenklatur", "title": "Struktur und Nomenklatur der Alkanole",
             "covers": ["Bedeutung einer funktionellen Gruppe"]},
            {"id": "alkohol_eigenschaften",
             "title": "Änderung von Eigenschaften innerhalb der homologen Reihe in Bezug zur Verwendung (Hydrophilie, Hydrophobie)",
             "covers": ["Propan-1,2,3-triol"]},
            {"id": "alkohol_wirkung", "title": "Physiologische Wirkung von alkoholischen Getränken"},
            {"id": "alkanale", "title": "Alkanale"},
        ],
    },
    {
        "code": "Unit 5",
        "topic": "Organische Säuren",
        "title": "Organische Säuren – Salatsauce, Entkalker & Co",
        "cards": [
            {"id": "carbonsaeure_struktur", "title": "Struktur von Alkansäuren, Carboxy-Gruppe"},
            {"id": "carbonsaeure_eigenschaften", "title": "Eigenschaften und Verwendung von Alkansäuren",
             "covers": ["Änderung der Eigenschaften innerhalb der homologen Reihe in Bezug zur Verwendung"]},
            {"id": "aminosaeuren", "title": "Aminosäuren"},
        ],
    },
    {
        "code": "Unit 6",
        "topic": "Ester",
        "title": "Ester – Vielfalt der Produkte aus Alkoholen und Säuren",
        "cards": [
            {"id": "fette",
             "title": "Eigenschaften und Verwendung von Alkansäurealkylestern und Fetten (lipophil, lipophob)",
             "covers": ["Fettsäuren und deren Salze"]},
            {"id": "ester", "title": "Struktur von Estern, Estergruppe",
             "covers": ["Synthese und Analyse von Estern",
                        "Kondensationsreaktion und Hydrolyse als katalysierte, umkehrbare Reaktionen"]},
        ],
    },
]

TOPICS: list[str] = [u["topic"] for u in CURRICULUM_UNITS]

# Flattened curriculum cards, keyed by skill id (keeps curriculum order).
CURRICULUM_CARDS: dict[str, dict] = {
    card["id"]: card
    for unit in CURRICULUM_UNITS for card in unit["cards"]
}

# Everything the app actually shows/uses: page, tests, radar and analytics.
# Prerequisites outside the curriculum are stripped so no visible skill points
# at a hidden one.
VISIBLE_SKILLS: dict[str, dict] = {
    sid: {**SKILLS[sid],
          "pre": [p for p in SKILLS[sid]["pre"] if p in CURRICULUM_CARDS],
          "title": card["title"],
          "covers": card.get("covers", [])}
    for sid, card in CURRICULUM_CARDS.items()
}
VISIBLE_TOPICS: list[str] = [t for t in TOPICS
                             if any(v["topic"] == t for v in VISIBLE_SKILLS.values())]

# Everything not in the curriculum stays defined but is not shown.
HIDDEN_SKILLS = frozenset(set(SKILLS) - set(VISIBLE_SKILLS))

# Official curriculum subchapter titles shown on the Chemie page.
SUBTOPIC_TITLES = {sid: card["title"] for sid, card in CURRICULUM_CARDS.items()}
SUBTOPIC_COVERS = {sid: card.get("covers", []) for sid, card in CURRICULUM_CARDS.items()}

# Display order of the subchapters (curriculum order).
SUBTOPIC_ORDER = {sid: i for i, sid in enumerate(CURRICULUM_CARDS)}

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
    adj = {"sauer": "sauren", "neutral": "neutralen", "basisch": "basischen"}[lsg]
    adj_expl = {"sauer": "saurer", "neutral": "neutraler", "basisch": "basischer"}[lsg]
    all_colors = ["rot", "grün", "blau/violett", "pink", "farblos", "grün/gelb", "orange"]
    wrong = [c for c in all_colors if c != color]
    # "grün" and "grün/gelb" would both look plausible for Rotkohlsaft.
    if color == "grün/gelb":
        wrong.remove("grün")
    elif color == "grün":
        wrong.remove("grün/gelb")
    return Question("", "indikator", "mc", f"Welche Farbe zeigt {ind} in einer {adj} Lösung?", color,
                    _mc(rng.sample(wrong, 3), color, rng),
                    explanation=f"{ind} färbt sich in {adj_expl} Lösung {color}.")


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


# ---------------------------------------------------------------------------
# Curriculum 3.9–3.12: hydrocarbons, alcohols, organic acids, esters
# ---------------------------------------------------------------------------
def q_saeure_base_begriff(rng):
    variants = [
        ("Nach Brønsted ist eine Säure ...", "ein Protonendonator (H⁺-Spender)",
         ["ein Protonenakzeptator (H⁺-Nehmer)", "ein Elektronendonator", "ein Hydroxidspender"],
         "Säuren geben Protonen (H⁺) ab. Basen nehmen Protonen auf."),
        ("Nach Brønsted ist eine Base ...", "ein Protonenakzeptator (H⁺-Nehmer)",
         ["ein Protonendonator (H⁺-Spender)", "ein Elektronenakzeptator", "immer ein Metallhydroxid"],
         "Eine Base nimmt Protonen auf – sie muss kein Hydroxid enthalten."),
        ("In der Reaktion HCl + H₂O → H₃O⁺ + Cl⁻ wirkt H₂O als ...",
         "Base, weil es ein Proton aufnimmt",
         ["Säure, weil es ein Proton abgibt", "Katalysator, weil es unverändert bleibt", "Salz, weil es Ionen bildet"],
         "H₂O nimmt das Proton von HCl auf und wird zu H₃O⁺."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "saeure_base_begriff", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={wrong[0]: "Brønsted denkt in Protonen (H⁺), nicht in Elektronen oder Hydroxid-Ionen."})


def q_vorkommen_verwendung(rng):
    variants = [
        ("Welches Gas ist der Hauptbestandteil von Erdgas?", "Methan",
         ["Ethen", "Kohlenstoffdioxid", "Wasserstoff"],
         "Erdgas besteht überwiegend aus Methan (CH₄)."),
        ("Wofür werden Propan und Butan vor allem verwendet?", "Als Camping- und Heizgas",
         ["Als Entkalker", "Als Speiseöl", "Als Düngemittel"],
         "Propan/Butan lassen sich bei mäßigem Druck verflüssigen und brennen sauber – ideal für Campinggas."),
        ("Woraus besteht Erdöl?", "Aus einem Gemisch verschiedener Kohlenwasserstoffe",
         ["Aus reinem Ethanol", "Aus einem einzelnen Alkan", "Aus Salzen und Wasser"],
         "Erdöl ist ein Gemisch; durch Destillation wird es in Fraktionen wie Benzin und Diesel getrennt."),
        ("Welcher Kohlenwasserstoff ist ein typischer Bestandteil von Autobenzin?", "Octan",
         ["Methan", "Ethanol", "Glycerin"],
         "Octan (C₈H₁₈) ist ein typischer Bestandteil von Benzin. Die Oktanzahl vergleicht die Klopffestigkeit mit Isooctan."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "vorkommen_verwendung", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl)


def q_isomerie(rng):
    variants = [
        ("Zwei Moleküle haben dieselbe Summenformel, aber eine unterschiedliche Anordnung der Atome. Wie heißen sie?",
         "Isomere", ["Homologe", "Isotope", "Ionen"],
         "Isomere haben gleiche Summenformel, aber verschiedene Struktur."),
        ("Welches Molekül ist ein Isomer von Butan (C₄H₁₀)?", "2-Methylpropan",
         ["Propan (C₃H₈)", "Pentan (C₅H₁₂)", "Ethen (C₂H₄)"],
         "2-Methylpropan (Isobutan) hat ebenfalls C₄H₁₀, aber eine verzweigte Kette."),
        ("Wie viele Konstitutionsisomere hat Butan (C₄H₁₀)?", "2",
         ["1", "3", "4"],
         "Butan und 2-Methylpropan – zwei Isomere mit derselben Summenformel C₄H₁₀."),
        ("Warum haben Isomere unterschiedliche Siedepunkte?", "Weil ihre Molekülform die zwischenmolekularen Kräfte verändert",
         ["Weil sie verschieden viele Atome enthalten", "Weil sie unterschiedliche Elemente enthalten", "Weil Isomere immer gasförmig sind"],
         "Verzweigte Isomere haben eine kleinere Kontaktfläche und meist schwächere Van-der-Waals-Kräfte."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "isomerie", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"Pentan (C₅H₁₂)": "Isomere müssen dieselbe Summenformel haben – Pentan hat ein C-Atom mehr."})


def q_verbrennung(rng):
    variants = [
        ("Welche Produkte entstehen bei der vollständigen Verbrennung eines Kohlenwasserstoffs?",
         "Kohlenstoffdioxid und Wasser", ["Kohlenstoffmonoxid und Wasserstoff", "Kohlenstoff und Wasser", "Sauerstoff und Methan"],
         "C und H reagieren mit O₂ zu CO₂ und H₂O."),
        ("Welches giftige Gas entsteht bei unvollständiger Verbrennung?", "Kohlenstoffmonoxid (CO)",
         ["Kohlenstoffdioxid (CO₂)", "Wasserstoff (H₂)", "Sauerstoff (O₂)"],
         "Bei Sauerstoffmangel entsteht CO. Es bindet an Hämoglobin und verhindert den Sauerstofftransport."),
        ("Wie viele O₂-Moleküle braucht die vollständige Verbrennung von Methan (CH₄ + ... O₂ → CO₂ + 2 H₂O)?",
         "2", ["1", "3", "4"],
         "CH₄ + 2 O₂ → CO₂ + 2 H₂O. Vier O-Atome auf beiden Seiten."),
        ("Warum ist eine gelbe, rußende Flamme ein Warnzeichen?", "Es entsteht Ruß durch unvollständige Verbrennung",
         ["Die Verbrennung ist besonders vollständig", "Es entsteht zusätzlich Wasser", "Das Gas ist besonders rein"],
         "Ruß zeigt Sauerstoffmangel und unvollständige Verbrennung an – dabei kann auch CO entstehen."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "verbrennung", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"Kohlenstoffdioxid (CO₂)": "CO₂ entsteht bei vollständiger Verbrennung; CO ist das giftige Produkt bei Sauerstoffmangel."})


def q_ungesaettigt(rng):
    variants = [
        ("Welche Bindung kennzeichnet ein Alken?", "Eine C=C-Doppelbindung",
         ["Eine C-C-Einfachbindung", "Eine C≡C-Dreifachbindung", "Eine C-H-Bindung"],
         "Alkene besitzen mindestens eine Kohlenstoff-Kohlenstoff-Doppelbindung."),
        ("Woran erkennt man ungesättigte Kohlenwasserstoffe experimentell?", "Bromwasser wird entfärbt",
         ["Kalkwasser wird trüb", "Die Knallgasprobe pfeift", "Universalindikator wird rot"],
         "Die C=C-Doppelbindung addiert Brom; die braune Bromlösung wird farblos."),
        ("Wie lautet die Summenformel von Ethen?", "C₂H₄",
         ["C₂H₆", "C₂H₂", "CH₄"],
         "Ethen ist ein Alken: CₙH₂ₙ mit n = 2 ergibt C₂H₄."),
        ("Was passiert bei der Addition von Wasserstoff an Ethen?", "Aus Ethen wird Ethan",
         ["Aus Ethen wird Ethanol", "Ethen wird zu CO₂ verbrannt", "Ethen wird ein Alkin"],
         "Die Doppelbindung wird hydriert: C₂H₄ + H₂ → C₂H₆."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "ungesaettigt", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"C₂H₆": "C₂H₆ ist das gesättigte Ethan. Ethen hat eine Doppelbindung und zwei H-Atome weniger."})


def q_alkohol_herstellung(rng):
    variants = [
        ("Wie wird Ethanol traditionell aus Zucker hergestellt?", "Durch Gärung mit Hefe",
         ["Durch Neutralisation mit Natronlauge", "Durch Verbrennung von Methan", "Durch Filtration von Erdöl"],
         "Hefe wandelt Glucose in Ethanol und CO₂ um: C₆H₁₂O₆ → 2 C₂H₅OH + 2 CO₂."),
        ("Wie wird Ethanol industriell in großen Mengen hergestellt?", "Durch Addition von Wasser an Ethen",
         ["Durch Gärung von Kalk", "Durch Destillation von Essig", "Durch Verbrennung von Ethan"],
         "Ethen reagiert mit Wasser (Hydratisierung) zu Ethanol – schnell und ohne Zucker."),
        ("Aus welchem Rohstoff wird Methanol industriell hergestellt?", "Aus Synthesegas (CO und H₂)",
         ["Aus Zucker und Hefe", "Aus Kalkstein", "Aus Natriumchlorid"],
         "Methanol wird aus Synthesegas hergestellt; es ist giftig und nicht zum Trinken geeignet."),
        ("Was entsteht bei der alkoholischen Gärung neben Ethanol?", "Kohlenstoffdioxid",
         ["Sauerstoff", "Wasserstoff", "Kohlenstoffmonoxid"],
         "Bei der Gärung entweicht CO₂ – deshalb schäumt Most beim Gären."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "alkohol_herstellung", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl)


def q_alkohol_nomenklatur(rng):
    alcohols = [("CH₃–OH", "Methanol"), ("CH₃–CH₂–OH", "Ethanol"),
                ("CH₃–CH₂–CH₂–OH", "Propan-1-ol"), ("CH₃–CH(OH)–CH₃", "Propan-2-ol"),
                ("CH₃–CH₂–CH₂–CH₂–OH", "Butan-1-ol")]
    if rng.random() < 0.65:
        formula, ans = rng.choice(alcohols)
        wrong = [n for _, n in alcohols if n != ans]
        wrong += ["Butan-2-ol", "Ethanal"]
        return Question("", "alkohol_nomenklatur", "mc", f"Wie heißt der Alkohol {formula} nach IUPAC?",
                        ans, _mc(wrong, ans, rng),
                        explanation="Die Endung '-ol' zeigt die Hydroxygruppe; die Zahl gibt ihre Position an.",
                        traps={"Propan-2-ol": "Bei Propan-2-ol sitzt die OH-Gruppe am mittleren C-Atom, nicht am Ende."})
    variants = [
        ("Welche funktionelle Gruppe kennzeichnet Alkohole?", "Die Hydroxygruppe (–OH)",
         ["Die Carboxygruppe (–COOH)", "Die Aldehydgruppe (–CHO)", "Die Aminogruppe (–NH₂)"],
         "Die –OH-Gruppe bestimmt die typischen Eigenschaften der Alkohole."),
        ("Wie heißt CH₃–CH(OH)–CH₃?", "Propan-2-ol",
         ["Propan-1-ol", "Butan-1-ol", "Propanal"],
         "Drei C-Atome und die OH-Gruppe am zweiten C-Atom ergeben Propan-2-ol."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "alkohol_nomenklatur", "mc", prompt, ans, _mc(wrong, ans, rng), explanation=expl)


def q_alkohol_eigenschaften(rng):
    variants = [
        ("Warum löst sich Ethanol gut in Wasser, Decan-1-ol aber kaum?",
         "Bei Ethanol überwiegt die hydrophile OH-Gruppe; bei der langen Kette dominiert der hydrophobe Teil",
         ["Decan-1-ol hat keine OH-Gruppe", "Ethanol ist ein Salz", "Decan-1-ol ist eine Säure"],
         "Die OH-Gruppe bildet Wasserstoffbrücken; je länger die Kohlenwasserstoffkette, desto wasserabweisender wird das Molekül."),
        ("Warum ist Glycerin (Propan-1,2,3-triol) gut wasserlöslich und zähflüssig?",
         "Es besitzt drei OH-Gruppen, die viele Wasserstoffbrücken bilden",
         ["Es ist ein langkettiger Kohlenwasserstoff", "Es enthält eine C=C-Doppelbindung", "Es ist ein Salz"],
         "Drei Hydroxygruppen machen Glycerin hydrophil, viskos und feuchtigkeitsspeichernd."),
        ("Welcher Alkohol hat den höheren Siedepunkt: Ethanol oder Butan-1-ol?", "Butan-1-ol",
         ["Ethanol", "Beide gleich", "Das lässt sich nicht vorhersagen"],
         "Die längere Kette verstärkt die Van-der-Waals-Kräfte; Butan-1-ol siedet bei 118 °C, Ethanol bei 78 °C."),
        ("Warum siedet Ethanol höher als das gleich große Ethan?", "Wegen der Wasserstoffbrücken zwischen den OH-Gruppen",
         ["Weil Ethan eine Doppelbindung hat", "Weil Ethanol ein Salz ist", "Weil Ethan schwerer ist"],
         "Die polare OH-Gruppe ermöglicht starke Wasserstoffbrücken – deshalb ist Ethanol flüssig, Ethan gasförmig."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "alkohol_eigenschaften", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"Ethanol": "Ethanol hat die kürzere Kette und schwächere Van-der-Waals-Kräfte."})


def q_alkohol_wirkung(rng):
    variants = [
        ("Warum ist Ethanol in alkoholischen Getränken gesundheitsschädlich?",
         "Es wird in der Leber zu Acetaldehyd abgebaut, das Zellen schädigt",
         ["Es ist ein Vitamin", "Es wird unverändert ausgeschieden", "Es bildet im Magen Salzsäure"],
         "Acetaldehyd ist ein reaktives Zellgift; außerdem dämpft Ethanol das Nervensystem."),
        ("Wie wirkt Alkohol auf das zentrale Nervensystem?", "Es dämpft es und verlangsamt Reaktion und Urteilsvermögen",
         ["Es beschleunigt alle Reaktionen dauerhaft", "Es stärkt die Sehleistung", "Es hat keine Wirkung"],
         "Alkohol ist ein Neurotoxin: Reaktionszeit, Koordination und Urteilsfähigkeit verschlechtern sich."),
        ("Warum ist Methanol viel gefährlicher als Ethanol?", "Es wird zu giftiger Ameisensäure abgebaut und kann erblinden",
         ["Es riecht stärker", "Es ist ein Feststoff", "Es kann nicht verdampfen"],
         "Schon kleine Mengen Methanol können Sehnerv und Organe schwer schädigen."),
        ("Welche Aussage über Alkohol und Fahren ist richtig?",
         "Schon geringe Mengen verlängern die Reaktionszeit und sind im Straßenverkehr verboten",
         ["Ein Kaffee macht den Alkohol sofort unschädlich", "Alkohol verbessert die Konzentration", "Nur Schnaps ist gefährlich, Bier nicht"],
         "Der Körper baut Alkohol nur langsam ab; Kaffee beschleunigt das nicht."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "alkohol_wirkung", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl)


def q_alkanale(rng):
    variants = [
        ("Welche funktionelle Gruppe kennzeichnet Alkanale?", "Die Aldehydgruppe (–CHO)",
         ["Die Hydroxygruppe (–OH)", "Die Carboxygruppe (–COOH)", "Die Aminogruppe (–NH₂)"],
         "Alkanale enthalten eine Aldehydgruppe; die Endung lautet '-al'."),
        ("Ethanol wird mild oxidiert. Welcher Stoff entsteht zuerst?", "Ethanal",
         ["Ethansäure", "Ethen", "Methan"],
         "Primäre Alkohole werden zu Alkanalen und bei weiterer Oxidation zu Alkansäuren."),
        ("Wie heißt CH₃–CHO?", "Ethanal",
         ["Ethanol", "Ethansäure", "Methanal"],
         "Zwei C-Atome und eine Aldehydgruppe ergeben Ethanal (Acetaldehyd)."),
        ("Was entsteht bei der weiteren Oxidation von Ethanal?", "Ethansäure (Essigsäure)",
         ["Ethanol", "Ethen", "Kohlenstoffdioxid"],
         "Aldehyde können weiter zur Carbonsäure oxidiert werden: Ethanal → Ethansäure."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "alkanale", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"Ethanol": "Ethanol ist der Ausgangsstoff; bei der Oxidation entsteht daraus Ethanal."})


def q_carbonsaeure_struktur(rng):
    variants = [
        ("Welche Atomgruppe macht eine Carbonsäure sauer?", "Die Carboxygruppe (–COOH)",
         ["Die Hydroxygruppe (–OH)", "Die Aldehydgruppe (–CHO)", "Die Aminogruppe (–NH₂)"],
         "Die Carboxygruppe kann ein Proton (H⁺) abgeben und wirkt deshalb als Säure."),
        ("Wie heißt CH₃–COOH nach IUPAC?", "Ethansäure",
         ["Methansäure", "Propansäure", "Ethanal"],
         "Zwei C-Atome und eine Carboxygruppe ergeben Ethansäure – bekannt als Essigsäure."),
        ("Wie lautet die allgemeine Formel der gesättigten Alkansäuren?", "CₙH₂ₙ₊₁COOH",
         ["CₙH₂ₙ₊₂", "CₙH₂ₙ", "CₙH₂ₙ₊₁OH"],
         "Alkansäuren bestehen aus einer Alkylkette und genau einer Carboxygruppe."),
        ("Wie viele H⁺-Ionen kann eine Carboxygruppe abgeben?", "1",
         ["2", "3", "0"],
         "Nur das Wasserstoffatom der COOH-Gruppe ist sauer und wird abgegeben."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "carbonsaeure_struktur", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"CₙH₂ₙ₊₁OH": "Das ist die Formel eines Alkohols, nicht einer Carbonsäure."})


def q_carbonsaeure_eigenschaften(rng):
    variants = [
        ("Warum löst Essigsäure Kalk (Calciumcarbonat) auf?",
         "Sie gibt H⁺-Ionen ab; Carbonat reagiert zu CO₂ und Wasser",
         ["Sie bildet mit Kalk eine Seife", "Sie ist ein Metalloxid", "Sie entzieht dem Kalk Wasser"],
         "Säure + Carbonat → Salz + Wasser + CO₂. Deshalb schäumt Entkalker."),
        ("Wie ändert sich die Wasserlöslichkeit innerhalb der homologen Reihe der Alkansäuren?",
         "Sie nimmt mit längerer Kohlenwasserstoffkette ab",
         ["Sie nimmt mit längerer Kette zu", "Sie bleibt gleich", "Sie steigt zuerst stark an und bleibt dann gleich"],
         "Die hydrophobe Kette wird länger, die polare Carboxygruppe bleibt gleich – die Löslichkeit sinkt."),
        ("Wofür wird Essigsäure im Alltag verwendet?", "Als Essig, Konservierungsmittel und Entkalker",
         ["Als Campinggas", "Als Kunststoff", "Als Düngesalz"],
         "Verdünnte Essigsäure ist Essig; sie konserviert und löst Kalk."),
        ("Was entsteht, wenn Zink mit Essigsäure reagiert?", "Zinkacetat und Wasserstoff",
         ["Zinkacetat und Sauerstoff", "Zinkoxid und Wasser", "Nur Wasserstoff und Wasser"],
         "Metall + Säure → Salz + Wasserstoff. Die Knallgasprobe weist H₂ nach."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "carbonsaeure_eigenschaften", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl)


def q_aminosaeuren(rng):
    variants = [
        ("Welche zwei funktionellen Gruppen hat eine Aminosäure?", "Aminogruppe (–NH₂) und Carboxygruppe (–COOH)",
         ["Hydroxygruppe (–OH) und Aldehydgruppe (–CHO)", "Nur Carboxygruppen", "Estergruppe und Aminogruppe"],
         "Die Aminogruppe kann Protonen aufnehmen, die Carboxygruppe abgeben."),
        ("Warum können Aminosäuren sowohl als Säure als auch als Base wirken?",
         "Die Carboxygruppe gibt H⁺ ab, die Aminogruppe nimmt H⁺ auf",
         ["Sie enthalten zwei Carboxygruppen", "Sie sind immer neutral", "Sie enthalten kein Wasserstoffatom"],
         "Diese Doppelnatur nennt man amphoter; sie hängt vom pH-Wert der Lösung ab."),
        ("Woraus bestehen Proteine?", "Aus Aminosäuren, die durch Peptidbindungen verknüpft sind",
         ["Aus Fettsäuren und Glycerin", "Aus Zuckermolekülen", "Aus Alkansäuren und Alkohol"],
         "Aminosäuren sind die Bausteine der Proteine."),
        ("Welche Aminosäure ist die einfachste?", "Glycin",
         ["Alanin", "Glycerin", "Ethansäure"],
         "Glycin hat als Seitenkette nur ein Wasserstoffatom."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "aminosaeuren", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"Glycerin": "Glycerin ist ein Alkohol (Triol), keine Aminosäure."})


def q_ester(rng):
    variants = [
        ("Wie entsteht ein Ester in einer Kondensationsreaktion?",
         "Alkohol + Carbonsäure → Ester + Wasser",
         ["Alkohol + Carbonsäure → Ester + Wasserstoff", "Alkohol + Lauge → Ester + Salz", "Carbonsäure + Metall → Ester + Wasser"],
         "Unter Säurekatalyse reagieren Alkohol und Carbonsäure zu Ester und Wasser."),
        ("Welche Atomgruppe kennzeichnet die Estergruppe?", "–COO–",
         ["–COOH", "–OH", "–CHO"],
         "Die Estergruppe entsteht aus der Carboxygruppe der Säure und der OH-Gruppe des Alkohols."),
        ("Wie heißt der Ester aus Ethanol und Ethansäure?", "Ethylethanoat (Essigsäureethylester)",
         ["Methylethanoat", "Ethansäure", "Ethanal"],
         "Der Alkohol liefert den ersten Namensteil, die Säure den zweiten: Ethyl + ethanoat."),
        ("Was passiert bei der Hydrolyse eines Esters?",
         "Er reagiert mit Wasser zurück zu Alkohol und Carbonsäure",
         ["Er verbrennt zu CO₂ und Wasser", "Er wird zu einem Alkan", "Er bildet eine Lauge"],
         "Die Estersynthese ist umkehrbar: Hydrolyse spaltet den Ester wieder in seine Ausgangsstoffe."),
        ("Warum riecht ein Ester oft nach Früchten?", "Kleine Ester sind flüchtig und werden vom Geruchssinn wahrgenommen",
         ["Ester sind immer Salze", "Ester enthalten Zucker", "Ester sind radioaktiv"],
         "Viele kurzkettige Ester haben charakteristische Fruchtaromen – z. B. Butansäureethylester nach Ananas."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "ester", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"–COOH": "–COOH ist die Carboxygruppe der Säure; im Ester ist der H durch einen Alkylrest ersetzt."})


def q_fette(rng):
    variants = [
        ("Fette sind Ester aus ...", "Glycerin und drei Fettsäuren",
         ["Ethanol und drei Alkansäuren", "Glycerin und drei Mineralien", "Fettsäuren und Natronlauge"],
         "Fette (Triglyceride) sind Triester des Glycerins mit drei Fettsäuren."),
        ("Was entsteht bei der Verseifung von Fett mit Natronlauge?",
         "Glycerin und Natriumseifen (Fettsäuresalze)",
         ["Glycerin und freie Salzsäure", "Ethanol und Natriumchlorid", "Nur Wasser und CO₂"],
         "Die Estergruppen werden hydrolysiert; die Fettsäuren bilden mit Na⁺ Seifen."),
        ("Was sind Fettsäuren?", "Langkettige Carbonsäuren",
         ["Kurzkettige Alkohole", "Salze der Schwefelsäure", "Zucker mit Aminogruppe"],
         "Fettsäuren sind Carbonsäuren mit meist 12 bis 22 C-Atomen."),
        ("Warum sind Fette lipophil und kaum wasserlöslich?",
         "Der lange unpolare Kohlenwasserstoffrest überwiegt die polare Estergruppe",
         ["Fette enthalten keine Atombindungen", "Fette sind Salze", "Fette haben viele OH-Gruppen"],
         "Die langen Fettsäureketten sind unpolar und lösen sich gut in Fett, aber schlecht in Wasser."),
    ]
    prompt, ans, wrong, expl = rng.choice(variants)
    return Question("", "fette", "mc", prompt, ans, _mc(wrong, ans, rng),
                    explanation=expl,
                    traps={"Ethanol und Natriumchlorid": "Bei der Verseifung entstehen Glycerin und Fettsäuresalze (Seifen), kein Kochsalz."})


TEMPLATES = {
    "ionen": q_ionen, "salzformel": q_salzformel, "ph_skala": q_ph_skala, "indikator": q_indikator,
    "saeurebildung": q_saeurebildung, "laugenbildung": q_laugenbildung, "saeure_metall": q_saeure_metall,
    "neutralisation": q_neutralisation, "molare_masse": q_molare_masse, "stoffmenge": q_stoffmenge,
    "konzentration": q_konzentration, "ph_rechnen": q_ph_rechnen, "alkan_formel": q_alkan_formel,
    "alkan_name": q_alkan_name, "siedetrend": q_siedetrend,
    # curriculum 3.9–3.12
    "saeure_base_begriff": q_saeure_base_begriff, "vorkommen_verwendung": q_vorkommen_verwendung,
    "isomerie": q_isomerie, "verbrennung": q_verbrennung, "ungesaettigt": q_ungesaettigt,
    "alkohol_herstellung": q_alkohol_herstellung, "alkohol_nomenklatur": q_alkohol_nomenklatur,
    "alkohol_eigenschaften": q_alkohol_eigenschaften, "alkohol_wirkung": q_alkohol_wirkung,
    "alkanale": q_alkanale, "carbonsaeure_struktur": q_carbonsaeure_struktur,
    "carbonsaeure_eigenschaften": q_carbonsaeure_eigenschaften, "aminosaeuren": q_aminosaeuren,
    "ester": q_ester, "fette": q_fette,
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
    skills = list(VISIBLE_SKILLS)
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

# Example grade key (Note 1–6) for the 30-question practice test.  The 4/5 line
# sits exactly on PASS_MARK, so "bestanden" always means Note 4 or better.  This
# is NOT an official Berlin key: schools set their own in the Fachkonferenz, so
# the UI labels it as an example.  (min points out of 30, note, label)
NOTENSCHLUESSEL = (
    (28, 1, "sehr gut"),
    (25, 2, "gut"),
    (23, 3, "befriedigend"),
    (PASS_MARK, 4, "ausreichend"),
    (10, 5, "mangelhaft"),
    (0, 6, "ungenügend"),
)
NOTE_TOTAL = 30


def note_for(score: int | None, total: int = NOTE_TOTAL) -> dict | None:
    """Map a score to the example grade key; scaled if the test is not 30 long."""
    if score is None or total <= 0:
        return None
    points = score * NOTE_TOTAL / total
    for minimum, note, label in NOTENSCHLUESSEL:
        if points >= minimum:
            return {"note": note, "label": label}
    return {"note": 6, "label": "ungenügend"}
