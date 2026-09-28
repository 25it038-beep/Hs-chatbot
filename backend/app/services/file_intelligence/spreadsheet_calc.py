"""
HSBot General Chat — Deterministic Spreadsheet Calculation Engine (V2)
Performs exact arithmetic (SUM, AVERAGE, MIN, MAX, COUNT, range filters, month ranges)
over parsed XLSX and CSV structured sheet data so the LLM never guesses numbers.
"""
import re
from typing import Optional, Any


MONTH_ORDER = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
MONTH_SHORT = [m[:3] for m in MONTH_ORDER]


def _col_index_to_letter(idx: int) -> str:
    """0-indexed column to Excel letter (0 -> A, 25 -> Z, 26 -> AA)."""
    result = ""
    n = idx + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _col_letter_to_index(letter: str) -> int:
    """Excel column letter to 0-indexed integer (A -> 0, D -> 3)."""
    letter = letter.upper().strip()
    result = 0
    for ch in letter:
        if "A" <= ch <= "Z":
            result = result * 26 + (ord(ch) - ord("A") + 1)
    return result - 1


def _to_number(val: Any) -> Optional[float]:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        if val != val:  # NaN check
            return None
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    # Remove currency symbols, commas, percent signs
    cleaned = re.sub(r"[$€£¥,\s]", "", s)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        return float(cleaned)
    except ValueError:
        return None


def _expand_month_range(query_lower: str) -> Optional[set[str]]:
    """Detect phrases like 'January through March', 'Jan to Mar', 'from January to March'."""
    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+(?:through|to|thru|-|–|until)\s+"
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
        query_lower,
    )
    if not m:
        return None
    m1, m2 = m.group(1)[:3], m.group(2)[:3]
    try:
        i1 = MONTH_SHORT.index(m1)
        i2 = MONTH_SHORT.index(m2)
    except ValueError:
        return None
    if i1 <= i2:
        indices = range(i1, i2 + 1)
    else:
        indices = list(range(i1, 12)) + list(range(0, i2 + 1))
    allowed = set()
    for idx in indices:
        allowed.add(MONTH_ORDER[idx])
        allowed.add(MONTH_SHORT[idx])
    return allowed


