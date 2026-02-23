"""
Format validator — checks that the LLM output matches the diary spec.
"""

from __future__ import annotations

import re
import logging
from uuid import UUID

from app.dto.validation import FormatValidationDTO

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(r"^<b>\d{4}\.\d{2}\.\d{2}(\s+\d{2}:\d{2})?\s*-\s*Дневник</b>")
_GRATITUDE_RE = re.compile(r"○\s+.+")
_CODE_BLOCK_RE = re.compile(r"```(?:\w+)?\s*(.*?)```", re.DOTALL)


def validate_format(text: str, request_id: UUID) -> FormatValidationDTO:
    """
    Validate the LLM output against diary format rules (HTML).
    """
    checks = {}

    # 1. No triple backticks (clean text mode)
    checks["no_backticks"] = "```" not in text

    # 2. Header line matches format <b>...</b>
    first_line = text.strip().split("\n")[0]
    checks["header_ok"] = bool(_HEADER_RE.match(first_line))

    # 3. Has bold section headers <b>...</b>
    checks["has_bold_sections"] = "<b>" in text and "</b>" in text

    # 4. Gratitude section uses ○ (if present)
    if "Благодарю" in text or "благодарю" in text.lower():
        checks["gratitude_section_ok"] = bool(_GRATITUDE_RE.search(text))
    else:
        checks["gratitude_section_ok"] = True

    # 5. General hygiene
    checks["no_links"] = "[" not in text
    checks["no_long_dash"] = "—" not in text and "–" not in text
    checks["no_stars"] = "*" not in text

    is_valid = all(checks.values())
    logger.info("Validation (HTML) for %s: valid=%s checks=%s", request_id, is_valid, checks)

    return FormatValidationDTO(
        request_id=request_id,
        is_valid=is_valid,
        checks=checks,
    )


def is_clarification_question(text: str) -> bool:
    """Heuristic: if LLM asks for the date instead of generating a diary entry."""
    return "<b>" not in text and ("дату" in text.lower() or "yyyy" in text.lower())


def extract_code_block(text: str) -> str:
    """No longer used in HTML mode, returns text as-is."""
    return text.strip()
