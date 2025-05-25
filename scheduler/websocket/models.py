from typing import Optional

from pydantic import BaseModel

class GitWsMessage(BaseModel):
    service: str
    message: str
    action: str
    version: Optional[str] = None
    service_name: Optional[str] = None

    def __str__(self) -> str:
        return f"GitWsMessage(service={self.service}, message={self.message}, action={self.action}, version={self.version})"

class ProxyResponse(BaseModel):
    is_error: bool
    msg: str