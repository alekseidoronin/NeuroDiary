"""
DTO for diary format validation results.
"""

from __future__ import annotations

from typing import Dict
from uuid import UUID

from pydantic import BaseModel


class FormatValidationDTO(BaseModel):
    request_id: UUID
    is_valid: bool = False
    checks: Dict[str, bool] = {}
    repair_attempted: bool = False
    repaired_text: str = ""
