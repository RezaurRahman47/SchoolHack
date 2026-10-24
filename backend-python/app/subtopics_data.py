"""Core educational content for Chemie subtopics (RLP Berlin-Brandenburg Klasse 9).

Provides:
  1. Lernkarten (Core knowledge flashcard decks built without AI fluff).
  2. Interactive practice exercises:
     - True/False (Wahr/Falsch)
     - 2-Option inline sentence choice with animated selection
     - Sentence split in half with 2 completion options
"""
from __future__ import annotations

SUBTOPIC_DATA: dict[str, dict] = {
    "ionen": {
        "title": "Ionenladung bestimmen",
        "topic": "Grundlagen",
        "core_principle": "Metalle geben Valenzelektronen ab (positive Kationen), Nichtmetalle nehmen Elektronen auf (negative Anionen), um die Edelgaskonfiguration zu erreichen.",
        "flashcards": [
            {
                "id": "ionen_1",
                "title": "Kation vs. Anion",
                "front": "Was ist der fundamentale Unterschied zwischen einem Kation und einem Anion?",
                "back": "Ein Kation ist positiv geladen (+), weil das Atom Elektronen abgegeben hat (z. B. Na⁺, Ca²⁺). Ein Anion ist negativ geladen (-), weil das Atom Elektronen aufgenommen hat (z. B. Cl⁻, O²⁻).",
                "takeaway": "Metalle bilden Kationen (+), Nichtmetalle bilden Anionen (-).",
                "source": "Fokus Chemie S. 12 / RLP Klasse 9"
            },
            {
                "id": "ionen_2",
                "title": "Edelgasregel (Oktettregel)",
                "front": "Warum bilden Atome überhaupt Ionen?",
                "back": "Atome streben nach einer voll besetzten äußeren Elektronenschale (Edelgaskonfiguration mit 8 Valenzelektronen). Hauptgruppen-Elemente geben dazu Elektronen ab oder nehmen welche auf.",
                "takeaway": "Das Ziel jeder Ionenbildung ist ein stabiler energetischer Zustand wie bei Edelgasen.",
                "source": "Fokus Chemie S. 13"
            },
            {
                "id": "ionen_3",
                "title": "Hauptgruppe und Ladung",
                "front": "Wie liest man die Ladung aus dem Periodensystem ab?",
                "back": "1. Hauptgruppe (Alkalimetalle) -> immer 1+ (z. B. Na⁺)\n2. Hauptgruppe (Erdalkalimetalle) -> immer 2+ (z. B. Mg²⁺, Ca²⁺)\n7. Hauptgruppe (Halogene) -> immer 1- (z. B. Cl⁻, F⁻)\n6. Hauptgruppe -> meist 2- (z. B. O²⁻, S²⁻)",
                "takeaway": "Die Hauptgruppennummer verrät die Anzahl der Valenzelektronen.",
                "source": "Fokus Chemie S. 14"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Metall-Atome nehmen bei der Ionenbildung stets Elektronen auf und werden negativ geladen.",
                    "is_true": False,
                    "explanation": "Falsch! Metalle haben wenige Valenzelektronen und geben diese ab. Sie werden dadurch zu positiv geladenen Kationen."
                },
                {
                    "statement": "Calcium steht in der 2. Hauptgruppe und bildet daher zweifach positiv geladene Ca²⁺-Ionen.",
                    "is_true": True,
                    "explanation": "Richtig! Elemente der 2. Hauptgruppe geben ihre 2 Valenzelektronen ab."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Nichtmetallatome nehmen Elektronen auf und bilden dadurch ",
                    "opt1": "Anionen",
                    "opt2": "Kationen",
                    "suffix": ", welche eine negative Ladung tragen.",
                    "correct": "Anionen",
                    "explanation": "Elektronen sind negativ geladen. Die Aufnahme von Elektronen führt zu negativ geladenen Anionen."
                },
                {
                    "prefix": "Alkalimetalle aus der 1. Hauptgruppe wie Natrium besitzen ",
                    "opt1": "ein Valenzelektron",
                    "opt2": "zwei Valenzelektronen",
                    "suffix": " und bilden daher einfach positive Ionen.",
                    "correct": "ein Valenzelektron",
                    "explanation": "Die 1. Hauptgruppe hat genau ein Valenzelektron, das leicht abgegeben wird."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Wenn ein neutrales Chlor-Atom ein zusätzliches Elektron aufnimmt, entsteht ...",
                    "opt1": "ein einfach negativ geladenes Chlorid-Ion (Cl⁻).",
                    "opt2": "ein positiv geladenes Kation mit Protonenüberschuss.",
                    "correct": 0,
                    "explanation": "Durch Aufnahme eines negativen Elektrons entsteht das negativ geladene Anion Cl⁻."
                }
            ]
        }
    },
    "salzformel": {
        "title": "Salzformeln aufstellen",
        "topic": "Grundlagen",
        "core_principle": "In jeder Salzverbindung heben sich positive und negative Ionenladungen exakt auf – die Gesamtladung eines Salzes ist immer 0 (elektroneutral).",
        "flashcards": [
            {
                "id": "salz_1",
                "title": "Das Prinzip der Elektroneutralität",
                "front": "Welche Grundregel gilt für jede Salzformel?",
                "back": "Salzkristalle sind nach außen elektrisch neutral: Summe der positiven Kationenladungen = Summe der negativen Anionenladungen.",
                "takeaway": "Gesamtladung = 0. Das Kationen-Anionen-Verhältnis muss Ladungsgleichheit ergeben.",
                "source": "Fokus Chemie S. 16"
            },
            {
                "id": "salz_2",
                "title": "Das Überkreuz-Verfahren",
                "front": "Wie ermittelt man das Zahlenverhältnis (z. B. bei Al³⁺ und O²⁻)?",
                "back": "Die Ladungszahl des Kations wird zum Index des Anions und umgekehrt: Al³⁺ und O²⁻ -> 2 · (+3) + 3 · (-2) = 0 -> Al₂O₃.",
                "takeaway": "Überkreuz stellen, wenn nötig durch den gemeinsamen Teiler kürzen.",
                "source": "Fokus Chemie S. 17"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Ein Salzkristall wie Natriumchlorid trägt insgesamt eine positive elektrische Überschussladung.",
                    "is_true": False,
                    "explanation": "Falsch! Salze sind nach außen immer elektrisch neutral (Gesamtladung = 0)."
                },
                {
                    "statement": "Für Magnesiumionen (Mg²⁺) und Chloridionen (Cl⁻) lautet die korrekte Verhältnisformel MgCl₂.",
                    "is_true": True,
                    "explanation": "Richtig! Man benötigt zwei Cl⁻-Ionen (-2), um die zweifach positive Ladung von Mg²⁺ auszugleichen."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Um die zweifach positive Ladung eines Calciumions (Ca²⁺) auszugleichen, benötigt man ",
                    "opt1": "zwei einfach negative",
                    "opt2": "ein einfach negatives",
                    "suffix": " Chlorid-Ionen (Cl⁻).",
                    "correct": "zwei einfach negative",
                    "explanation": "+2 benötigt zweimal -1 zur Neutralität."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die Verhältnisformel von Aluminiumoxid mit Al³⁺ und O²⁻ lautet ...",
                    "opt1": "Al₂O₃, weil 2·(+3) + 3·(-2) genau null ergibt.",
                    "opt2": "Al₃O₂, weil Metalle immer den höheren Index erhalten.",
                    "correct": 0,
                    "explanation": "Das kleinste gemeinsame Vielfache von 3 und 2 ist 6, also 2 Al³⁺ und 3 O²⁻."
                }
            ]
        }
    },
    "ph_skala": {
        "title": "pH-Skala einordnen",
        "topic": "Säuren und Laugen",
        "core_principle": "Die pH-Skala reicht von 0 bis 14: pH < 7 ist sauer, pH = 7 ist neutral, pH > 7 ist alkalisch/basisch. Sie misst die Konzentration von Oxonium-Ionen.",
        "flashcards": [
            {
                "id": "ph_1",
                "title": "Die drei Bereiche der Skala",
                "front": "Welche Bereiche unterteilen die klassische pH-Skala von 0 bis 14?",
                "back": "• pH 0 bis < 7: Sauer (hohe H₃O⁺-Konzentration)\n• pH = 7: Neutral (Reinstwasser, [H₃O⁺] = [OH⁻])\n• pH > 7 bis 14: Basisch / alkalisch (hohe OH⁻-Konzentration)",
                "takeaway": "pH 7 ist der neutrale Wendepunkt; je kleiner der Wert, desto saurer.",
                "source": "Fokus Chemie S. 4"
            },
            {
                "id": "ph_2",
                "title": "Die Zehnerpotenz-Stufe",
                "front": "Was bedeutet eine Änderung um genau eine pH-Stufe?",
                "back": "Die pH-Skala ist logarithmisch! Eine pH-Stufe Unterschied bedeutet eine verzehnfachte (10x) oder gezehntelte Konzentration an H₃O⁺-Ionen. Eine Lösung mit pH 3 ist 100-mal saurer als eine mit pH 5.",
                "takeaway": "Jeder Schritt um 1 auf der Skala verzehnfacht die Säure- oder Laugenstärke.",
                "source": "Fokus Chemie S. 5"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Eine wässrige Lösung mit einem pH-Wert von 4 ist basisch.",
                    "is_true": False,
                    "explanation": "Falsch! Werte unter 7 sind sauer."
                },
                {
                    "statement": "Reines destilliertes Wasser bei 25 °C besitzt genau den pH-Wert 7 (neutral).",
                    "is_true": True,
                    "explanation": "Richtig! Reines Wasser ist weder sauer noch alkalisch, da H₃O⁺- und OH⁻-Ionen im Gleichgewicht stehen."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Lösungen mit einem pH-Wert kleiner als 7 sind ",
                    "opt1": "Säuren",
                    "opt2": "Laugen",
                    "suffix": ", da in ihnen die Konzentration an Oxonium-Ionen (H₃O⁺) überwiegt.",
                    "correct": "Säuren",
                    "explanation": "Säuren haben per Definition pH < 7, Laugen haben pH > 7."
                },
                {
                    "prefix": "Eine Rohrreiniger-Lösung mit Natronlauge hat typischerweise einen pH-Wert von etwa 13 und ist damit stark ",
                    "opt1": "alkalisch",
                    "opt2": "sauer",
                    "suffix": ".",
                    "correct": "alkalisch",
                    "explanation": "pH-Werte nahe 14 sind stark basisch bzw. alkalisch."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Vergleicht man eine Lösung mit pH 2 und eine Lösung mit pH 4, so ist die erste Lösung ...",
                    "opt1": "100-mal saurer, da die pH-Skala logarithmisch in Zehnerschritten verläuft.",
                    "opt2": "nur doppelt so sauer wie die zweite Lösung.",
                    "correct": 0,
                    "explanation": "Differenz von 2 pH-Stufen bedeutet 10² = 100-fache H₃O⁺-Konzentration."
                }
            ]
        }
    },
    "indikator": {
        "title": "Indikatorfarben deuten",
        "topic": "Säuren und Laugen",
        "core_principle": "Indikatoren sind Farbstoffe, die durch Farbänderung anzeigen, ob eine Lösung sauer, neutral oder alkalisch ist.",
        "flashcards": [
            {
                "id": "ind_1",
                "title": "Universalindikator",
                "front": "Welche Farben zeigt der Universalindikator bei Säuren, Neutralem und Laugen?",
                "back": "• Rot / Orange / Gelb = Sauer (pH 0 bis 6)\n• Grün = Neutral (pH 7)\n• Blau / Dunkelblau / Violett = Alkalisch (pH 8 bis 14)",
                "takeaway": "Rot = Sauer, Grün = Neutral, Blau = Basisch.",
                "source": "Fokus Chemie S. 4"
            },
            {
                "id": "ind_2",
                "title": "Phenolphthalein",
                "front": "Wie verhält sich der Spezialindikator Phenolphthalein?",
                "back": "• Im sauren und neutralen Bereich ist er vollkommen FARBLOS.\n• Im basischen Bereich (ab ca. pH 8,2) schlägt er schlagartig in leuchtendes PINK / MAGENTA um.",
                "takeaway": "Phenolphthalein eignet sich perfekt, um das Erreichen des Laugenbereichs zu erkennen.",
                "source": "Fokus Chemie S. 7"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Phenolphthalein färbt sich in saurer Salzsäure intensiv rot.",
                    "is_true": False,
                    "explanation": "Falsch! In saurer Lösung ist Phenolphthalein farblos. Erst in Laugen wird er pink/magenta."
                },
                {
                    "statement": "Färbt sich Universalindikatorpapier dunkelblau, liegt eine alkalische Lösung vor.",
                    "is_true": True,
                    "explanation": "Richtig! Blaue Färbung zeigt Laugen/Basen (pH > 7) an."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Wird Universalindikator in Essigessenz getropft, färbt sich die Flüssigkeit ",
                    "opt1": "rot",
                    "opt2": "blau",
                    "suffix": ", da Essig eine saure Lösung ist.",
                    "correct": "rot",
                    "explanation": "Säuren färben Universalindikator rot bis gelb."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Gibt man einige Tropfen Phenolphthalein zu Natronlauge, so beobachtet man ...",
                    "opt1": "eine intensive violett-rosa Färbung.",
                    "opt2": "ein vollständiges Entfärben zu einer klaren Lösung.",
                    "correct": 0,
                    "explanation": "Laugen schlagen Phenolphthalein in pink/violett um."
                }
            ]
        }
    },
    "saeurebildung": {
        "title": "Säurebildung (Oxid + Wasser)",
        "topic": "Säuren und Laugen",
        "core_principle": "Nichtmetalloxid + Wasser reagieren zu einer Säure (z. B. SO₂ + H₂O -> H₂SO₃; CO₂ + H₂O -> H₂CO₃).",
        "flashcards": [
            {
                "id": "saeureb_1",
                "title": "Nichtmetalloxid + Wasser",
                "front": "Wie entstehen saure Lösungen aus Verbrennungsprodukten?",
                "back": "Verbrennt man ein Nichtmetall (z. B. Schwefel, Kohlenstoff), entsteht ein Nichtmetalloxid. Löst man dieses Gas in Wasser, reagiert es chemisch zu einer Säure.",
                "takeaway": "Nichtmetalloxid + Wasser -> Säure (z. B. CO₂ + H₂O -> H₂CO₃).",
                "source": "Fokus Chemie S. 8"
            },
            {
                "id": "saeureb_2",
                "title": "Saurer Regen",
                "front": "Was ist der Zusammenhang zwischen Säurebildung und saurem Regen?",
                "back": "Schwefeldioxid (SO₂) und Stickoxide (NOₓ) aus Industrie und Verkehr reagieren mit dem Regenwasser in der Atmosphäre zu schwefliger Säure und Salpetersäure.",
                "takeaway": "Umweltfolge der Säurebildung: Saurer Regen schädigt Wälder und Gewässer.",
                "source": "Fokus Chemie S. 9"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Wenn Nichtmetalloxide wie Kohlenstoffdioxid in Wasser gelöst werden, sinkt der pH-Wert unter 7.",
                    "is_true": True,
                    "explanation": "Richtig! Es entsteht Kohlensäure (H₂CO₃), wodurch die Lösung sauer wird."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Löst man Schwefeldioxid (SO₂) in Wasser, entsteht ",
                    "opt1": "eine Säure",
                    "opt2": "eine Lauge",
                    "suffix": ", welche Indikatorpapier rot färbt.",
                    "correct": "eine Säure",
                    "explanation": "Nichtmetalloxid + Wasser = Säure (schweflige Säure H₂SO₃)."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die allgemeine Wortgleichung für die Entstehung von Säuren lautet ...",
                    "opt1": "Nichtmetalloxid + Wasser reagiert zu Säure.",
                    "opt2": "Metalloxid + Wasser reagiert zu Säure.",
                    "correct": 0,
                    "explanation": "Metalle bilden Laugen, Nichtmetalle bilden Säuren."
                }
            ]
        }
    },
    "laugenbildung": {
        "title": "Laugenbildung (Oxid + Wasser)",
        "topic": "Säuren und Laugen",
        "core_principle": "Metalloxid + Wasser reagieren zu einer Metallhydroxidlösung (Lauge) (z. B. CaO + H₂O -> Ca(OH)₂; Na₂O + H₂O -> 2 NaOH).",
        "flashcards": [
            {
                "id": "laugeb_1",
                "title": "Metalloxid + Wasser",
                "front": "Wie entsteht eine alkalische Lösung (Lauge) aus Metalloxiden?",
                "back": "Löst man ein unedles Metalloxid (z. B. Calciumoxid / Branntkalk CaO) in Wasser, bildet sich das Metallhydroxid (Lauge). Die Lösung enthält Hydroxid-Ionen (OH⁻).",
                "takeaway": "Metalloxid + Wasser -> Metallhydroxid (Lauge).",
                "source": "Fokus Chemie S. 10"
            },
            {
                "id": "laugeb_2",
                "title": "Das Hydroxid-Ion (OH⁻)",
                "front": "Welches Ion ist für die typischen Eigenschaften aller Laugen verantwortlich?",
                "back": "Das Hydroxid-Ion (OH⁻). Es bewirkt die blaue Indikatorfärbung, den pH-Wert > 7, das seifige Gefühl auf der Haut und die ätzende Wirkung auf Fette und Eiweiße.",
                "takeaway": "OH⁻ ist der chemische Träger der alkalischen Eigenschaften.",
                "source": "Fokus Chemie S. 11"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Für die basischen Eigenschaften einer Lauge sind stets Hydroxid-Ionen (OH⁻) verantwortlich.",
                    "is_true": True,
                    "explanation": "Richtig! Alle wässrigen Laugen enthalten einen Überschuss an Hydroxid-Ionen."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Bei der Reaktion von Calciumoxid mit Wasser entsteht ",
                    "opt1": "Kalkwasser",
                    "opt2": "Kohlensäure",
                    "suffix": ", eine alkalische Calciumhydroxidlösung.",
                    "correct": "Kalkwasser",
                    "explanation": "CaO + H₂O -> Ca(OH)₂ (Kalkwasser, eine Lauge)."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Wenn Magnesiumoxid mit Wasser in Kontakt kommt, bildet sich ...",
                    "opt1": "eine alkalische Magnesiumhydroxidlösung mit OH⁻-Ionen.",
                    "opt2": "eine saure Lösung mit vielen H₃O⁺-Ionen.",
                    "correct": 0,
                    "explanation": "Metalloxide reagieren mit Wasser zu Laugen (Hydroxiden)."
                }
            ]
        }
    },
    "saeure_metall": {
        "title": "Säure + Metall / Carbonat",
        "topic": "Säuren und Laugen",
        "core_principle": "Säure + unedles Metall -> Salz + Wasserstoff (H₂); Säure + Carbonat -> Salz + Wasser + Kohlenstoffdioxid (CO₂).",
        "flashcards": [
            {
                "id": "saeure_m_1",
                "title": "Säure greift unedle Metalle an",
                "front": "Was passiert, wenn Salzsäure auf unedle Metalle wie Zink oder Magnesium trifft?",
                "back": "Das Metall löst sich unter starkem Aufschäumen auf. Es entsteht brennbares Wasserstoffgas (H₂) und ein gelöstes Metallsalz (z. B. Zn + 2 HCl -> ZnCl₂ + H₂↑).",
                "takeaway": "Säure + unedles Metall -> Metallsalz + Wasserstoff (Knallgasprobe!).",
                "source": "Fokus Chemie S. 14"
            },
            {
                "id": "saeure_m_2",
                "title": "Säure auf Kalk (Carbonate)",
                "front": "Warum zischen Essig oder Salzsäure auf Marmor oder Muschelschalen?",
                "back": "Kalk ist Calciumcarbonat (CaCO₃). Säuren treiben die schwächere Kohlensäure aus, die sofort in Wasser und Kohlenstoffdioxid-Gas zerfällt (Aufbrausen).",
                "takeaway": "Säure + Carbonat -> Salz + Wasser + CO₂ (Nachweis mit Kalkwasser).",
                "source": "Fokus Chemie S. 15"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Bei der Reaktion von verdünnter Salzsäure mit Magnesium entsteht geruchloses Wasserstoffgas.",
                    "is_true": True,
                    "explanation": "Richtig! Mg + 2 HCl -> MgCl₂ + H₂↑."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Tropft man Salzsäure auf Kreide (Calciumcarbonat), entsteht sprudelnd ",
                    "opt1": "Kohlenstoffdioxid",
                    "opt2": "Wasserstoffgas",
                    "suffix": ", welches Kalkwasser trübt.",
                    "correct": "Kohlenstoffdioxid",
                    "explanation": "Carbonate spalten bei Kontakt mit Säuren CO₂ ab."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Gibt man ein Stück Zinkblech in verdünnte Schwefelsäure, so entweicht ...",
                    "opt1": "Wasserstoffgas, das mit der Knallgasprobe nachgewiesen werden kann.",
                    "opt2": "Sauerstoffgas, das einen glimmenden Span entzündet.",
                    "correct": 0,
                    "explanation": "Unedle Metalle werden oxidiert und bilden elementaren Wasserstoff (H₂)."
                }
            ]
        }
    },
    "neutralisation": {
        "title": "Neutralisation: Salz benennen",
        "topic": "Säuren und Laugen",
        "core_principle": "Säure + Lauge -> Salz + Wasser. H₃O⁺ + OH⁻ -> 2 H₂O. Der Name des Salzes setzt sich aus dem Kation der Lauge und dem Säurerest zusammen.",
        "flashcards": [
            {
                "id": "neut_1",
                "title": "Das Kernprinzip der Neutralisation",
                "front": "Was geschieht auf Teilchenebene bei der Neutralisation?",
                "back": "Die sauren Oxonium-Ionen (H₃O⁺) und die basischen Hydroxid-Ionen (OH⁻) reagieren im Verhältnis 1:1 zu neutralen Wassermolekülen: H₃O⁺ + OH⁻ -> 2 H₂O. Die Reaktion ist exotherm.",
                "takeaway": "Säure + Lauge -> Wasser + Salz.",
                "source": "Fokus Chemie S. 18"
            },
            {
                "id": "neut_2",
                "title": "Salznamen systematisch bilden",
                "front": "Wie leitet sich der Name des entstehenden Salzes ab?",
                "back": "Erster Teil = Metallkation aus der Lauge (z. B. Natrium...)\nZweiter Teil = Säurerestanion:\n• Salzsäure -> Chlorid\n• Schwefelsäure -> Sulfat\n• Salpetersäure -> Nitrat\n• Kohlensäure -> Carbonat",
                "takeaway": "Natronlauge + Salzsäure = Natriumchlorid + Wasser.",
                "source": "Fokus Chemie S. 19"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Bei der vollständigen Neutralisation von Salzsäure mit Natronlauge entsteht eine Lösung mit pH-Wert 7.",
                    "is_true": True,
                    "explanation": "Richtig! Die H₃O⁺- und OH⁻-Ionen neutralisieren sich vollständig zu Wasser."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Neutralisiert man Kalilauge mit Salpetersäure, entsteht das Salz ",
                    "opt1": "Kaliumnitrat",
                    "opt2": "Kaliumsulfat",
                    "suffix": " neben Wasser.",
                    "correct": "Kaliumnitrat",
                    "explanation": "Kalium (aus Kalilauge) + Nitrat (aus Salpetersäure) = Kaliumnitrat."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die Reaktionsprodukte einer Neutralisation zwischen Natronlauge und Schwefelsäure lauten ...",
                    "opt1": "Natriumsulfat und Wasser.",
                    "opt2": "Natriumchlorid und Wasserstoff.",
                    "correct": 0,
                    "explanation": "Schwefelsäure bildet Sulfate, die Lauge liefert Natrium."
                }
            ]
        }
    },
    "molare_masse": {
        "title": "Molare Masse berechnen",
        "topic": "Stoffmenge und Mol",
        "core_principle": "Die molare Masse M (Einheit: g/mol) ist die Masse von 1 Mol eines Stoffes. Man berechnet sie durch Aufsummieren der Atommassen aus dem Periodensystem.",
        "flashcards": [
            {
                "id": "molm_1",
                "title": "Definition der molaren Masse M",
                "front": "Was gibt die molare Masse M an und welche Einheit hat sie?",
                "back": "Sie gibt an, wie viel Gramm genau 1 Mol (6,022 · 10²³ Teilchen) eines Stoffes wiegen. Ihre Einheit ist g/mol. Der Zahlenwert entspricht der relativen Atommasse im PSE.",
                "takeaway": "M = m / n (Einheit: g/mol).",
                "source": "Fokus Chemie S. 20"
            },
            {
                "id": "molm_2",
                "title": "Moleküle aufsummieren",
                "front": "Wie berechnet man M für Wasser (H₂O)?",
                "back": "Aus dem PSE:\nH = 1,0 g/mol, O = 16,0 g/mol.\nM(H₂O) = 2 · 1,0 + 1 · 16,0 = 18,0 g/mol.",
                "takeaway": "Jedes Atom im Molekül mit seinem Index multiplizieren und addieren.",
                "source": "Fokus Chemie S. 21"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Die molare Masse von Sauerstoffgas (O₂) beträgt 16 g/mol.",
                    "is_true": False,
                    "explanation": "Falsch! Ein Sauerstoff-Atom hat 16 g/mol, das Molekül O₂ besteht aus 2 Atomen und hat M = 32 g/mol."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Die atomare Masse eines Elements im Periodensystem entspricht zahlenmäßig direkt seiner molaren Masse in ",
                    "opt1": "g/mol",
                    "opt2": "kg/l",
                    "suffix": ".",
                    "correct": "g/mol",
                    "explanation": "Die Einheit der molaren Masse ist Gramm pro Mol (g/mol)."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Um die molare Masse von Kohlendioxid (CO₂) zu berechnen, ...",
                    "opt1": "addiert man die Masse von 1 Kohlenstoff-Atom (12 g/mol) und 2 Sauerstoff-Atomen (2·16 g/mol) zu 44 g/mol.",
                    "opt2": "multipliziert man die Masse von Kohlenstoff mit der doppelten Ordnungszahl.",
                    "correct": 0,
                    "explanation": "M(CO₂) = 12 + 2 · 16 = 44 g/mol."
                }
            ]
        }
    },
    "stoffmenge": {
        "title": "Stoffmenge n = m / M",
        "topic": "Stoffmenge und Mol",
        "core_principle": "Die Stoffmenge n (Einheit: mol) verknüpft die wägbare Masse m (in g) mit der Teilchenzahl über n = m / M.",
        "flashcards": [
            {
                "id": "stoffm_1",
                "title": "Die Grundformel n = m / M",
                "front": "Wie lautet die fundamentale Beziehung zwischen Stoffmenge, Masse und molarer Masse?",
                "back": "n = m / M\n• n = Stoffmenge in mol\n• m = Masse in Gramm (g)\n• M = molare Masse in g/mol\nUmgestellt: m = n · M",
                "takeaway": "Masse geteilt durch molare Masse ergibt die Stoffmenge in mol.",
                "source": "Fokus Chemie S. 22"
            },
            {
                "id": "stoffm_2",
                "title": "Was ist 1 Mol?",
                "front": "Wie viele Teilchen enthält genau 1 Mol eines Stoffes?",
                "back": "1 Mol enthält rund 6,022 · 10²³ Teilchen (Avogadro-Konstante N_A). Das ist das 'Dutzend' der Chemiker, um mikroskopische Atome wägbar zu machen.",
                "takeaway": "1 mol = 602 Trilliarden Teilchen.",
                "source": "Fokus Chemie S. 23"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Wenn man 36 g Wasser (M = 18 g/mol) hat, entspricht dies genau 2 mol Wasser.",
                    "is_true": True,
                    "explanation": "Richtig! n = m / M = 36 g / 18 g/mol = 2 mol."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Möchte man die Masse m aus der Stoffmenge n berechnen, muss man die Stoffmenge mit der molaren Masse ",
                    "opt1": "multiplizieren",
                    "opt2": "dividieren",
                    "suffix": " (Formel: m = n · M).",
                    "correct": "multiplizieren",
                    "explanation": "Umstellen von n = m / M liefert m = n · M."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die Einheit der chemischen Stoffmenge n lautet ...",
                    "opt1": "Mol (Einheitenzeichen: mol).",
                    "opt2": "Gramm pro Liter (g/l).",
                    "correct": 0,
                    "explanation": "Die Stoffmenge misst die Teilchenportion und wird in Mol angegeben."
                }
            ]
        }
    },
    "konzentration": {
        "title": "Konzentration c = n / V",
        "topic": "Stoffmenge und Mol",
        "core_principle": "Die Stoffmengenkonzentration c gibt an, wie viel Mol eines gelösten Stoffes in einem Liter Lösung enthalten sind (c = n / V in mol/l).",
        "flashcards": [
            {
                "id": "konz_1",
                "title": "Formel c = n / V",
                "front": "Wie ist die Stoffmengenkonzentration c definiert?",
                "back": "c = n / V\n• c = Konzentration in mol/l (oder M)\n• n = Stoffmenge des gelösten Stoffes in mol\n• V = Volumen der gesamten Lösung in Litern (l)",
                "takeaway": "Mol pro Liter Lösung = Stoffmengenkonzentration c.",
                "source": "Fokus Chemie S. 24"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Löst man 1 mol Natriumchlorid in 2 Litern Wasser auf, beträgt die Konzentration 2 mol/l.",
                    "is_true": False,
                    "explanation": "Falsch! c = n / V = 1 mol / 2 l = 0,5 mol/l."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Wird eine Salzlösung mit reinem Wasser verdünnt, so ",
                    "opt1": "sinkt",
                    "opt2": "steigt",
                    "suffix": " ihre Stoffmengenkonzentration c.",
                    "correct": "sinkt",
                    "explanation": "Das Volumen V wird größer bei unveränderter Stoffmenge n -> c sinkt."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die Formel zur Berechnung der Konzentration einer Lösung lautet ...",
                    "opt1": "c = n / V mit der Einheit mol/l.",
                    "opt2": "c = m · V mit der Einheit g·l.",
                    "correct": 0,
                    "explanation": "c = Stoffmenge n geteilt durch Volumen V."
                }
            ]
        }
    },
    "ph_rechnen": {
        "title": "pH-Wert berechnen",
        "topic": "Säuren und Laugen",
        "core_principle": "Der pH-Wert ist der negative dekadische Logarithmus der Oxonium-Ionenkonzentration: pH = -log₁₀(c(H₃O⁺)). Bei c = 0,01 mol/l ist pH = 2.",
        "flashcards": [
            {
                "id": "ph_r_1",
                "title": "pH = -log c(H₃O⁺)",
                "front": "Wie lautet die mathematische Formel zur Berechnung des pH-Wertes?",
                "back": "pH = -log₁₀[c(H₃O⁺)]\nZehnerpotenz-Merkhilfe für glatte Werte:\n• c = 0,1 mol/l = 10⁻¹ mol/l -> pH = 1\n• c = 0,01 mol/l = 10⁻² mol/l -> pH = 2\n• c = 0,001 mol/l = 10⁻³ mol/l -> pH = 3",
                "takeaway": "Der Exponent der Zehnerpotenz (ohne Minuszeichen) ist der pH-Wert.",
                "source": "Fokus Chemie S. 26"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Eine Salzsäurelösung mit c(HCl) = 0,001 mol/l hat den pH-Wert 3.",
                    "is_true": True,
                    "explanation": "Richtig! 0,001 = 10⁻³, also ist pH = 3."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Verdünnt man eine starke Säure um den Faktor 10 mit Wasser, so ",
                    "opt1": "steigt",
                    "opt2": "sinkt",
                    "suffix": " ihr pH-Wert um genau 1 Einheit.",
                    "correct": "steigt",
                    "explanation": "Verdünnen macht die Säure schwächer, der pH-Wert wandert nach oben in Richtung 7."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Eine Lösung mit einer H₃O⁺-Konzentration von 10⁻⁵ mol/l besitzt ...",
                    "opt1": "einen pH-Wert von genau 5.",
                    "opt2": "einen pH-Wert von minus 5.",
                    "correct": 0,
                    "explanation": "pH ist der negative Logarithmus: -(-5) = 5."
                }
            ]
        }
    },
    "alkan_formel": {
        "title": "Alkane: Summenformel",
        "topic": "Kohlenwasserstoffe",
        "core_principle": "Alkane sind gesättigte Kohlenwasserstoffe mit Einfachbindungen. Ihre allgemeine Summenformel lautet CₙH₂ₙ₊₂.",
        "flashcards": [
            {
                "id": "alk_f_1",
                "title": "Die allgemeine Formel CₙH₂ₙ₊₂",
                "front": "Wie berechnet man die Anzahl der Wasserstoffatome bei Alkanen?",
                "back": "Für n Kohlenstoffatome (C) gilt:\nH = 2 · n + 2\nBeispiel Propan (3 C-Atome):\nH = 2 · 3 + 2 = 8 -> Summenformel C₃H₈.",
                "takeaway": "CₙH₂ₙ₊₂: 'Das Doppelte plus zwei'.",
                "source": "Fokus Chemie S. 28"
            },
            {
                "id": "alk_f_2",
                "title": "Gesättigte Kohlenwasserstoffe",
                "front": "Was bedeutet 'gesättigt' bei Alkanen?",
                "back": "Alle Kohlenstoffatome sind ausschließlich durch Einfachbindungen (C-C) miteinander verknüpft. Jedes C-Atom bindet maximal viele Wasserstoffatome (vierbindiger Kohlenstoff).",
                "takeaway": "Alkane besitzen nur C-C-Einfachbindungen und keine Doppelbindungen.",
                "source": "Fokus Chemie S. 29"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Ein Alkan mit 4 Kohlenstoffatomen (Butan) besitzt die Summenformel C₄H₁₀.",
                    "is_true": True,
                    "explanation": "Richtig! 2 · 4 + 2 = 10 Wasserstoffatome."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Alkane werden als gesättigt bezeichnet, weil zwischen den Kohlenstoffatomen ausschließlich ",
                    "opt1": "Einfachbindungen",
                    "opt2": "Doppelbindungen",
                    "suffix": " vorliegen.",
                    "correct": "Einfachbindungen",
                    "explanation": "Alkane haben nur C-C-Einfachbindungen; Alkene haben Doppelbindungen."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die Summenformel eines Alkans mit 6 Kohlenstoffatomen lautet ...",
                    "opt1": "C₆H₁₄, da 2·6 + 2 = 14 ergibt (Hexan).",
                    "opt2": "C₆H₁₂, da die Wasserstoffzahl genau dem Doppelten entspricht.",
                    "correct": 0,
                    "explanation": "Formel CₙH₂ₙ₊₂ -> 2·6 + 2 = 14."
                }
            ]
        }
    },
    "alkan_name": {
        "title": "Alkane: Namen (IUPAC)",
        "topic": "Kohlenwasserstoffe",
        "core_principle": "Die homologe Reihe der ersten 10 Alkane: Methan (C₁), Ethan (C₂), Propan (C₃), Butan (C₄), Pentan (C₅), Hexan (C₆), Heptan (C₇), Octan (C₈), Nonan (C₉), Decan (C₁₀).",
        "flashcards": [
            {
                "id": "alk_n_1",
                "title": "Die ersten vier Alkane (Historische Namen)",
                "front": "Wie heißen die ersten 4 unverzweigten Alkane (C₁ bis C₄)?",
                "back": "1. Methan (CH₄)\n2. Ethan (C₂H₆)\n3. Propan (C₃H₈)\n4. Butan (C₄H₁₀)\nEselsbrücke: 'Mein Elefant Putzt Brille'.",
                "takeaway": "Die ersten 4 haben historische Trivialnamen, ab C₅ folgen griechische Zahlwörter.",
                "source": "Fokus Chemie S. 30"
            },
            {
                "id": "alk_n_2",
                "title": "Ab C₅: Griechische Zahlwörter",
                "front": "Wie werden Alkane ab 5 Kohlenstoffatomen benannt?",
                "back": "Griechische Vorsilbe + Endung '-an':\n• Penta- (5) -> Pentan\n• Hexa- (6) -> Hexan\n• Hepta- (7) -> Heptan\n• Octa- (8) -> Octan\n• Nona- (9) -> Nonan\n• Deca- (10) -> Decan",
                "takeaway": "Die Endung '-an' kennzeichnet stets die Stoffklasse der Alkane.",
                "source": "Fokus Chemie S. 31"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Das Alkan mit der Summenformel C₅H₁₂ heißt Propan.",
                    "is_true": False,
                    "explanation": "Falsch! 5 C-Atome = Pentan. Propan hat nur 3 C-Atome (C₃H₈)."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Das Alkan mit genau 8 Kohlenstoffatomen im Molekül trägt den Namen ",
                    "opt1": "Octan",
                    "opt2": "Decan",
                    "suffix": " (Bestandteil von Autobenzin).",
                    "correct": "Octan",
                    "explanation": "Octa = 8; Deca = 10."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die ersten vier Glieder der homologen Reihe der Alkane heißen in richtiger Reihenfolge ...",
                    "opt1": "Methan, Ethan, Propan, Butan.",
                    "opt2": "Ethan, Methan, Butan, Propan.",
                    "correct": 0,
                    "explanation": "C₁=Methan, C₂=Ethan, C₃=Propan, C₄=Butan."
                }
            ]
        }
    },
    "siedetrend": {
        "title": "Siedepunkte & Van-der-Waals",
        "topic": "Kohlenwasserstoffe",
        "core_principle": "Mit zunehmender Kettenlänge steigen die Van-der-Waals-Kräfte zwischen den Alkanmolekülen, wodurch die Siedetemperatur kontinuierlich ansteigt.",
        "flashcards": [
            {
                "id": "siede_1",
                "title": "Van-der-Waals-Kräfte",
                "front": "Warum halten Alkanmoleküle überhaupt zusammen, obwohl sie unpolar sind?",
                "back": "Durch kurzzeitige asymmetrische Elektronenverteilungen entstehen spontane und induzierte Dipole. Diese schwachen zwischenmolekularen Anziehungskräfte heißen Van-der-Waals-Kräfte.",
                "takeaway": "Größere Moleküloberfläche = stärkere Van-der-Waals-Kräfte.",
                "source": "Fokus Chemie S. 32"
            },
            {
                "id": "siede_2",
                "title": "Aggregatzustände bei Raumtemperatur",
                "front": "Wie verändern sich die Aggregatzustände mit wachsender Kette?",
                "back": "• C₁ bis C₄: Gase (Methan, Ethan, Propan, Butan)\n• C₅ bis C₁₆: Flüssigkeiten (Benzin, Diesel)\n• ab C₁₇: Feststoffe (Paraffinkerzen)",
                "takeaway": "Längere Kette -> höhere Siedetemperatur -> Wechsel von gasförmig zu flüssig zu fest.",
                "source": "Fokus Chemie S. 33"
            }
        ],
        "practice": {
            "true_false": [
                {
                    "statement": "Methan (CH₄) hat bei Raumtemperatur eine höhere Siedetemperatur als Hexan (C₆H₁₄).",
                    "is_true": False,
                    "explanation": "Falsch! Methan ist bei Raumtemperatur gasförmig (Siedepunkt -162 °C), während Hexan flüssig ist (Siedepunkt +69 °C)."
                }
            ],
            "sentence_choice": [
                {
                    "prefix": "Je länger die Kohlenstoffkette eines Alkans wird, desto ",
                    "opt1": "stärker",
                    "opt2": "schwächer",
                    "suffix": " werden die Van-der-Waals-Kräfte zwischen den Molekülen.",
                    "correct": "stärker",
                    "explanation": "Größere Moleküle haben mehr Berührungsfläche und Elektronen -> stärkere Anziehung."
                }
            ],
            "sentence_split": [
                {
                    "half1": "Die Zunahme der Siedetemperaturen innerhalb der homologen Reihe der Alkane erklärt sich durch ...",
                    "opt1": "immer stärkere zwischenmolekulare Van-der-Waals-Kräfte bei wachsender Molekülmasse.",
                    "opt2": "die Bildung starker kovalenter Atombindungen zwischen verschiedenen Molekülen.",
                    "correct": 0,
                    "explanation": "Zwischen den Alkanmolekülen wirken Van-der-Waals-Kräfte, die mit der Kettenlänge zunehmen."
                }
            ]
        }
    }
}


def get_subtopic_data(skill_id: str) -> dict | None:
    return SUBTOPIC_DATA.get(skill_id)
