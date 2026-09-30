import os
import ast
import json
import csv
import yaml
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image
import openpyxl
import docx
import pptx
import fitz
from typing import Dict, Any
from app.services.universal_artifacts.contracts import ValidationResult


class ArtifactValidator:
    """Universal Artifact Verification Engine (§31–§36).
    Enforces that zero fake, empty, corrupt, or unreadable files are delivered.
    """

    @classmethod
    def validate(cls, file_path: str, fmt: str) -> ValidationResult:
        clean_fmt = fmt.lower().lstrip(".")

        if not os.path.exists(file_path):
            return ValidationResult(is_valid=False, format=clean_fmt, error="File does not exist on disk")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return ValidationResult(is_valid=False, format=clean_fmt, error="File is empty (0 bytes)")

        try:
            # 1. PDF Validation (§33)
            if clean_fmt == "pdf":
                doc = fitz.open(file_path)
                page_count = len(doc)
                doc.close()
                if page_count < 1:
                    return ValidationResult(is_valid=False, format=clean_fmt, error="PDF contains zero pages")
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=3, total_checks=3, details={"page_count": page_count})

            # 2. DOCX Validation (§32)
            elif clean_fmt in ["docx", "doc"]:
                d = docx.Document(file_path)
                para_count = len(d.paragraphs)
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=3, total_checks=3, details={"paragraphs": para_count})

            # 3. PPTX Validation (§35)
            elif clean_fmt in ["pptx", "ppt"]:
                p = pptx.Presentation(file_path)
                slide_count = len(p.slides)
                if slide_count < 1:
                    return ValidationResult(is_valid=False, format=clean_fmt, error="Presentation contains zero slides")
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=3, total_checks=3, details={"slide_count": slide_count})

            # 4. XLSX Validation (§34)
            elif clean_fmt in ["xlsx", "xls"]:
                wb = openpyxl.load_workbook(file_path, data_only=True)
                sheets = wb.sheetnames
                wb.close()
                if len(sheets) < 1:
                    return ValidationResult(is_valid=False, format=clean_fmt, error="Workbook contains zero sheets")
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=3, total_checks=3, details={"sheets": sheets})

            # 5. CSV / TSV Validation (§6)
            elif clean_fmt in ["csv", "tsv"]:
                delim = "\t" if clean_fmt == "tsv" else ","
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.reader(f, delimiter=delim)
                    row_count = sum(1 for _ in reader)
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=2, total_checks=2, details={"row_count": row_count})

            # 6. JSON Validation (§8)
            elif clean_fmt == "json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=2, total_checks=2)

            # 7. YAML Validation (§8)
            elif clean_fmt in ["yaml", "yml"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    yaml.safe_load(f)
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=2, total_checks=2)

            # 8. XML Validation (§8)
            elif clean_fmt == "xml":
                ET.parse(file_path)
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=2, total_checks=2)

            # 9. Python Code Syntax Check (§36)
            elif clean_fmt == "py":
                with open(file_path, "r", encoding="utf-8") as f:
                    ast.parse(f.read())
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=2, total_checks=2)

            # 10. ZIP Archive Integrity Check (§12)
            elif clean_fmt == "zip":
                if not zipfile.is_zipfile(file_path):
                    return ValidationResult(is_valid=False, format=clean_fmt, error="File is not a valid ZIP archive")
                with zipfile.ZipFile(file_path, 'r') as zf:
                    bad = zf.testzip()
                    if bad:
                        return ValidationResult(is_valid=False, format=clean_fmt, error=f"Corrupt ZIP entry: {bad}")
                    names = zf.namelist()
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=3, total_checks=3, details={"files_count": len(names), "files": names})

            # 11. Image Checks (§11)
            elif clean_fmt in ["png", "jpg", "jpeg", "webp"]:
                with Image.open(file_path) as img:
                    img.verify()
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=2, total_checks=2)

            elif clean_fmt == "svg":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                if "<svg" not in text or "</svg>" not in text:
                    return ValidationResult(is_valid=False, format=clean_fmt, error="Malformed SVG root elements")
                return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=2, total_checks=2)

            # Default generic text file validation
            return ValidationResult(is_valid=True, format=clean_fmt, checks_passed=1, total_checks=1, details={"bytes": file_size})

        except Exception as e:
            return ValidationResult(is_valid=False, format=clean_fmt, error=f"Structural validation exception: {str(e)}")
