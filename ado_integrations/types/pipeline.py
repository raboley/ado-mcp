from pydantic import BaseModel

class Pipeline(BaseModel):
    id: int
    name: str
    folder: str | None = None

class PipelineParameter(BaseModel):
    name: str
    type: str
    defaultValue: str | None = None
    required: bool

class PipelineDefinition(BaseModel):
    id: int
    name: str
    folder: str | None = None
    parameters: list[PipelineParameter]
