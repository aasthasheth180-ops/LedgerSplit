
from decimal import Decimal


def simplify_debts(
    balances: dict[int, Decimal],
) -> list[dict]:
    """
    Calculate suggested payments between group members.

    Positive balance: user should receive money.
    Negative balance: user owes money.

    This function suggests payments but does not
    record or execute actual transactions.
    """

    # Verify that the ledger is balanced.
    total = sum(balances.values(), Decimal("0.00"))

    if total != Decimal("0.00"):
        raise ValueError("Group balances must sum to zero")

    # Members who should receive money.
    creditors = [
        [user_id, amount]
        for user_id, amount in sorted(balances.items())
        if amount > 0
    ]

    # Members who owe money.
    debtors = [
        [user_id, -amount]
        for user_id, amount in sorted(balances.items())
        if amount < 0
    ]

    settlements = []

    debtor_index = 0
    creditor_index = 0

    # Match debtors with creditors.
    while (
        debtor_index < len(debtors)
        and creditor_index < len(creditors)
    ):
        debtor_id, amount_owed = debtors[debtor_index]
        creditor_id, amount_receivable = creditors[creditor_index]

        # Choose the smaller remaining amount.
        payment = min(amount_owed, amount_receivable)

        settlements.append({
            "from_user_id": debtor_id,
            "to_user_id": creditor_id,
            "amount": payment,
        })

        # Update outstanding balances.
        debtors[debtor_index][1] -= payment
        creditors[creditor_index][1] -= payment

        # Advance when a person's balance is settled.
        if debtors[debtor_index][1] == 0:
            debtor_index += 1

        if creditors[creditor_index][1] == 0:
            creditor_index += 1

    return settlements
