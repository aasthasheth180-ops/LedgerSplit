
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GroupCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )


class GroupResponse(BaseModel):
    id: int
    name: str
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupMemberAdd(BaseModel):
    user_id: int = Field(gt=0)



class GroupMemberResponse(BaseModel):
    id: int
    group_id: int
    user_id: int
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)
