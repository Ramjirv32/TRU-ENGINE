#!/usr/bin/env python3
"""
run_llm_verify.py – Read JSON → Send to LLM → Store corrected JSON
====================================================================
Usage:
    python run_llm_verify.py kpriet
    python run_llm_verify.py output/kpriet.json
    python run_llm_verify.py --all
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from college_scraper.llm.verifier import LLMVerifier

GROQ_API_KEY = "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"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
VERIFIED_DIR = os.path.join(OUTPUT_DIR, "verified")


def find_json(name: str) -> str | None:
    """Resolve a college name/slug/path to an actual JSON file."""
    # If it's already a valid path
    for candidate in [name, os.path.join(SCRIPT_DIR, name), os.path.join(OUTPUT_DIR, name)]:
        if os.path.isfile(candidate):
            return candidate

    # Try slug match in output/
    slug = os.path.splitext(os.path.basename(name))[0]
    for f in glob.glob(os.path.join(OUTPUT_DIR, "*.json")):
        bn = os.path.basename(f).lower()
        if "verified" in bn or "colleges_all" in bn:
            continue
        if slug.lower() in bn:
            return f

    # Try with .json appended
    direct = os.path.join(OUTPUT_DIR, f"{slug}.json")
    if os.path.isfile(direct):
        return direct

    return None


def _apply_additional_details_overrides(data: dict) -> None:
    """
    Override placements_by_year package values with authoritative values from
    additional_details (the raw scraped structured list).

    Supports per-year entries like "Highest Package (2023)" / "Median CTC (2024)"
    etc., mapping them into placements_by_year[year] and also keeps the legacy
    "placements" flat dict in sync for backward compatibility.
    """
    details = data.get("additional_details")
    if not details or not isinstance(details, list):
        return

    # Build lookup: category → value
    lookup: dict[str, str] = {}
    for entry in details:
        if isinstance(entry, dict):
            cat = str(entry.get("category", "")).strip()
            val = entry.get("value", "")
            if cat and val:
                lookup[cat] = str(val).strip()

    overrides_applied = []
    years = [2023, 2024, 2025]

    # ── Per-year overrides into placements_by_year ─────────────────────────────
    pby = data.get("placements_by_year")
    if not isinstance(pby, dict):
        pby = {}
        data["placements_by_year"] = pby

    pkg_map = {
        "highest_package": "Highest Package",
        "median_package":  "Median CTC",
        "lowest_package":  "Lowest Package",
    }

    for year in years:
        yr_str = str(year)
        if yr_str not in pby:
            pby[yr_str] = {}
        slot = pby[yr_str]
        for field, label in pkg_map.items():
            key = f"{label} ({year})"
            if key in lookup:
                old = slot.get(field)
                new = lookup[key]
                if old != new:
                    slot[field] = new
                    overrides_applied.append(
                        f"placements_by_year[{year}].{field}: {old!r} → {new!r} (from additional_details)"
                    )

    # ── Also sync latest year into legacy flat placements dict ────────────────
    latest_yr = str(max(years))
    placements = data.get("placements")
    if isinstance(placements, dict) and latest_yr in pby:
        for field in ("highest_package", "median_package", "lowest_package"):
            if field in pby[latest_yr]:
                old = placements.get(field)
                new = pby[latest_yr][field]
                if old != new:
                    placements[field] = new
                    overrides_applied.append(
                        f"placements.{field}: {old!r} → {new!r} (synced from placements_by_year[{latest_yr}])"
                    )

    if overrides_applied:
        existing = data.get("llm_corrections", [])
        data["llm_corrections"] = existing + overrides_applied
        print(f"  🔧 additional_details overrides applied:")
        for msg in overrides_applied:
            print(f"     • {msg}")


def main():
    # Parse args (support both "kpriet" and "--college kpriet" and "output/kpriet.json")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    # Handle --college <name> syntax
    for i, flag in enumerate(sys.argv[1:], 1):
        if flag in ("--college", "-c") and i < len(sys.argv) - 1:
            args.append(sys.argv[i + 1])
            break

    do_all = "--all" in flags

    if do_all:
        all_files = glob.glob(os.path.join(OUTPUT_DIR, "*.json"))
        args = [
            os.path.basename(f).replace(".json", "")
            for f in all_files
            if "verified" not in f and "colleges_all" not in f
        ]

    if not args:
        print("Usage:")
        print("  python run_llm_verify.py kpriet")
        print("  python run_llm_verify.py output/kpriet.json")
        print("  python run_llm_verify.py --all")
        sys.exit(1)

    verifier = LLMVerifier(api_key=GROQ_API_KEY)
    os.makedirs(VERIFIED_DIR, exist_ok=True)

    for name in args:
        filepath = find_json(name)
        if not filepath:
            print(f"❌ No JSON found for '{name}' in {OUTPUT_DIR}/")
            continue

        # 1. Read JSON
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = raw[0] if isinstance(raw, list) else raw
        college = data.get("college_name", os.path.basename(filepath))
        print(f"\n📄 Read: {filepath} → {college}")

        # 2. Send to LLM
        print(f"🤖 Sending to Groq ({verifier.model})...")
        corrected = verifier.verify(data)

        # 3a. Enforce additional_details → placements overrides
        _apply_additional_details_overrides(corrected)

        # 3. Post-process: update stale metadata after LLM corrections
        from datetime import date
        corrections = corrected.get("llm_corrections", [])
        if corrected.get("llm_verified"):
            # Recalculate confidence: base 0.75 + bonus for fewer unknowns
            corrected["data_confidence_score"] = round(
                min(0.75 + len(corrections) * 0.005, 0.93), 3
            )
            corrected["last_updated"] = str(date.today())
            corrected["data_version"] = "2026.3_multi_year"
            # Drop stale validation_report (numbers no longer match after LLM edits)
            corrected.pop("validation_report", None)
            # Update field confidence: all corrected fields → 0.90
            fc = corrected.get("field_confidence", {})
            for entry in corrections:
                if isinstance(entry, str) and "→" in entry:
                    field = entry.split(":")[0].strip()
                    if field in fc:
                        fc[field] = 0.90
            corrected["field_confidence"] = fc

        # 4. Save corrected JSON
        slug = os.path.splitext(os.path.basename(filepath))[0]
        out_path = os.path.join(VERIFIED_DIR, f"{slug}_verified.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(corrected, f, ensure_ascii=False, indent=2)

        print(f"💾 Saved: {out_path}")
        print(f"📊 Confidence score: {corrected.get('data_confidence_score')}")

        if corrections:
            print(f"📝 Corrections ({len(corrections)}):")
            for c in corrections:
                print(f"   • {c}" if isinstance(c, str) else f"   • {c}")

        if len(args) > 1:
            time.sleep(1.5)

    print(f"\n✅ Done — verified files in {VERIFIED_DIR}/")


if __name__ == "__main__":
    main()
