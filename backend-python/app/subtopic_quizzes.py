"""Five-question checks for every subtopic shown on the Chemie page.

The questions are built from the existing curriculum question engine where a
matching skill exists, plus a small set of hand-written book questions for the
curriculum subchapters that do not have their own template.  The bank is built
once at import time with deterministic seeds, so every student sees the same
five questions for a subtopic.
"""
from __future__ import annotations

import random

from .questions import generate


def _mcq(prompt: str, answer: str, wrong: list[str], explanation: str, skill: str) -> dict:
    options = [answer, *wrong]
    rng = random.Random(f"options-{prompt}")
    rng.shuffle(options)
    return {
        "kind": "mc",
        "prompt": prompt,
        "answer": answer,
        "options": options,
        "tolerance": 0.0,
        "unit": "",
        "explanation": explanation,
        "skill": skill,
        "traps": {},
    }


def _num(prompt: str, answer: str, unit: str, explanation: str, skill: str) -> dict:
    return {
        "kind": "num",
        "prompt": prompt,
        "answer": answer,
        "options": [],
        "tolerance": 0.02,
        "unit": unit,
        "explanation": explanation,
        "skill": skill,
        "traps": {},
    }


# ---------------------------------------------------------------------------
# Hand-written questions for curriculum subchapters without a dedicated skill.
# ---------------------------------------------------------------------------
HAND: dict[str, list[dict]] = {
    "stoechiometrie": [
        _num(
            "2 H₂ + O₂ → 2 H₂O: Wie viele Mol H₂ reagieren mit 1 mol O₂?",
            "2", "mol",
            "Das Verhältnis aus der Gleichung ist 2 : 1. Zu 1 mol O₂ gehören also 2 mol H₂.",
            "stoffmenge",
        ),
        _num(
            "CH₄ + 2 O₂ → CO₂ + 2 H₂O: Wie viele Mol CO₂ entstehen aus 3 mol CH₄?",
            "3", "mol",
            "Das Verhältnis CH₄ : CO₂ ist 1 : 1. Aus 3 mol CH₄ entstehen 3 mol CO₂.",
            "stoffmenge",
        ),
        _num(
            "C₃H₈ + 5 O₂ → 3 CO₂ + 4 H₂O: Wie viele Mol O₂ braucht die vollständige "
            "Verbrennung von 2 mol Propan?",
            "10", "mol",
            "Pro Propan-Molekül werden 5 O₂ benötigt. Für 2 mol Propan sind es 2 · 5 = 10 mol O₂.",
            "stoffmenge",
        ),
        _num(
            "2 Al + 3 Cl₂ → 2 AlCl₃: Wie viele Mol Cl₂ reagieren mit 4 mol Al?",
            "6", "mol",
            "Das Verhältnis Al : Cl₂ ist 2 : 3. Aus 4 mol Al folgen 4 · 3/2 = 6 mol Cl₂.",
            "stoffmenge",
        ),
        _num(
            "CaCO₃ → CaO + CO₂: Wie viele Mol CO₂ entstehen aus 5 mol CaCO₃?",
            "5", "mol",
            "Das Verhältnis CaCO₃ : CO₂ ist 1 : 1. Aus 5 mol CaCO₃ entstehen 5 mol CO₂.",
            "stoffmenge",
        ),
    ],
    "massenberechnung": [
        _num(
            "Berechne die Masse von 2 mol CO₂ (M = 44 g/mol).",
            "88", "g",
            "m = n · M = 2 mol · 44 g/mol = 88 g.",
            "molare_masse",
        ),
        _num(
            "Berechne die Masse von 0,5 mol NaOH (M = 40 g/mol).",
            "20", "g",
            "m = n · M = 0,5 mol · 40 g/mol = 20 g.",
            "molare_masse",
        ),
        _num(
            "Berechne die Masse von 3 mol H₂O (M = 18 g/mol).",
            "54", "g",
            "m = n · M = 3 mol · 18 g/mol = 54 g.",
            "molare_masse",
        ),
        _num(
            "Berechne die Masse von 1,5 mol O₂ (M = 32 g/mol).",
            "48", "g",
            "m = n · M = 1,5 mol · 32 g/mol = 48 g.",
            "molare_masse",
        ),
        _num(
            "Berechne die Masse von 0,25 mol NaCl (M = 58,5 g/mol).",
            "14.625", "g",
            "m = n · M = 0,25 mol · 58,5 g/mol = 14,625 g.",
            "molare_masse",
        ),
    ],
    "saeure_base_begriff": [
        _mcq(
            "Welches Teilchen gibt eine Brønsted-Säure an eine Base ab?",
            "Ein Proton (H⁺)",
            ["Ein Elektron (e⁻)", "Ein Neutron", "Ein Hydroxid-Ion (OH⁻)"],
            "Nach Brønsted ist eine Säure ein Protonendonator: Sie gibt H⁺ ab, die Base nimmt es auf.",
            "saeure_base_begriff",
        ),
        _mcq(
            "In der Reaktion NH₃ + H₂O ⇌ NH₄⁺ + OH⁻ wirkt NH₃ als ...",
            "Base, weil es ein Proton aufnimmt",
            ["Säure, weil es ein Proton abgibt", "Katalysator, weil es unverändert bleibt",
             "Salz, weil es Ionen bildet"],
            "NH₃ nimmt vom Wasser ein Proton auf und wird zu NH₄⁺; Wasser wirkt hier als Säure.",
            "saeure_base_begriff",
        ),
    ],
    "kw_vorkommen": [
        _mcq(
            "Welches Produkt entsteht bei der fraktionierten Destillation von Erdöl in der Fraktion "
            "mit den niedrigsten Siedepunkten?",
            "Gase wie Propan und Butan",
            ["Benzin", "Diesel", "Bitumen"],
            "Leicht siedende Bestandteile wie Propan und Butan werden zuerst abgetrennt; "
            "schwere Fraktionen wie Bitumen bleiben zurück.",
            "vorkommen_verwendung",
        ),
    ],
    "isomerie": [
        _mcq(
            "2-Methylbutan ist ein Isomer von ...",
            "Pentan",
            ["Butan", "Hexan", "Propan"],
            "Beide haben die Summenformel C₅H₁₂; 2-Methylbutan ist die verzweigte Form von Pentan.",
            "isomerie",
        ),
    ],
    "van_der_waals": [
        _mcq(
            "Warum hat Pentan einen höheren Siedepunkt als 2-Methylbutan?",
            "Die unverzweigte Kette hat eine größere Kontaktfläche und stärkere Van-der-Waals-Kräfte",
            ["Pentan hat mehr C-Atome", "Pentan ist stärker polar",
             "2-Methylbutan bildet Wasserstoffbrücken"],
            "Beide sind C₅H₁₂. Die Verzweigung verringert die Kontaktfläche und damit die "
            "Van-der-Waals-Kräfte.",
            "siedetrend",
        ),
    ],
    "verbrennung": [
        _mcq(
            "Welche Reaktionsgleichung beschreibt die vollständige Verbrennung von Propan?",
            "C₃H₈ + 5 O₂ → 3 CO₂ + 4 H₂O",
            ["C₃H₈ + 3 O₂ → 3 CO₂ + 4 H₂O", "C₃H₈ + 4 O₂ → 3 CO₂ + 4 H₂O",
             "C₃H₈ + 5 O₂ → 3 CO + 4 H₂O"],
            "Propan hat 3 C- und 8 H-Atome. Vollständige Verbrennung braucht 5 O₂ und bildet "
            "3 CO₂ + 4 H₂O.",
            "verbrennung",
        ),
    ],
    "ungesaettigt": [
        _mcq(
            "Mit welchem Reagenz weist man eine C=C-Doppelbindung durch Entfärbung nach?",
            "Bromwasser",
            ["Kalkwasser", "Universalindikator", "Fehling-Lösung"],
            "Alkene addieren Brom; die braune Bromlösung wird dabei farblos.",
            "ungesaettigt",
        ),
    ],
    "alkohol_herstellung": [
        _mcq(
            "Welche Bedingungen braucht die alkoholische Gärung?",
            "Hefe und warme Temperaturen",
            ["Natronlauge und starke Hitze", "Sauerstoff und UV-Licht", "Eisen und Salzsäure"],
            "Hefeenzyme wandeln Zucker bei milden Temperaturen in Ethanol und CO₂ um.",
            "alkohol_herstellung",
        ),
    ],
    "funktionelle_gruppe": [
        _mcq(
            "Welche funktionelle Gruppe kennzeichnet Alkohole?",
            "Hydroxygruppe (–OH)",
            ["Carboxygruppe (–COOH)", "Aldehydgruppe (–CHO)", "Aminogruppe (–NH₂)"],
            "Die –OH-Gruppe bestimmt die typischen Eigenschaften der Alkohole.",
            "alkohol_nomenklatur",
        ),
        _mcq(
            "Welche funktionelle Gruppe kennzeichnet Alkanale?",
            "Aldehydgruppe (–CHO)",
            ["Hydroxygruppe (–OH)", "Carboxygruppe (–COOH)", "Estergruppe (–COO–)"],
            "Alkanale enthalten eine Aldehydgruppe; ihre Namen enden auf '-al'.",
            "alkanale",
        ),
        _mcq(
            "Welche funktionelle Gruppe kennzeichnet Carbonsäuren?",
            "Carboxygruppe (–COOH)",
            ["Hydroxygruppe (–OH)", "Aldehydgruppe (–CHO)", "Aminogruppe (–NH₂)"],
            "Die Carboxygruppe kann ein Proton abgeben und macht die Verbindung sauer.",
            "carbonsaeure_struktur",
        ),
        _mcq(
            "Welche funktionelle Gruppe enthält eine Aminosäure zusätzlich zur Carboxygruppe?",
            "Aminogruppe (–NH₂)",
            ["Aldehydgruppe (–CHO)", "Estergruppe (–COO–)", "Hydroxygruppe (–OH)"],
            "Aminosäuren verbinden eine basische Aminogruppe mit einer sauren Carboxygruppe.",
            "aminosaeuren",
        ),
        _mcq(
            "Welche Atomgruppe verbindet den Alkohol- und den Säureteil in einem Ester?",
            "Estergruppe (–COO–)",
            ["Carboxygruppe (–COOH)", "Hydroxygruppe (–OH)", "Aminogruppe (–NH₂)"],
            "Die Estergruppe entsteht aus der Carboxygruppe der Säure und der OH-Gruppe des Alkohols.",
            "ester",
        ),
    ],
    "alkohole_eigenschaften": [
        _mcq(
            "Warum ist Propan-1-ol in Wasser schlechter löslich als Ethanol?",
            "Die längere Kohlenwasserstoffkette ist hydrophober",
            ["Propan-1-ol hat keine OH-Gruppe", "Propan-1-ol ist ein Salz",
             "Propan-1-ol hat eine C=C-Doppelbindung"],
            "Die OH-Gruppe bleibt gleich, aber die längere unpolare Kette stört die "
            "Wasserstoffbrücken mit Wasser.",
            "alkohol_eigenschaften",
        ),
    ],
    "alkohol_wirkung": [
        _mcq(
            "Welches Organ baut den größten Teil des aufgenommenen Alkohols ab?",
            "Die Leber",
            ["Die Lunge", "Die Niere", "Der Magen"],
            "In der Leber wird Ethanol über Acetaldehyd zu Essigsäure abgebaut.",
            "alkohol_wirkung",
        ),
    ],
    "propan_triol": [
        _mcq(
            "Wie lautet die Summenformel von Propan-1,2,3-triol (Glycerin)?",
            "C₃H₈O₃",
            ["C₃H₈O", "C₃H₆O₃", "C₃H₄O₃"],
            "Drei C-Atome, acht H-Atome und drei O-Atome ergeben C₃H₈O₃.",
            "alkohol_eigenschaften",
        ),
        _mcq(
            "Wie viele Hydroxygruppen besitzt Glycerin?",
            "3",
            ["1", "2", "4"],
            "Propan-1,2,3-triol trägt an jedem der drei C-Atome eine OH-Gruppe.",
            "alkohol_eigenschaften",
        ),
        _mcq(
            "Warum ist Glycerin zähflüssig?",
            "Die drei OH-Gruppen bilden viele Wasserstoffbrücken",
            ["Es ist ein langkettiger Kohlenwasserstoff", "Es enthält eine C=C-Doppelbindung",
             "Es ist ein Salz"],
            "Die drei Hydroxygruppen vernetzen die Moleküle über Wasserstoffbrücken; "
            "dadurch fließt Glycerin langsam.",
            "alkohol_eigenschaften",
        ),
        _mcq(
            "Wofür wird Glycerin häufig verwendet?",
            "Als Feuchthaltemittel in Kosmetik und Lebensmitteln",
            ["Als Campinggas", "Als Entkalker", "Als Ottokraftstoff"],
            "Glycerin bindet Wasser und wird deshalb in Cremes, Zahnpasta und Lebensmitteln eingesetzt.",
            "alkohol_eigenschaften",
        ),
        _mcq(
            "Welche Eigenschaft verdankt Glycerin seiner guten Wasserlöslichkeit?",
            "Die polaren Hydroxygruppen",
            ["Die unpolare Kohlenwasserstoffkette", "Die Estergruppe", "Die Aminogruppe"],
            "Die drei OH-Gruppen können Wasserstoffbrücken mit Wasser bilden.",
            "alkohol_eigenschaften",
        ),
    ],
    "alkanale": [
        _mcq(
            "Wie lautet die Halbstrukturformel von Ethanal?",
            "CH₃–CHO",
            ["CH₃–CH₂–OH", "CH₃–COOH", "CH₄"],
            "Ethanal hat zwei C-Atome und eine Aldehydgruppe (–CHO).",
            "alkanale",
        ),
    ],
    "alkansaeuren_herstellung": [
        _mcq(
            "Durch welche Reaktion entsteht Ethansäure aus Ethanol?",
            "Durch Oxidation",
            ["Durch Neutralisation", "Durch Hydrierung", "Durch Verseifung"],
            "Ethanol wird zunächst zu Ethanal und dann weiter zu Ethansäure oxidiert.",
            "carbonsaeure_struktur",
        ),
        _mcq(
            "Welches Zwischenprodukt entsteht bei der Oxidation von Ethanol zu Ethansäure?",
            "Ethanal",
            ["Ethen", "Ethan", "Ethylacetat"],
            "Die Oxidation verläuft über das Aldehyd: Ethanol → Ethanal → Ethansäure.",
            "carbonsaeure_struktur",
        ),
        _mcq(
            "Wie wird Essigsäure traditionell hergestellt?",
            "Durch Essigsäuregärung mit Bakterien",
            ["Durch Neutralisation von Natronlauge", "Durch Verbrennung von Methan",
             "Durch Destillation von Erdöl"],
            "Essigsäurebakterien oxidieren Ethanol in Gegenwart von Sauerstoff zu Essigsäure.",
            "carbonsaeure_struktur",
        ),
        _mcq(
            "Welches Oxidationsmittel kann Ethanol im Labor zu Ethansäure oxidieren?",
            "Kaliumpermanganat",
            ["Natriumchlorid", "Kalkwasser", "Bromwasser"],
            "Kaliumpermanganat ist ein starkes Oxidationsmittel und oxidiert Ethanol bis zur "
            "Carbonsäure.",
            "carbonsaeure_struktur",
        ),
        _mcq(
            "Welche funktionelle Gruppe entsteht bei der Oxidation von Ethanal?",
            "Carboxygruppe (–COOH)",
            ["Hydroxygruppe (–OH)", "Aldehydgruppe (–CHO)", "Estergruppe (–COO–)"],
            "Aus der Aldehydgruppe wird bei weiterer Oxidation eine Carboxygruppe.",
            "carbonsaeure_struktur",
        ),
    ],
    "carbonsaeure_struktur": [
        _mcq(
            "Welches H-Atom einer Carbonsäure wird als Proton abgegeben?",
            "Das H-Atom der OH-Gruppe",
            ["Ein H-Atom der Alkylkette", "Das H-Atom am C=O-Kohlenstoff", "Das H-Atom der Aminogruppe"],
            "Nur das Wasserstoffatom der OH-Gruppe in –COOH ist sauer und kann als H⁺ abgespalten werden.",
            "carbonsaeure_struktur",
        ),
    ],
    "alkansaeuren_eigenschaften": [
        _mcq(
            "Warum leitet eine wässrige Essigsäurelösung elektrischen Strom?",
            "Weil sie H⁺-Ionen und Acetat-Ionen bildet",
            ["Weil Essigsäure ein Salz ist", "Weil sie ungeladen bleibt", "Weil sie Wasserstoffgas bildet"],
            "Essigsäure protolysiert teilweise zu H₃O⁺ und CH₃COO⁻; diese Ionen tragen den Strom.",
            "carbonsaeure_eigenschaften",
        ),
    ],
    "alkansaeuren_trends": [
        _mcq(
            "Wie ändert sich die Siedetemperatur innerhalb der homologen Reihe der Alkansäuren?",
            "Sie steigt mit der Kettenlänge",
            ["Sie sinkt mit der Kettenlänge", "Sie bleibt gleich", "Sie steigt nur bis zur Ethansäure"],
            "Längere Ketten haben stärkere Van-der-Waals-Kräfte und sieden deshalb höher.",
            "carbonsaeure_eigenschaften",
        ),
        _mcq(
            "Wie ändert sich die Wasserlöslichkeit der Alkansäuren mit längerer Kohlenwasserstoffkette?",
            "Sie nimmt ab",
            ["Sie nimmt zu", "Sie bleibt gleich", "Sie nimmt zuerst ab und dann stark zu"],
            "Die hydrophobe Kette wird länger, während die polare Carboxygruppe gleich bleibt.",
            "carbonsaeure_eigenschaften",
        ),
        _mcq(
            "Welche Alkansäure hat die kürzeste Kohlenstoffkette?",
            "Methansäure",
            ["Ethansäure", "Propansäure", "Butansäure"],
            "Methansäure (Ameisensäure) besitzt nur ein C-Atom.",
            "carbonsaeure_eigenschaften",
        ),
        _mcq(
            "Welche Eigenschaft nimmt mit längerer Kohlenwasserstoffkette zu?",
            "Die Lipophilie",
            ["Die Wasserlöslichkeit", "Die Säurestärke", "Die Flüchtigkeit"],
            "Längere unpolare Ketten lösen sich besser in Fett und schlechter in Wasser.",
            "carbonsaeure_eigenschaften",
        ),
        _mcq(
            "Warum werden längerkettige Alkansäuren als lipophil bezeichnet?",
            "Ihre lange Kohlenwasserstoffkette ist unpolar",
            ["Ihre Carboxygruppe ist unpolar", "Sie enthalten keine Sauerstoffatome", "Sie sind Salze"],
            "Die unpolare Kette dominiert mit zunehmender Länge die Eigenschaften.",
            "carbonsaeure_eigenschaften",
        ),
    ],
    "aminosaeuren": [
        _mcq(
            "Welche Bindung verknüpft Aminosäuren in einem Protein?",
            "Peptidbindung",
            ["Estergruppe", "C=C-Doppelbindung", "Ionenbindung"],
            "Die Carboxygruppe einer Aminosäure reagiert mit der Aminogruppe der nächsten unter "
            "Wasserabspaltung zur Peptidbindung.",
            "aminosaeuren",
        ),
    ],
    "ester_eigenschaften": [
        _mcq(
            "Was bedeutet der Begriff lipophil?",
            "Fettliebend",
            ["Wasserliebend", "Säureliebend", "Gasförmig"],
            "Lipophile Stoffe lösen sich gut in Fetten und Ölen, aber schlecht in Wasser.",
            "fette",
        ),
    ],
    "ester_synthese": [
        _mcq(
            "Aus welchen beiden Stoffklassen entstehen Ester?",
            "Alkohol und Carbonsäure",
            ["Alkohol und Lauge", "Carbonsäure und Metall", "Alkan und Wasser"],
            "Bei der Veresterung reagiert die Carboxygruppe der Säure mit der OH-Gruppe des Alkohols.",
            "ester",
        ),
        _mcq(
            "Welcher Katalysator wird bei der Estersynthese häufig verwendet?",
            "Schwefelsäure",
            ["Natronlauge", "Kalkwasser", "Bromwasser"],
            "Eine kleine Menge Schwefelsäure beschleunigt die Veresterung.",
            "ester",
        ),
        _mcq(
            "Wie heißt der Ester aus Methanol und Ethansäure?",
            "Methylethanoat",
            ["Ethylmethanoat", "Ethansäure", "Methanol"],
            "Der Alkohol liefert den ersten Namensteil, die Säure den zweiten: Methyl + ethanoat.",
            "ester",
        ),
        _mcq(
            "Was wird bei der Veresterung abgespalten?",
            "Wasser",
            ["Wasserstoff", "Sauerstoff", "Kohlenstoffdioxid"],
            "Alkohol + Carbonsäure → Ester + Wasser; deshalb ist es eine Kondensationsreaktion.",
            "ester",
        ),
        _mcq(
            "Warum ist die Estersynthese eine Kondensationsreaktion?",
            "Zwei Moleküle verbinden sich unter Abspaltung von Wasser",
            ["Zwei Moleküle verbinden sich unter Aufnahme von Wasser",
             "Ein Molekül zerfällt in zwei Teile", "Ein Salz wird in Ionen gespalten"],
            "Bei einer Kondensation entsteht aus zwei Molekülen ein größeres Molekül und Wasser.",
            "ester",
        ),
    ],
    "kondensation_hydrolyse": [
        _mcq(
            "Was versteht man unter der Hydrolyse eines Esters?",
            "Die Spaltung des Esters durch Wasser",
            ["Die Verbrennung des Esters", "Die Neutralisation des Esters", "Die Destillation des Esters"],
            "Hydrolyse bedeutet Spaltung durch Wasser; dabei entstehen Alkohol und Carbonsäure.",
            "ester",
        ),
        _mcq(
            "Wie kann die Hydrolyse eines Esters begünstigt werden?",
            "Durch Wasser und einen Katalysator",
            ["Durch Entzug von Wasser", "Durch Abkühlen ohne Wasser", "Durch Zugabe von Natriumchlorid"],
            "Die Rückreaktion braucht Wasser und wird durch Säure oder Base katalysiert.",
            "ester",
        ),
        _mcq(
            "Warum ist die Estersynthese eine Gleichgewichtsreaktion?",
            "Hin- und Rückreaktion laufen gleichzeitig ab",
            ["Die Reaktion läuft nur in eine Richtung", "Es entsteht kein Wasser",
             "Der Katalysator wird verbraucht"],
            "Veresterung und Hydrolyse laufen gleichzeitig ab; das Gleichgewicht ist umkehrbar.",
            "ester",
        ),
        _mcq(
            "Wohin verschiebt sich das Gleichgewicht der Veresterung, wenn man Wasser entzieht?",
            "Zum Ester",
            ["Zu den Ausgangsstoffen", "Es bleibt unverändert", "Zum Katalysator"],
            "Wasser ist ein Produkt. Entzieht man es, verschiebt sich das Gleichgewicht nach rechts "
            "zum Ester.",
            "ester",
        ),
        _mcq(
            "Welche Produkte entstehen bei der alkalischen Hydrolyse eines Esters?",
            "Alkohol und Carbonsäuresalz",
            ["Alkohol und Carbonsäure", "Nur Wasser", "Alkan und CO₂"],
            "In alkalischer Lösung wird die entstehende Carbonsäure sofort zum Salz neutralisiert; "
            "die Reaktion läuft dadurch vollständig ab.",
            "ester",
        ),
    ],
    "fettsaeuren_seifen": [
        _mcq(
            "Was ist der Hauptbestandteil einer klassischen Seife?",
            "Natrium- oder Kaliumsalze von Fettsäuren",
            ["Reine Fettsäuren", "Glycerin", "Natriumchlorid"],
            "Bei der Verseifung von Fett mit Natron- oder Kalilauge entstehen die Alkalisalze der "
            "Fettsäuren – die Seifen.",
            "fette",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Subtopic specs: generated parts + hand-written extras.
# ---------------------------------------------------------------------------
SPECS: dict[str, dict] = {
    # Unit 1 – quantitative chemistry
    "stoffmenge": {
        "title": "Stoffmenge", "skill": "stoffmenge",
        "parts": [("stoffmenge", 5)], "hand": [],
    },
    "atommasse": {
        "title": "Atommasse und molare Masse", "skill": "molare_masse",
        "parts": [("molare_masse", 5)], "hand": [],
    },
    "stoechiometrie": {
        "title": "Stöchiometrisches Rechnen", "skill": "stoffmenge",
        "parts": [], "hand": HAND["stoechiometrie"],
    },
    "massenberechnung": {
        "title": "Massenberechnungen bei chemischen Reaktionen", "skill": "molare_masse",
        "parts": [], "hand": HAND["massenberechnung"],
    },
    "konzentration": {
        "title": "Stoffmengenkonzentration", "skill": "konzentration",
        "parts": [("konzentration", 5)], "hand": [],
    },
    # Unit 2 – acids and bases
    "indikatoren": {
        "title": "Indikatoren", "skill": "indikator",
        "parts": [("indikator", 5)], "hand": [],
    },
    "ph_wert": {
        "title": "pH-Wert", "skill": "ph_skala",
        "parts": [("ph_skala", 3), ("ph_rechnen", 2)], "hand": [],
    },
    "saeure_base_begriff": {
        "title": "Säure-Base-Begriff", "skill": "saeure_base_begriff",
        "parts": [("saeure_base_begriff", 3)], "hand": HAND["saeure_base_begriff"],
    },
    "saure_alkalische_loesung": {
        "title": "Bildung von sauren und alkalischen Lösungen", "skill": "saeurebildung",
        "parts": [("saeurebildung", 2), ("laugenbildung", 2), ("saeure_metall", 1)], "hand": [],
    },
    "neutralisation": {
        "title": "Neutralisationsreaktion", "skill": "neutralisation",
        "parts": [("neutralisation", 5)], "hand": [],
    },
    # Unit 3 – hydrocarbons
    "kw_vorkommen": {
        "title": "Vorkommen und Verwendung", "skill": "vorkommen_verwendung",
        "parts": [("vorkommen_verwendung", 4)], "hand": HAND["kw_vorkommen"],
    },
    "alkane_struktur": {
        "title": "Struktur und Eigenschaften", "skill": "alkan_formel",
        "parts": [("alkan_formel", 2), ("alkan_name", 2), ("siedetrend", 1)], "hand": [],
    },
    "isomerie": {
        "title": "Isomerie", "skill": "isomerie",
        "parts": [("isomerie", 4)], "hand": HAND["isomerie"],
    },
    "van_der_waals": {
        "title": "Zwischenmolekulare Wechselwirkungen", "skill": "siedetrend",
        "parts": [("siedetrend", 4)], "hand": HAND["van_der_waals"],
    },
    "nomenklatur": {
        "title": "Nomenklatur", "skill": "alkan_name",
        "parts": [("alkan_name", 5)], "hand": [],
    },
    "verbrennung": {
        "title": "Chemische Reaktionen", "skill": "verbrennung",
        "parts": [("verbrennung", 4)], "hand": HAND["verbrennung"],
    },
    "ungesaettigt": {
        "title": "Ungesättigte Kohlenwasserstoffe", "skill": "ungesaettigt",
        "parts": [("ungesaettigt", 4)], "hand": HAND["ungesaettigt"],
    },
    # Unit 4 – alcohols
    "alkohol_herstellung": {
        "title": "Herstellung", "skill": "alkohol_herstellung",
        "parts": [("alkohol_herstellung", 4)], "hand": HAND["alkohol_herstellung"],
    },
    "alkohole_struktur": {
        "title": "Struktur und Nomenklatur", "skill": "alkohol_nomenklatur",
        "parts": [("alkohol_nomenklatur", 5)], "hand": [],
    },
    "funktionelle_gruppe": {
        "title": "Bedeutung einer funktionellen Gruppe", "skill": "alkohol_nomenklatur",
        "parts": [], "hand": HAND["funktionelle_gruppe"],
    },
    "alkohole_eigenschaften": {
        "title": "Änderung von Eigenschaften", "skill": "alkohol_eigenschaften",
        "parts": [("alkohol_eigenschaften", 4)], "hand": HAND["alkohole_eigenschaften"],
    },
    "alkohol_wirkung": {
        "title": "Physiologische Wirkung", "skill": "alkohol_wirkung",
        "parts": [("alkohol_wirkung", 4)], "hand": HAND["alkohol_wirkung"],
    },
    "propan_triol": {
        "title": "Propan-1,2,3-triol", "skill": "alkohol_eigenschaften",
        "parts": [], "hand": HAND["propan_triol"],
    },
    "alkanale": {
        "title": "Alkanale", "skill": "alkanale",
        "parts": [("alkanale", 4)], "hand": HAND["alkanale"],
    },
    # Unit 5 – organic acids
    "alkansaeuren_herstellung": {
        "title": "Herstellung", "skill": "carbonsaeure_struktur",
        "parts": [], "hand": HAND["alkansaeuren_herstellung"],
    },
    "carbonsaeure_struktur": {
        "title": "Struktur", "skill": "carbonsaeure_struktur",
        "parts": [("carbonsaeure_struktur", 4)], "hand": HAND["carbonsaeure_struktur"],
    },
    "alkansaeuren_eigenschaften": {
        "title": "Eigenschaften und Verwendung", "skill": "carbonsaeure_eigenschaften",
        "parts": [("carbonsaeure_eigenschaften", 4)], "hand": HAND["alkansaeuren_eigenschaften"],
    },
    "alkansaeuren_trends": {
        "title": "Änderung der Eigenschaften", "skill": "carbonsaeure_eigenschaften",
        "parts": [], "hand": HAND["alkansaeuren_trends"],
    },
    "aminosaeuren": {
        "title": "Aminosäuren", "skill": "aminosaeuren",
        "parts": [("aminosaeuren", 4)], "hand": HAND["aminosaeuren"],
    },
    # Unit 6 – esters and fats
    "ester_eigenschaften": {
        "title": "Eigenschaften und Verwendung", "skill": "fette",
        "parts": [("fette", 4)], "hand": HAND["ester_eigenschaften"],
    },
    "ester_struktur": {
        "title": "Struktur von Estern", "skill": "ester",
        "parts": [("ester", 5)], "hand": [],
    },
    "ester_synthese": {
        "title": "Synthese und Analyse", "skill": "ester",
        "parts": [], "hand": HAND["ester_synthese"],
    },
    "kondensation_hydrolyse": {
        "title": "Kondensationsreaktion und Hydrolyse", "skill": "ester",
        "parts": [], "hand": HAND["kondensation_hydrolyse"],
    },
    "fettsaeuren_seifen": {
        "title": "Fettsäuren und deren Salze", "skill": "fette",
        "parts": [("fette", 4)], "hand": HAND["fettsaeuren_seifen"],
    },
}


def _build_quiz(sub_id: str, spec: dict) -> dict:
    """Generate a deterministic five-question bank for one subtopic."""
    rng = random.Random(f"subtopic-{sub_id}")
    questions: list[dict] = []
    seen: set[str] = set()

    def add(q: dict) -> None:
        prompt = q["prompt"].strip()
        if not prompt or prompt in seen:
            return
        seen.add(prompt)
        q = {**q, "id": f"{sub_id}-{len(questions) + 1}"}
        questions.append(q)

    for skill, count in spec["parts"]:
        added = 0
        for _ in range(160):
            if added >= count:
                break
            before = len(questions)
            add(generate(skill, rng, "").to_dict())
            if len(questions) > before:
                added += 1

    for q in spec["hand"]:
        add({**q})

    if len(questions) != 5:
        raise RuntimeError(f"{sub_id}: expected 5 questions, built {len(questions)}")
    return {"title": spec["title"], "skill": spec["skill"], "questions": questions}


QUIZZES: dict[str, dict] = {sub_id: _build_quiz(sub_id, spec) for sub_id, spec in SPECS.items()}


def get_quiz(sub_id: str) -> dict | None:
    return QUIZZES.get(sub_id)
