
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.services.ledger_service import calculate_group_balances


router = APIRouter(
    prefix="/groups",
    tags=["Balances"],
)


@router.get("/{group_id}/balances")
def get_group_balances(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check whether the group exists.
    group = db.scalar(
        select(Group).where(Group.id == group_id)
    )

    if group is None or group.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # Only group members may view balances.
    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # Calculate balances using our existing service.
    balances = calculate_group_balances(
        db=db,
        group_id=group_id,
    )

    return {
        "group_id": group_id,
        "balances": [
            {
                "user_id": user_id,
                "net_balance": str(amount),
            }
            for user_id, amount in sorted(balances.items())
        ],
    }
