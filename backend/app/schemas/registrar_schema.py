from typing import Optional
from pydantic import BaseModel

# Phase 0 placeholder — Student 3: Registrar
# Collection: performance_logs


class RegistrarActionBase(BaseModel):
    application_id: str
    action: Optional[str] = None
    performed_by: Optional[str] = None


class RegistrarActionCreate(RegistrarActionBase):
    pass


class RegistrarActionResponse(RegistrarActionBase):
    action_id: str
