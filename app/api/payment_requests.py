from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User

from app.schemas.payment_request import (
    PaymentRequestCreate,
    PaymentRequestResponse,
)

from app.services.payment_request_service import (
    create_payment_request,
    list_payment_requests,
    cancel_payment_request,
)


router = APIRouter(
    prefix="/groups",
    tags=["Payment Requests"],
)


@router.post(
    "/{group_id}/payment-requests",
    response_model=PaymentRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group_payment_request(
    group_id: int,
    payload: PaymentRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
    ),
):
    return create_payment_request(
        db=db,
        group_id=group_id,
        requester_id=current_user.id,
        payload=payload,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/{group_id}/payment-requests",
    response_model=list[PaymentRequestResponse],
)
def get_group_payment_requests(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_payment_requests(
        db=db,
        group_id=group_id,
        user_id=current_user.id,
    )


@router.post(
    "/{group_id}/payment-requests/{request_id}/cancel",
    response_model=PaymentRequestResponse,
)
def cancel_group_payment_request(
    group_id: int,
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return cancel_payment_request(
        db=db,
        group_id=group_id,
        request_id=request_id,
        requester_id=current_user.id,
    )

from app.schemas.payment_request import PaymentRequestUpdate
from app.services.payment_request_service import update_payment_request

@router.patch("/{group_id}/payment-requests/{request_id}", response_model=PaymentRequestResponse)
def edit_payment_request(group_id: int, request_id: int, payload: PaymentRequestUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return update_payment_request(db, group_id, request_id, current_user.id, payload)
