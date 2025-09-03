from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TableDataclass(BaseModel):
    title: str
    request: Any
    headers: List[str]
    table_rows: Any
    view_url: str
    view_record_url: str
    add_url: str
    delete_url: str

class ViewRecordDataclass(BaseModel):
    request: Any
    record: Dict
    view_url: str
    edit_url: str
    users: Optional[List[Any]] = None
    system_choices: Optional[List[Any]] = None