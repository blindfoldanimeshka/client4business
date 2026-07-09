from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.approval_request import ApprovalStatus, SourceType


class ApprovalRequestCreate(BaseModel):
    sourceType: SourceType
    sourceId: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    reviewerUserIds: list[str] = Field(default_factory=list)

    @field_validator("reviewerUserIds")
    @classmethod
    def non_empty_ids(cls, v: list[str]) -> list[str]:
        if any(not item.strip() for item in v):
            raise ValueError("reviewerUserIds must not contain empty strings")
        return v


class ApprovalRequestOut(BaseModel):
    id: str
    workspaceId: str
    sourceType: SourceType
    sourceId: str
    title: str
    description: str | None
    reviewerUserIds: list[str]
    status: ApprovalStatus
    createdByUserId: str
    decidedByUserId: str | None
    decidedAt: datetime | None
    decisionNote: str | None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class ApprovalRequestList(BaseModel):
    items: list[ApprovalRequestOut]
    total: int
    limit: int
    offset: int
