from pydantic import BaseModel
from typing import List, Optional, Dict

class ColumnStats(BaseModel):
    name: str
    type: str
    null_percent: float
    distinct_count: Optional[int]
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None

class TableProfile(BaseModel):
    table_name: str
    columns: List[ColumnStats]
    sample_values: Dict[str, List[str]]

class EnrichmentInput(BaseModel):
    table: TableProfile
    domain_hint: Optional[str] = None