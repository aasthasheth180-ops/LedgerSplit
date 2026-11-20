import pytest
from decimal import Decimal

from app.services.settlement_service import simplify_debts


def test_simple_debt_settlement():
    # Alice should receive $60.
    # Bob and Charlie each owe $30.
    balances = {
        1: Decimal("60.00"),
        2: Decimal("-30.00"),
        3: Decimal("-30.00"),
    }

    settlements = simplify_debts(balances)

    expected = [
        {
            "from_user_id": 2,
            "to_user_id": 1,
            "amount": Decimal("30.00"),
        },
        {
            "from_user_id": 3,
            "to_user_id": 1,
            "amount": Decimal("30.00"),
        },
    ]

    assert settlements == expected


def test_multiple_creditors_and_debtors():
    balances = {
        1: Decimal("70.00"),    # Alice receives
        2: Decimal("30.00"),    # Bob receives
        3: Decimal("-60.00"),   # Charlie owes
        4: Decimal("-40.00"),   # David owes
    }

    settlements = simplify_debts(balances)

    expected = [
        {
            "from_user_id": 3,
            "to_user_id": 1,
            "amount": Decimal("60.00"),
        },
        {
            "from_user_id": 4,
            "to_user_id": 1,
            "amount": Decimal("10.00"),
        },
        {
            "from_user_id": 4,
            "to_user_id": 2,
            "amount": Decimal("30.00"),
        },
    ]

    assert settlements == expected

    # Total suggested payments must equal total debt.
    total_transferred = sum(
        (item["amount"] for item in settlements),
        Decimal("0.00"),
    )

    assert total_transferred == Decimal("100.00")



def test_zero_balances_require_no_settlements():
    balances = {
        1: Decimal("0.00"),
        2: Decimal("0.00"),
        3: Decimal("0.00"),
    }

    settlements = simplify_debts(balances)

    assert settlements == []


def test_unbalanced_ledger_is_rejected():
    balances = {
        1: Decimal("100.00"),
        2: Decimal("-60.00"),
    }

    with pytest.raises(
        ValueError,
        match="Group balances must sum to zero",
    ):
        simplify_debts(balances)
