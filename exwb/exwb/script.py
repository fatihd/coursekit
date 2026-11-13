"""The book's script, from the profile's `"script"` (default `"hebrew"`; `"greek"` for the Greek books).

`apply(profile)` points the rule-based code at the right letters: the "script side" of an item (called `he` in the
code and database for historical reasons) is the side written in that script; only Hebrew lines are re-ordered
right-to-left; OCR picks the best-marked variant by that script's marks.
"""
import re
from . import detect, ocr

SCRIPTS = {
    "hebrew": {"letters": r"[֐-׿]", "ocr_letters": r"[א-ת]", "marks": r"[ְ-ׇּׁׂ]",
               "rtl": True, "keyboard": "he_IL", "label": "Hebrew"},
    "greek": {"letters": r"[Ͱ-Ͽἀ-῿]", "ocr_letters": r"[Ͱ-Ͽἀ-῿]",
              "marks": r"[̀́̓̔͂ͅἀ-῿]", "rtl": False, "keyboard": "el_GR",
              "label": "Greek"},
}
ACTIVE = {"name": "hebrew", **SCRIPTS["hebrew"]}


def apply(profile):
    name = (profile or {}).get("script", "hebrew")
    s = SCRIPTS[name]
    ACTIVE.clear(); ACTIVE.update(name=name, **s)
    detect.HEB = re.compile(s["letters"])
    detect.SCRIPT_RTL = s["rtl"]
    ocr.LETTERS = re.compile(s["ocr_letters"])
    ocr.POINTS = re.compile(s["marks"])
    return ACTIVE
