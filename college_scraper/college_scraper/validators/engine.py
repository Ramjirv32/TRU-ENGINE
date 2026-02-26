"""
validators/engine.py – Layer 3: Validation Engine
===================================================
Runs ALL validation rules on a scraped college item and produces
a comprehensive validation report with:

  • Per-rule pass/fail status
  • Overall validation score (0.0 – 1.0)
  • Error / warning counts
  • Human-readable summary

This is the **MOST IMPORTANT** component for achieving 95% data accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from college_scraper.validators.rules import ALL_RULES, RuleResult


@dataclass
class ValidationReport:
    """Full validation report for one college."""
    college_name: str = ""
    total_rules: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    error_count: int = 0
    warning_count: int = 0
    validation_score: float = 0.0       # 0.0 – 1.0
    rule_results: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "college_name": self.college_name,
            "total_rules": self.total_rules,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "validation_score": self.validation_score,
            "rule_results": self.rule_results,
            "summary": self.summary,
        }


class ValidationEngine:
    """
    Run all validation rules on a college data dict.

    Usage::

        engine = ValidationEngine()
        report = engine.validate(item_dict)
        print(report.validation_score)   # 0.857
        print(report.summary)            # "5/7 rules passed ..."
    """

    def __init__(self, rules=None):
        self.rules = rules or ALL_RULES

    def validate(self, data: dict) -> ValidationReport:
        """Run all rules and produce a report."""
        report = ValidationReport()
        report.college_name = data.get("college_name", "Unknown")
        report.total_rules = len(self.rules)

        for rule_fn in self.rules:
            try:
                result: RuleResult = rule_fn(data)
            except Exception as exc:
                result = RuleResult(
                    rule_name=rule_fn.__name__,
                    passed=False,
                    severity="error",
                    message=f"Rule crashed: {exc}",
                )

            report.rule_results.append(result.to_dict())

            if result.passed:
                report.rules_passed += 1
            else:
                report.rules_failed += 1
                if result.severity == "error":
                    report.error_count += 1
                elif result.severity == "warning":
                    report.warning_count += 1

        # ── Compute validation score ──────────────────────────────────
        if report.total_rules > 0:
            # Errors penalise more than warnings
            penalty = (report.error_count * 0.15) + (report.warning_count * 0.05)
            raw = report.rules_passed / report.total_rules
            report.validation_score = round(max(0.0, min(1.0, raw - penalty)), 3)
        else:
            report.validation_score = 0.0

        # ── Summary ───────────────────────────────────────────────────
        report.summary = (
            f"{report.rules_passed}/{report.total_rules} rules passed | "
            f"{report.error_count} errors, {report.warning_count} warnings | "
            f"score: {report.validation_score}"
        )

        return report

    def validate_batch(self, items: list[dict]) -> list[ValidationReport]:
        """Validate a list of items, return reports."""
        return [self.validate(item) for item in items]
