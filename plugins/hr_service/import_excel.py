"""
Excel import for HR employees: parse sheets DДЖ and Инфоком, validate, merge by personal_number.
SPEC_HR_SERVICE sections 3–4.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def import_employees_from_file(file_path: str) -> Any:
    """
    Parse .xlsx/.xls file (sheets «ДДЖ» and «Инфоком»), check duplicate personal_number,
    merge by personal_number, insert only new employees. Returns dict with added_count, added_names, errors
    or "Error: ..." string on fatal error (e.g. duplicate in file).
    """
    # Stub: full implementation in Task 4
    return "Error: Excel import not implemented yet. Use API or admin import."
