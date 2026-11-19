from typing import Literal
from pydantic import BaseModel, Field

class ReceiptIn(BaseModel):
    claim_id: int
    revision_no: int = Field(ge=1, le=9999)
    disputed: bool
    note: str = Field(default='', max_length=2000)
