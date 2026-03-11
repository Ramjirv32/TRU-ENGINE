#!/usr/bin/env python3
"""
Standalone Gemini Validator
----------------------------
Runs ONLY the Gemini validation step on an already-processed _structured.json file.

Usage:
    python gemini_validate_only.py <structured_json_file> [audit_json_file]

Examples:
    # With audit context (best accuracy):
    python gemini_validate_only.py vit_chennai_structured.json vit_chennai_audit.json

    # Without audit context (Gemini uses its own knowledge only):
    python gemini_validate_only.py vit_chennai_structured.json

The corrected output overwrites the input structured.json file (a .bak backup is made).
"""

import json
import os
import sys

# Import everything from audit_processor (Gemini config, sections, validate function)
from audit_processor import (
    validate_with_gemini,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    finalize_output,
)


def run_gemini_only(structured_file: str, audit_file: str = None):
    if not os.path.exists(structured_file):
        print(f"❌ File not found: {structured_file}")
        sys.exit(1)

    # Load structured JSON
    with open(structured_file, "r") as f:
        structured = json.load(f)

    college_name = structured.get("college_name", "Unknown College")
    print(f"\n🔍 Gemini-only validation for: {college_name}")
    print(f"   Input:  {structured_file}")

    # Load audit sections if provided
    audit_sections = []
    if audit_file:
        if not os.path.exists(audit_file):
            print(f"⚠  Audit file not found: {audit_file} — proceeding without context")
        else:
            with open(audit_file, "r") as f:
                audit_data = json.load(f)
            audit_sections = audit_data.get("sections", [])
            print(f"   Audit:  {audit_file}  ({len(audit_sections)} sections)")
    else:
        print(f"   Audit:  (none) — Gemini will rely on training knowledge only")

    # Backup original
    backup_file = structured_file.replace(".json", ".bak.json")
    with open(backup_file, "w") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)
    print(f"   Backup: {backup_file}\n")

    # Run Gemini validation
    validated = validate_with_gemini(structured, audit_sections, college_name)

    if validated:
        # Re-run finalize to ensure all new fields get proper defaults
        validated = finalize_output(validated)

        with open(structured_file, "w") as f:
            json.dump(validated, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Validated output saved to: {structured_file}")

        # Show summary of what changed vs backup
        changed_keys = []
        for k in validated:
            old_val = structured.get(k)
            new_val = validated.get(k)
            if old_val != new_val:
                changed_keys.append(k)
        print(f"   Fields updated by Gemini: {len(changed_keys)}")
        if changed_keys:
            print(f"   Changed keys: {', '.join(changed_keys[:20])}")
            if len(changed_keys) > 20:
                print(f"   ... and {len(changed_keys) - 20} more")
    else:
        print(f"\n⚠  Gemini validation returned no data. Original file unchanged.")
        os.remove(backup_file)
        print(f"   (Backup removed)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    structured_arg = sys.argv[1]
    audit_arg = sys.argv[2] if len(sys.argv) >= 3 else None

    # Auto-detect audit file if not given (same name but _structured → _audit)
    if audit_arg is None:
        auto_audit = structured_arg.replace("_structured.json", "_audit.json")
        if os.path.exists(auto_audit):
            print(f"ℹ  Auto-detected audit file: {auto_audit}")
            audit_arg = auto_audit

    run_gemini_only(structured_arg, audit_arg)
