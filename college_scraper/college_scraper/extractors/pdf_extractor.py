"""
extractors/pdf_extractor.py – 🔴 Level 3 PDF Parser
=====================================================
Parse placement reports and annual reports from PDF files.

Uses **pdfplumber** to extract tables and text from college PDFs.

Target data:
  • Placement statistics (total placed, avg CTC, highest CTC)
  • Student enrollment numbers (UG, PG, PhD breakdowns)
  • Faculty count

These are Level-3 (dynamic/risky) data points that change every year
and MUST come from official PDF documents — never from blog sites.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


@dataclass
class PDFExtractionResult:
    """Result from parsing a college PDF (placement report / annual report)."""
    source_type: str = ""              # "placement_report" | "annual_report"
    source_url: str = ""
    total_placed: Optional[int] = None
    placement_rate: Optional[float] = None
    avg_ctc: Optional[str] = None
    highest_ctc: Optional[str] = None
    lowest_ctc: Optional[str] = None
    total_students: Optional[int] = None
    ug_students: Optional[int] = None
    pg_students: Optional[int] = None
    phd_students: Optional[int] = None
    faculty_count: Optional[int] = None
    tables_found: int = 0
    pages_parsed: int = 0
    extraction_confidence: float = 0.0
    errors: list[str] = field(default_factory=list)
    raw_text_preview: str = ""         # first 500 chars for debugging

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "source_url": self.source_url,
            "total_placed": self.total_placed,
            "placement_rate": self.placement_rate,
            "avg_ctc": self.avg_ctc,
            "highest_ctc": self.highest_ctc,
            "lowest_ctc": self.lowest_ctc,
            "total_students": self.total_students,
            "ug_students": self.ug_students,
            "pg_students": self.pg_students,
            "phd_students": self.phd_students,
            "faculty_count": self.faculty_count,
            "tables_found": self.tables_found,
            "pages_parsed": self.pages_parsed,
            "extraction_confidence": self.extraction_confidence,
            "errors": self.errors,
        }


class PDFExtractor:
    """
    Parse college PDF files (placement reports, annual reports) using pdfplumber.

    Extraction strategy:
    1. Extract all text from each page
    2. Search for known patterns (regex) for placement stats
    3. Extract tables and look for enrollment / placement columns
    4. Compute confidence based on how many fields were found
    """

    # Regex patterns for common placement report fields
    PATTERNS = {
        "total_placed": [
            r"total\s+(?:students?\s+)?placed\s*[:\-–]?\s*(\d[\d,]*)",
            r"(\d[\d,]*)\s+students?\s+placed",
            r"placed\s*[:\-–]?\s*(\d[\d,]*)",
        ],
        "placement_rate": [
            r"placement\s+(?:rate|percentage)\s*[:\-–]?\s*([\d.]+)\s*%",
            r"([\d.]+)\s*%\s*placement",
        ],
        "avg_ctc": [
            r"average\s+(?:CTC|package|salary)\s*[:\-–]?\s*(?:₹|INR|Rs\.?)?\s*([\d.]+\s*(?:LPA|lakh|Cr|crore))",
            r"avg\.?\s+CTC\s*[:\-–]?\s*(?:₹|INR)?\s*([\d.]+\s*LPA)",
        ],
        "highest_ctc": [
            r"highest\s+(?:CTC|package|salary)\s*[:\-–]?\s*(?:₹|INR|Rs\.?)?\s*([\d.]+\s*(?:LPA|lakh|Cr|crore))",
            r"max(?:imum)?\s+(?:CTC|package)\s*[:\-–]?\s*(?:₹|INR)?\s*([\d.]+\s*(?:LPA|Cr))",
        ],
        "lowest_ctc": [
            r"lowest\s+(?:CTC|package|salary)\s*[:\-–]?\s*(?:₹|INR|Rs\.?)?\s*([\d.]+\s*(?:LPA|lakh))",
            r"min(?:imum)?\s+(?:CTC|package)\s*[:\-–]?\s*(?:₹|INR)?\s*([\d.]+\s*LPA)",
        ],
        "total_students": [
            r"total\s+(?:student\s+)?(?:strength|enrollment)\s*[:\-–]?\s*(\d[\d,]*)",
            r"total\s+students\s*[:\-–]?\s*(\d[\d,]*)",
        ],
        "faculty_count": [
            r"(?:total\s+)?faculty\s*[:\-–]?\s*(\d[\d,]*)",
            r"(\d[\d,]*)\s+faculty\s+members?",
        ],
    }

    def extract_from_bytes(self, pdf_bytes: bytes,
                           source_type: str = "placement_report",
                           source_url: str = "") -> PDFExtractionResult:
        """Parse a PDF from raw bytes."""
        if not HAS_PDFPLUMBER:
            return PDFExtractionResult(
                errors=["pdfplumber not installed"],
                source_type=source_type,
                source_url=source_url,
            )

        result = PDFExtractionResult(source_type=source_type, source_url=source_url)
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
            result.pages_parsed = len(pdf.pages)
            full_text = ""

            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"

                # Count tables
                tables = page.extract_tables()
                result.tables_found += len(tables)

            pdf.close()
            result.raw_text_preview = full_text[:500]
            found = 0

            # ── Pattern matching ──────────────────────────────────────
            for field_name, patterns in self.PATTERNS.items():
                for pattern in patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        raw_val = match.group(1).replace(",", "")
                        if field_name in ("avg_ctc", "highest_ctc", "lowest_ctc"):
                            setattr(result, field_name, f"₹{match.group(1)}")
                        elif field_name == "placement_rate":
                            result.placement_rate = float(raw_val)
                        else:
                            setattr(result, field_name, int(raw_val))
                        found += 1
                        break

            # ── Confidence ────────────────────────────────────────────
            total_fields = len(self.PATTERNS)
            result.extraction_confidence = round(found / total_fields, 3) if total_fields else 0.0

        except Exception as exc:
            result.errors.append(f"PDF parse error: {exc}")

        return result

    def extract_from_file(self, filepath: str,
                          source_type: str = "placement_report") -> PDFExtractionResult:
        """Parse a PDF from a file path."""
        try:
            with open(filepath, "rb") as f:
                return self.extract_from_bytes(
                    f.read(), source_type=source_type, source_url=f"file://{filepath}"
                )
        except FileNotFoundError:
            return PDFExtractionResult(
                errors=[f"File not found: {filepath}"],
                source_type=source_type,
            )
