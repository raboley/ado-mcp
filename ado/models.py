from pydantic import BaseModel

class Project(BaseModel):
    """
    Represents an Azure DevOps project.
    """
    id: str
    name: str
    description: str | None = None
    url: str
    state: str
    revision: int
    visibility: str
    lastUpdateTime: str