from pydantic import BaseModel

class BuildDefinition(BaseModel):
    id: int
    name: str
