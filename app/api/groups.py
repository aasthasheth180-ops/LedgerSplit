
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupMemberAdd,
    GroupMemberResponse,
)
from app.services.group_service import (
    create_group,
    get_user_groups,
    add_group_member,
    get_group_members,
)

router = APIRouter(
    prefix="/groups",
    tags=["Groups"],
)


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_group(
        db=db,
        name=payload.name,
        creator_id=current_user.id,
    )



@router.get(
    "",
    response_model=list[GroupResponse],
    status_code=status.HTTP_200_OK,
)
def list_my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_groups(
        db=db,
        user_id=current_user.id,
    )


@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member_to_group(
    group_id: int,
    payload: GroupMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return add_group_member(
        db=db,
        group_id=group_id,
        user_id=payload.user_id,
        requester_id=current_user.id,
    )


@router.get(
    "/{group_id}/members",
    response_model=list[GroupMemberResponse],
    status_code=status.HTTP_200_OK,
)
def list_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_group_members(
        db=db,
        group_id=group_id,
        requester_id=current_user.id,
    )