class SpreadsheetCalculator:
    """Executes deterministic calculations over structured spreadsheet sheets."""

    @staticmethod
    def analyze_and_calculate(
        filename: str,
        sheets: list[dict[str, Any]],
        query: str,
    ) -> Optional[str]:
        """
        Inspect user query against spreadsheet sheets.
        Computes exact SUM, AVG, MIN, MAX, COUNT for matching sheets, columns, cell ranges, or row filters,
        plus always provides pre-computed column totals per sheet when arithmetic intent is detected.
        """
        if not sheets:
            return None

        q_lower = (query or "").lower()
        calc_Lines: list[str] = []

        # 1. Check if a specific sheet is mentioned (e.g., "in Sheet2", "Revenue sheet")
        target_sheets = []
        for sh in sheets:
            sname = sh.get("sheet_name", "")
            if sname and sname.lower() in q_lower:
                target_sheets.append(sh)
        if not target_sheets:
            target_sheets = sheets

        # 2. Check if explicit cell range is mentioned (e.g., B2:F20 or D2:D10)
        range_match = re.search(r"\b([A-Za-z]{1,2})(\d+)\s*:\s*([A-Za-z]{1,2})(\d+)\b", query or "")

        # 3. Check if explicit column letter is mentioned (e.g., "column D", "col D")
        col_letter_match = re.search(r"\bcol(?:umn)?\s+([A-Za-z])\b", query or "", re.IGNORECASE)
        target_col_idx: Optional[int] = None
        if col_letter_match:
            target_col_idx = _col_letter_to_index(col_letter_match.group(1))

        # 4. Check month range filter (e.g., "January through March")
        month_filter = _expand_month_range(q_lower)

        for sh in target_sheets:
            sname = sh.get("sheet_name", "Sheet1")
            headers: list[str] = sh.get("headers") or []
            rows: list[list[Any]] = sh.get("rows") or []
            col_letters = [_col_index_to_letter(i) for i in range(max(len(headers), max((len(r) for r in rows), default=0)))]

            if not rows:
                continue

            # Explicit cell range calculation
            if range_match:
                c1 = _col_letter_to_index(range_match.group(1))
                r1 = int(range_match.group(2))
                c2 = _col_letter_to_index(range_match.group(3))
                r2 = int(range_match.group(4))
                vals = []
                coords = []
                for excel_row in range(min(r1, r2), max(r1, r2) + 1):
                    row_idx = excel_row - 2
                    if 0 <= row_idx < len(rows):
                        row_data = rows[row_idx]
                        for c_idx in range(min(c1, c2), max(c1, c2) + 1):
                            if 0 <= c_idx < len(row_data):
                                num = _to_number(row_data[c_idx])
                                if num is not None:
                                    vals.append(num)
                                    coords.append(f"{_col_index_to_letter(c_idx)}{excel_row}={num:g}")
                if vals:
                    total = sum(vals)
                    avg = total / len(vals)
                    rng_str = f"{range_match.group(1).upper()}{r1}:{range_match.group(3).upper()}{r2}"
                    calc_Lines.append(
                        f"[{filename} — {sname} sheet, cells {rng_str}]\n"
                        f"  • Values ({len(vals)} numeric cells): {', '.join(coords[:25])}\n"
                        f"  • EXACT SUM (Total): {total:,.4f}".rstrip("0").rstrip(".") + "\n"
                        f"  • EXACT AVERAGE: {avg:,.4f}".rstrip("0").rstrip(".") + "\n"
                        f"  • MIN: {min(vals):g} | MAX: {max(vals):g}"
                    )

            # Determine which columns match the query (by column letter or by column header name)
            matched_cols: list[int] = []
            if target_col_idx is not None and 0 <= target_col_idx < len(col_letters):
                matched_cols.append(target_col_idx)

            for c_idx, h in enumerate(headers):
                h_clean = str(h).strip().lower()
                if h_clean and (h_clean in q_lower or any(tok in q_lower for tok in re.findall(r"[a-z0-9]{3,}", h_clean))):
                    if c_idx not in matched_cols:
                        matched_cols.append(c_idx)

            # If no specific column matched, compute across all numeric columns
            if not matched_cols:
                matched_cols = list(range(len(col_letters)))

            for c_idx in matched_cols:
                col_let = col_letters[c_idx] if c_idx < len(col_letters) else _col_index_to_letter(c_idx)
                col_hdr = headers[c_idx] if c_idx < len(headers) else f"Column {col_let}"

                all_vals: list[tuple[int, str, float]] = []
                filtered_vals: list[tuple[int, str, float]] = []

                for r_idx, row_data in enumerate(rows):
                    excel_row = r_idx + 2
                    if c_idx >= len(row_data):
                        continue
                    num = _to_number(row_data[c_idx])
                    if num is None:
                        continue
                    row_label = str(row_data[0]).strip() if len(row_data) > 0 and row_data[0] is not None else f"Row {excel_row}"
                    all_vals.append((excel_row, row_label, num))

                    # Check if row matches month filter or query row keywords
                    row_text_lower = " ".join(str(x).lower() for x in row_data if x is not None)
                    if month_filter:
                        if any(re.search(rf"\b{re.escape(m)}\b", row_text_lower) for m in month_filter):
                            filtered_vals.append((excel_row, row_label, num))
                    else:
                        # Also check if specific row labels in row_data[0] are mentioned in query
                        lbl_lower = row_label.lower()
                        if lbl_lower and len(lbl_lower) >= 3 and lbl_lower in q_lower:
                            filtered_vals.append((excel_row, row_label, num))

                if not all_vals:
                    continue

                # Emit filtered calculation if a filter matched
                if filtered_vals:
                    f_nums = [v[2] for v in filtered_vals]
                    f_sum = sum(f_nums)
                    f_avg = f_sum / len(f_nums)
                    start_r = filtered_vals[0][0]
                    end_r = filtered_vals[-1][0]
                    breakdown = ", ".join(f"{col_let}{r} ({lbl}) = {val:g}" for r, lbl, val in filtered_vals[:20])
                    calc_Lines.append(
                        f"[{filename} — {sname} sheet, Column {col_let} ('{col_hdr}'), filtered rows {col_let}{start_r}:{col_let}{end_r}]\n"
                        f"  • Matching cells: {breakdown}\n"
                        f"  • EXACT FILTERED TOTAL (SUM): {f_sum:g} (formatted: {f_sum:,.2f})\n"
                        f"  • EXACT FILTERED AVERAGE: {f_avg:g} | COUNT: {len(f_nums)} | MIN: {min(f_nums):g} | MAX: {max(f_nums):g}"
                    )

                # Always emit full column calculation summary
                nums = [v[2] for v in all_vals]
                c_sum = sum(nums)
                c_avg = c_sum / len(nums)
                start_r = all_vals[0][0]
                end_r = all_vals[-1][0]
                breakdown = ", ".join(f"{col_let}{r} ({lbl})={val:g}" for r, lbl, val in all_vals[:15])
                if len(all_vals) > 15:
                    breakdown += f", ... ({len(all_vals)} total cells)"
                calc_Lines.append(
                    f"[{filename} — {sname} sheet, Column {col_let} ('{col_hdr}'), cells {col_let}{start_r}:{col_let}{end_r}]\n"
                    f"  • Cell values: {breakdown}\n"
                    f"  • EXACT COLUMN TOTAL (SUM): {c_sum:g} (formatted: {c_sum:,.2f})\n"
                    f"  • EXACT COLUMN AVERAGE: {c_avg:.4g} | COUNT: {len(nums)} | MIN: {min(nums):g} | MAX: {max(nums):g}"
                )

        if not calc_Lines:
            return None

        return (
            "=== VERIFIED SPREADSHEET ARITHMETIC & CELL CALCULATIONS ===\n"
            "Use these exact computed values and cell citations in your response (do not guess or approximate):\n\n"
            + "\n\n".join(calc_Lines)
        )
