
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import (
    create_payment,
    confirm_payment,
    reject_payment,
    list_group_payments,
)


router = APIRouter(
    prefix="/groups",
    tags=["Payments"],
)


@router.post(
    "/{group_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)

def report_group_payment(
    group_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
    ),
):
    payment = create_payment(
        db=db,
        group_id=group_id,
        sender_id=current_user.id,
        payload=payload,
        idempotency_key=idempotency_key,
    )

    return payment



@router.post(
    "/{group_id}/payments/{payment_id}/confirm",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
)
def confirm_group_payment(
    group_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = confirm_payment(
        db=db,
        group_id=group_id,
        payment_id=payment_id,
        recipient_id=current_user.id,
    )

    return payment


@router.post(
    "/{group_id}/payments/{payment_id}/reject",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
)
def reject_group_payment(
    group_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = reject_payment(
        db=db,
        group_id=group_id,
        payment_id=payment_id,
        recipient_id=current_user.id,
    )

    return payment



@router.get(
    "/{group_id}/payments",
    response_model=list[PaymentResponse],
    status_code=status.HTTP_200_OK,
)
def get_group_payment_history(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payments = list_group_payments(
        db=db,
        group_id=group_id,
        user_id=current_user.id,
    )

    return payments
