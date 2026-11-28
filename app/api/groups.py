from fastapi import (
    APIRouter,
    Depends,
    Header,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupUpdate,
)

from app.services.group_service import (
    create_group,
    get_user_groups,
    add_group_member,
    get_group_members,
    remove_group_member,
    update_group,
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
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=1, max_length=128,
    ),
):
    return create_group(
        db=db,
        name=payload.name,
        creator_id=current_user.id,
        description=payload.description,
        category=payload.category,
        custom_category=payload.custom_category,
        currency=payload.currency,
        default_split=payload.default_split,
        color=payload.color,
        member_emails=payload.member_emails,
        idempotency_key=idempotency_key,
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
        email=payload.email,
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


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_group_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    remove_group_member(
        db=db,
        group_id=group_id,
        user_id=user_id,
        requester_id=current_user.id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
@router.patch(
    "/{group_id}",
    response_model=GroupResponse,
    status_code=status.HTTP_200_OK,
)
def edit_group(
    group_id: int,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_group(
        db=db,
        group_id=group_id,
        requester_id=current_user.id,
        payload=payload,
    )

from app.services.lifecycle_service import (
    delete_group,
    archive_group,
)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_existing_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_group(db, group_id, current_user.id)

    return Response(status_code=204)


@router.post(
    "/{group_id}/archive",
    response_model=GroupResponse,
)
def archive_existing_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return archive_group(db, group_id, current_user.id)