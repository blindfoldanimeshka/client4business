from pydantic import BaseModel, Field


class ApproveIn(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class CancelIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
