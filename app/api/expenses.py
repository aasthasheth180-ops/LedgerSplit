
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseResponse
from app.services.expense_service import (
    create_expense,
    get_group_expenses,
    get_expense_details,
)

router = APIRouter(
    prefix="/groups",
    tags=["Expenses"],
)


@router.post(
    "/{group_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group_expense(
    group_id: int,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense, splits = create_expense(
        db=db,
        group_id=group_id,
        payer_id=current_user.id,
        payload=payload,
    )

    return ExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        paid_by=expense.paid_by,
        description=expense.description,
        amount=expense.amount,
        created_at=expense.created_at,
        splits=splits,
    )




@router.get(
    "/{group_id}/expenses",
    response_model=list[ExpenseResponse],
    status_code=status.HTTP_200_OK,
)
def list_group_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = get_group_expenses(
        db=db,
        group_id=group_id,
        requester_id=current_user.id,
    )

    return [
        ExpenseResponse(
            id=expense.id,
            group_id=expense.group_id,
            paid_by=expense.paid_by,
            description=expense.description,
            amount=expense.amount,
            created_at=expense.created_at,
            splits=splits,
        )
        for expense, splits in results
    ]


@router.get(
    "/{group_id}/expenses/{expense_id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
)
def retrieve_expense_details(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense, splits = get_expense_details(
        db=db,
        group_id=group_id,
        expense_id=expense_id,
        requester_id=current_user.id,
    )

    return ExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        paid_by=expense.paid_by,
        description=expense.description,
        amount=expense.amount,
        created_at=expense.created_at,
        splits=splits,
    )
