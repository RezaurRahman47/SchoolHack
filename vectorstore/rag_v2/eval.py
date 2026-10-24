"""Quick retrieval evaluation — prints hits + image gating, no LLM."""
from __future__ import annotations

import sys

from .store import get_store

QUESTIONS = [
    "Warum leitet eine Salzlösung Strom?",
    "Was ist der pH-Wert?",
    "Wie entsteht saurer Regen?",
    "Was passiert bei einer Neutralisation?",
    "Wie berechnet man die Stoffmengenkonzentration?",
    "Was sind Alkane?",
    "Warum hat Ethan einen höheren Siedepunkt als Methan?",
    "Was ist die homologe Reihe der Alkane?",
    "Wie funktioniert die Verseifung von Fett?",
    "Was ist eine Estergruppe?",
    "Warum ist Ethanol in Wasser löslich?",
    "Was sind Isomere?",
    "Wie entsteht Schwefelsäure?",
    "Was zeigt ein Indikator an?",
    "Wie funktioniert die fraktionierte Destillation von Erdöl?",
    "Was ist eine exotherme Reaktion?",
    "Was ist der Unterschied zwischen einer Säure und einer sauren Lösung?",
    "Wie entsteht Kalkseife in hartem Wasser?",
    "Was sind Kohlenwasserstoffe?",
    "Wie wird Bier gebraut?",
]


def main() -> None:
    store = get_store()
    print(f"docs: {len(store.ids)}  text: {len(store.text_idx)}  captions: {len(store.cap_idx)}\n")
    for q in QUESTIONS:
        hits = store.search_text(q, k=3)
        top = hits[0].dense if hits else 0
        pages = [h.meta.get("page", 0) for h in hits[:3]]
        imgs = store.search_images(q, pages, top, k=1)
        print(f"Q: {q}")
        for h in hits:
            print(f"   {h.dense:.3f} (bm {h.bm25:.2f}) p{h.meta.get('page')} "
                  f"[{h.meta.get('section', '')[:38]}] {h.text[:80]!r}")
        if imgs:
            i = imgs[0]
            print(f"   IMG {i['relevance']:.3f} p{i['page']} {i['caption'][:70]!r}")
        else:
            print("   IMG none")
        print()


if __name__ == "__main__":
    main()
