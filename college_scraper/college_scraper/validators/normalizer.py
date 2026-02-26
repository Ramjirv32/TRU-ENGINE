"""
validators/normalizer.py – Rule 4: Duplicate Detection & Normalization
=======================================================================
Normalizes programme/department names to canonical forms so duplicates
like these are detected:

  "Computer Science & Engineering"
  "Computer Science and Engineering"
  "CSE"
  "Comp. Sci. & Engg."

All map to → "Computer Science and Engineering"
"""
from __future__ import annotations

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Canonical name mapping
# ─────────────────────────────────────────────────────────────────────────────
_ABBREVIATION_MAP: dict[str, str] = {
    "cse":    "Computer Science and Engineering",
    "ece":    "Electronics and Communication Engineering",
    "eee":    "Electrical and Electronics Engineering",
    "ee":     "Electrical Engineering",
    "me":     "Mechanical Engineering",
    "ce":     "Civil Engineering",
    "che":    "Chemical Engineering",
    "ae":     "Aerospace Engineering",
    "bt":     "Biotechnology",
    "it":     "Information Technology",
    "mme":    "Metallurgical and Materials Engineering",
    "maths":  "Mathematics",
    "phy":    "Physics",
    "chem":   "Chemistry",
    "bio":    "Biology",
    "econ":   "Economics",
    "mba":    "Master of Business Administration",
    "bba":    "Bachelor of Business Administration",
    "ai":     "Artificial Intelligence",
    "ml":     "Machine Learning",
    "ds":     "Data Science",
    "ai&ds":  "Artificial Intelligence and Data Science",
    "ai & ds":"Artificial Intelligence and Data Science",
    "csbs":   "Computer Science and Business Systems",
    "vlsi":   "VLSI Design",
    "iot":    "Internet of Things",
    "r&a":    "Robotics and Automation",
}

# Words that should be expanded
_WORD_EXPANSIONS: dict[str, str] = {
    "&": "and",
    "engg": "Engineering",
    "engg.": "Engineering",
    "eng": "Engineering",
    "eng.": "Engineering",
    "sci": "Science",
    "sci.": "Science",
    "comp": "Computer",
    "comp.": "Computer",
    "tech": "Technology",
    "tech.": "Technology",
    "mgmt": "Management",
    "mgmt.": "Management",
    "admin": "Administration",
    "admin.": "Administration",
    "elec": "Electronics",
    "elec.": "Electronics",
    "elect": "Electrical",
    "mech": "Mechanical",
    "mech.": "Mechanical",
    "comm": "Communication",
    "comm.": "Communication",
    "info": "Information",
    "info.": "Information",
}


def normalize_name(name: str) -> str:
    """
    Normalize a programme or department name to a canonical form.

    Steps:
      1. Check direct abbreviation map (case-insensitive)
      2. Expand known abbreviations within the string
      3. Normalize whitespace and "&" → "and"
      4. Title-case the result
    """
    if not name:
        return ""

    stripped = name.strip()

    # Step 1: Direct abbreviation lookup
    lower = stripped.lower()
    if lower in _ABBREVIATION_MAP:
        return _ABBREVIATION_MAP[lower]

    # Step 2: Expand word-by-word
    words = stripped.split()
    expanded = []
    for w in words:
        w_lower = w.lower().rstrip(".,")
        if w_lower in _WORD_EXPANSIONS:
            expanded.append(_WORD_EXPANSIONS[w_lower])
        elif w == "&":
            expanded.append("and")
        else:
            expanded.append(w)

    result = " ".join(expanded)

    # Step 3: Normalize whitespace
    result = re.sub(r"\s+", " ", result).strip()

    return result


def deduplicate_list(items: list[str]) -> list[str]:
    """
    Remove duplicates from a list of names after normalization.
    Returns the canonical form of each unique entry, preserving order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        canonical = normalize_name(item).lower()
        if canonical not in seen:
            seen.add(canonical)
            result.append(normalize_name(item))
    return result


def find_duplicates(items: list[str]) -> dict[str, list[str]]:
    """
    Find items that normalise to the same canonical form.
    Returns {canonical_form: [original_1, original_2, ...]}.
    """
    groups: dict[str, list[str]] = {}
    for item in items:
        canonical = normalize_name(item).lower()
        groups.setdefault(canonical, []).append(item)

    # Only return groups with duplicates
    return {k: v for k, v in groups.items() if len(v) > 1}


def normalize_college_data(data: dict) -> dict:
    """
    Normalize all programme and department names in a college data dict.
    Returns a new dict with normalized names.

    This mutates lists in-place for efficiency within the pipeline.
    """
    for field_name in ("ug_programs", "pg_programs", "phd_programs", "departments"):
        if field_name in data and isinstance(data[field_name], list):
            data[field_name] = deduplicate_list(data[field_name])
    return data
