
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.services.ledger_service import calculate_group_balances
from app.services.settlement_service import simplify_debts


router = APIRouter(tags=["Settlements"])


@router.get("/groups/{group_id}/settlements")
def get_group_settlements(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check whether the group exists.
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Group not found",
        )

    # Check whether the user belongs to this group.
    membership = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    # Calculate net balances.
    balances = calculate_group_balances(db, group_id)

    # Generate settlement suggestions.
    settlements = simplify_debts(balances)

    return {
        "group_id": group_id,
        "settlements": [
            {
                "from_user_id": item["from_user_id"],
                "to_user_id": item["to_user_id"],
                "amount": str(item["amount"]),
            }
            for item in settlements
        ],
    }
