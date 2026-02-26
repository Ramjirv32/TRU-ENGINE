"""
validators/rules.py – Individual Validation Rules
===================================================
Each rule takes a college data dict and returns a RuleResult.

Rules:
  ✅ Rule 1 – Math Validation   (UG + PG + PhD ≈ Total)
  ✅ Rule 2 – Placement Logic    (placed ≤ total; rate = placed/eligible)
  ✅ Rule 3 – Ranking Consistency (NIRF rank exists in known range)
  ✅ Rule 4 – Fee Sanity          (min ≤ max; non-negative)
  ✅ Rule 5 – Gender Ratio        (male + female = 100)
  ✅ Rule 6 – Department/Program cross-check
  ✅ Rule 7 – Required fields present
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleResult:
    """Outcome of a single validation rule."""
    rule_name: str
    passed: bool
    severity: str = "info"          # "error" | "warning" | "info"
    message: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule": self.rule_name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1: Math Validation – student counts must add up
# ─────────────────────────────────────────────────────────────────────────────
def rule_student_count_math(data: dict) -> RuleResult:
    """Check: UG + PG + PhD ≈ Total students (within 5% tolerance)."""
    stats = data.get("student_statistics", [])
    vals = {s["category"]: s["value"] for s in stats if isinstance(s, dict)}

    total = _extract_int(vals, "Total students")
    ug    = _extract_int(vals, "Undergraduate")
    pg    = _extract_int(vals, "Postgraduate")
    phd   = _extract_int(vals, "PhD students")

    if total == 0:
        return RuleResult(
            rule_name="student_count_math",
            passed=False,
            severity="warning",
            message="Total students is 0 or missing",
        )

    computed = ug + pg + phd
    diff_pct = abs(computed - total) / total * 100

    if diff_pct > 5:
        return RuleResult(
            rule_name="student_count_math",
            passed=False,
            severity="error",
            message=f"UG({ug}) + PG({pg}) + PhD({phd}) = {computed} ≠ Total({total}), diff {diff_pct:.1f}%",
            details={"ug": ug, "pg": pg, "phd": phd, "total": total, "diff_pct": round(diff_pct, 2)},
        )

    return RuleResult(
        rule_name="student_count_math",
        passed=True,
        severity="info",
        message=f"Student count check passed: {computed} ≈ {total} (diff {diff_pct:.1f}%)",
        details={"computed_sum": computed, "total": total, "diff_pct": round(diff_pct, 2)},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2: Placement Logic
# ─────────────────────────────────────────────────────────────────────────────
def rule_placement_logic(data: dict) -> RuleResult:
    """Check: placed ≤ total students; placement rate is consistent."""
    stats = data.get("student_statistics", [])
    vals = {s["category"]: s["value"] for s in stats if isinstance(s, dict)}

    total  = _extract_int(vals, "Total students")
    placed = _extract_int(vals, "Total students placed")
    rate   = _extract_float(vals, "Placement rate")

    errors = []

    if placed > total and total > 0:
        errors.append(f"placed({placed}) > total({total}) — impossible")

    if rate > 0 and total > 0:
        expected_placed = round(total * rate / 100)
        # UG 4-year placement rate, so check against UG count approx
        ug = _extract_int(vals, "Undergraduate")
        if ug > 0:
            actual_rate = round(placed / ug * 100) if ug else 0
            if abs(actual_rate - rate) > 15:  # 15% tolerance
                errors.append(
                    f"Placement rate {rate}% inconsistent: placed/UG = {placed}/{ug} = {actual_rate}%"
                )

    if errors:
        return RuleResult(
            rule_name="placement_logic",
            passed=False,
            severity="error",
            message="; ".join(errors),
            details={"total": total, "placed": placed, "stated_rate": rate},
        )

    return RuleResult(
        rule_name="placement_logic",
        passed=True,
        severity="info",
        message="Placement logic check passed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3: Ranking Consistency
# ─────────────────────────────────────────────────────────────────────────────
def rule_ranking_consistency(data: dict) -> RuleResult:
    """Check: NIRF rank in valid range (1–300); no contradictions."""
    ranking = data.get("global_ranking", "")
    details_list = data.get("additional_details", [])
    details_map = {d["category"]: d["value"] for d in details_list if isinstance(d, dict)}

    import re
    nirf_match = re.search(r"NIRF\s+(\d+)", ranking)
    warnings = []

    if nirf_match:
        nirf_rank = int(nirf_match.group(1))
        if nirf_rank < 1 or nirf_rank > 300:
            warnings.append(f"NIRF rank {nirf_rank} outside valid range 1–300")

        # Cross-check with additional_details
        nirf_detail = details_map.get("NIRF Ranking (Engineering) 2024", "")
        if nirf_detail and nirf_detail.isdigit():
            if int(nirf_detail) != nirf_rank:
                warnings.append(
                    f"NIRF mismatch: global_ranking says {nirf_rank}, "
                    f"additional_details says {nirf_detail}"
                )

    if warnings:
        return RuleResult(
            rule_name="ranking_consistency",
            passed=False,
            severity="warning",
            message="; ".join(warnings),
        )

    return RuleResult(
        rule_name="ranking_consistency",
        passed=True,
        severity="info",
        message="Ranking consistency check passed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4: Fee Sanity
# ─────────────────────────────────────────────────────────────────────────────
def rule_fee_sanity(data: dict) -> RuleResult:
    """Check: min ≤ max for all fee tiers."""
    fees = data.get("fees", {})
    errors = []

    for tier in ("ug", "pg", "phd"):
        fmin = fees.get(f"{tier}_yearly_min", 0)
        fmax = fees.get(f"{tier}_yearly_max", 0)
        if fmin < 0 or fmax < 0:
            errors.append(f"{tier.upper()} fees negative: min={fmin}, max={fmax}")
        if fmin > fmax and fmax > 0:
            errors.append(f"{tier.upper()} min({fmin}) > max({fmax})")

    if errors:
        return RuleResult(
            rule_name="fee_sanity",
            passed=False,
            severity="error",
            message="; ".join(errors),
        )

    return RuleResult(
        rule_name="fee_sanity",
        passed=True,
        severity="info",
        message="Fee sanity check passed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 5: Gender Ratio
# ─────────────────────────────────────────────────────────────────────────────
def rule_gender_ratio(data: dict) -> RuleResult:
    """Check: male% + female% = 100."""
    ratio = data.get("student_gender_ratio", {})
    male = ratio.get("male_percentage", 0)
    female = ratio.get("female_percentage", 0)

    if male + female != 100:
        return RuleResult(
            rule_name="gender_ratio",
            passed=False,
            severity="error",
            message=f"Male({male}%) + Female({female}%) = {male + female}% ≠ 100%",
        )

    if male < 0 or female < 0 or male > 100 or female > 100:
        return RuleResult(
            rule_name="gender_ratio",
            passed=False,
            severity="error",
            message=f"Impossible percentages: male={male}%, female={female}%",
        )

    return RuleResult(
        rule_name="gender_ratio",
        passed=True,
        severity="info",
        message="Gender ratio check passed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6: Department / Programme Cross-check
# ─────────────────────────────────────────────────────────────────────────────
def rule_dept_program_crosscheck(data: dict) -> RuleResult:
    """Check: at least some programmes should relate to departments."""
    departments = set(d.lower() for d in data.get("departments", []))
    all_programs = (
        data.get("ug_programs", [])
        + data.get("pg_programs", [])
        + data.get("phd_programs", [])
    )

    if not departments:
        return RuleResult(
            rule_name="dept_program_crosscheck",
            passed=False,
            severity="warning",
            message="No departments listed — cannot cross-check",
        )

    if not all_programs:
        return RuleResult(
            rule_name="dept_program_crosscheck",
            passed=False,
            severity="warning",
            message="No programmes listed — cannot cross-check",
        )

    # Check if at least 30% of department names appear in some programme name
    matches = 0
    for dept in departments:
        dept_words = set(dept.split())
        for prog in all_programs:
            prog_lower = prog.lower()
            # If at least 2 words match, count as related
            if len(dept_words & set(prog_lower.split())) >= 2:
                matches += 1
                break

    match_rate = matches / len(departments) if departments else 0

    if match_rate < 0.3:
        return RuleResult(
            rule_name="dept_program_crosscheck",
            passed=False,
            severity="warning",
            message=f"Only {match_rate:.0%} of departments match programme names",
            details={"match_rate": round(match_rate, 3), "dept_count": len(departments)},
        )

    return RuleResult(
        rule_name="dept_program_crosscheck",
        passed=True,
        severity="info",
        message=f"Department/programme cross-check passed ({match_rate:.0%} match)",
        details={"match_rate": round(match_rate, 3)},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 7: Required Fields Present
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_FIELDS = [
    "college_name", "location", "country", "about", "departments",
    "ug_programs", "global_ranking", "fees", "sources",
]

def rule_required_fields(data: dict) -> RuleResult:
    """Check: all required fields are present and non-empty."""
    missing = []
    for fld in REQUIRED_FIELDS:
        val = data.get(fld)
        if val is None or val == "" or val == [] or val == {}:
            missing.append(fld)

    if missing:
        return RuleResult(
            rule_name="required_fields",
            passed=False,
            severity="error",
            message=f"Missing required fields: {', '.join(missing)}",
            details={"missing": missing},
        )

    return RuleResult(
        rule_name="required_fields",
        passed=True,
        severity="info",
        message="All required fields present",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _extract_int(vals: dict, keyword: str) -> int:
    """Find a dict key containing *keyword* and return its int value."""
    for k, v in vals.items():
        if keyword.lower() in k.lower():
            if isinstance(v, int):
                return v
            if isinstance(v, str):
                digits = "".join(c for c in v if c.isdigit())
                return int(digits) if digits else 0
    return 0


def _extract_float(vals: dict, keyword: str) -> float:
    """Find a dict key containing *keyword* and return its float value."""
    for k, v in vals.items():
        if keyword.lower() in k.lower():
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                import re
                m = re.search(r"[\d.]+", v)
                return float(m.group()) if m else 0.0
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# All rules in execution order
# ─────────────────────────────────────────────────────────────────────────────
ALL_RULES = [
    rule_required_fields,
    rule_student_count_math,
    rule_placement_logic,
    rule_ranking_consistency,
    rule_fee_sanity,
    rule_gender_ratio,
    rule_dept_program_crosscheck,
]
