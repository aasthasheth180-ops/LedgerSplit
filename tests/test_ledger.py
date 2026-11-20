
from decimal import Decimal

from app.models.user import User
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.services.ledger_service import calculate_group_balances


def test_calculate_group_balances(db_session):
    # Create three users.
    alice = User(
        full_name="Alice",
        email="ledger_alice@example.com",
        hashed_password="test_hash",
    )

    bob = User(
        full_name="Bob",
        email="ledger_bob@example.com",
        hashed_password="test_hash",
    )

    charlie = User(
        full_name="Charlie",
        email="ledger_charlie@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob, charlie])
    db_session.flush()

    # Create a group.
    group = Group(
        name="Ledger Test Group",
        created_by=alice.id,
    )

    db_session.add(group)
    db_session.flush()

    # Add all three users to the group.
    db_session.add_all([
        GroupMember(group_id=group.id, user_id=alice.id, role="owner"),
        GroupMember(group_id=group.id, user_id=bob.id, role="member"),
        GroupMember(group_id=group.id, user_id=charlie.id, role="member"),
    ])
    db_session.flush()

    # Alice pays $90 for groceries.
    expense = Expense(
        group_id=group.id,
        paid_by=alice.id,
        description="Groceries",
        amount=Decimal("90.00"),
    )

    db_session.add(expense)
    db_session.flush()

    # Each member owes $30.
    db_session.add_all([
        ExpenseSplit(
            expense_id=expense.id,
            user_id=alice.id,
            amount_owed=Decimal("30.00"),
        ),
        ExpenseSplit(
            expense_id=expense.id,
            user_id=bob.id,
            amount_owed=Decimal("30.00"),
        ),
        ExpenseSplit(
            expense_id=expense.id,
            user_id=charlie.id,
            amount_owed=Decimal("30.00"),
        ),
    ])
    db_session.flush()

    # Calculate balances.
    balances = calculate_group_balances(
        db=db_session,
        group_id=group.id,
    )

    # Alice should receive $60.
    assert balances[alice.id] == Decimal("60.00")

    # Bob and Charlie each owe $30.
    assert balances[bob.id] == Decimal("-30.00")
    assert balances[charlie.id] == Decimal("-30.00")

    # Financial invariant: all balances must sum to zero.
    assert sum(balances.values()) == Decimal("0.00")





def test_balances_with_multiple_payers(db_session):
    # Create two users.
    alice = User(
        full_name="Alice Multiple",
        email="ledger_multi_alice@example.com",
        hashed_password="test_hash",
    )

    bob = User(
        full_name="Bob Multiple",
        email="ledger_multi_bob@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob])
    db_session.flush()

    # Create a group.
    group = Group(
        name="Multiple Payers Group",
        created_by=alice.id,
    )

    db_session.add(group)
    db_session.flush()

    # Add both users as members.
    db_session.add_all([
        GroupMember(
            group_id=group.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group.id,
            user_id=bob.id,
            role="member",
        ),
    ])
    db_session.flush()

    # Expense 1: Alice pays $100.
    groceries = Expense(
        group_id=group.id,
        paid_by=alice.id,
        description="Groceries",
        amount=Decimal("100.00"),
    )

    # Expense 2: Bob pays $60.
    electricity = Expense(
        group_id=group.id,
        paid_by=bob.id,
        description="Electricity",
        amount=Decimal("60.00"),
    )

    db_session.add_all([groceries, electricity])
    db_session.flush()

    # Record each person's share.
    db_session.add_all([
        ExpenseSplit(
            expense_id=groceries.id,
            user_id=alice.id,
            amount_owed=Decimal("50.00"),
        ),
        ExpenseSplit(
            expense_id=groceries.id,
            user_id=bob.id,
            amount_owed=Decimal("50.00"),
        ),
        ExpenseSplit(
            expense_id=electricity.id,
            user_id=alice.id,
            amount_owed=Decimal("30.00"),
        ),
        ExpenseSplit(
            expense_id=electricity.id,
            user_id=bob.id,
            amount_owed=Decimal("30.00"),
        ),
    ])
    db_session.flush()

    # Calculate the group's balances.
    balances = calculate_group_balances(
        db=db_session,
        group_id=group.id,
    )

    assert balances[alice.id] == Decimal("20.00")
    assert balances[bob.id] == Decimal("-20.00")

    # The ledger must remain balanced.
    assert sum(balances.values()) == Decimal("0.00")

def test_group_without_expenses_has_zero_balances(db_session):
    # Create two users.
    alice = User(
        full_name="Alice Empty",
        email="ledger_empty_alice@example.com",
        hashed_password="test_hash",
    )

    bob = User(
        full_name="Bob Empty",
        email="ledger_empty_bob@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob])
    db_session.flush()

    # Create a group.
    group = Group(
        name="Empty Ledger Group",
        created_by=alice.id,
    )

    db_session.add(group)
    db_session.flush()

    # Add both members.
    db_session.add_all([
        GroupMember(
            group_id=group.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group.id,
            user_id=bob.id,
            role="member",
        ),
    ])

    db_session.flush()

    # Calculate balances without any expenses.
    balances = calculate_group_balances(
        db=db_session,
        group_id=group.id,
    )

    # Both members must have zero balances.
    assert balances == {
        alice.id: Decimal("0.00"),
        bob.id: Decimal("0.00"),
    }

    # The ledger must remain balanced.
    assert sum(balances.values()) == Decimal("0.00")




def test_uneven_splits_preserve_decimal_precision(db_session):
    # Create three users.
    alice = User(
        full_name="Alice Precision",
        email="ledger_precision_alice@example.com",
        hashed_password="test_hash",
    )

    bob = User(
        full_name="Bob Precision",
        email="ledger_precision_bob@example.com",
        hashed_password="test_hash",
    )

    charlie = User(
        full_name="Charlie Precision",
        email="ledger_precision_charlie@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob, charlie])
    db_session.flush()

    # Create a group.
    group = Group(
        name="Precision Ledger Group",
        created_by=alice.id,
    )

    db_session.add(group)
    db_session.flush()

    # Add all three members.
    db_session.add_all([
        GroupMember(
            group_id=group.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group.id,
            user_id=bob.id,
            role="member",
        ),
        GroupMember(
            group_id=group.id,
            user_id=charlie.id,
            role="member",
        ),
    ])

    db_session.flush()

    # Alice pays $100 for dinner.
    expense = Expense(
        group_id=group.id,
        paid_by=alice.id,
        description="Dinner",
        amount=Decimal("100.00"),
    )

    db_session.add(expense)
    db_session.flush()

    # Uneven shares that total exactly $100.
    db_session.add_all([
        ExpenseSplit(
            expense_id=expense.id,
            user_id=alice.id,
            amount_owed=Decimal("33.33"),
        ),
        ExpenseSplit(
            expense_id=expense.id,
            user_id=bob.id,
            amount_owed=Decimal("33.33"),
        ),
        ExpenseSplit(
            expense_id=expense.id,
            user_id=charlie.id,
            amount_owed=Decimal("33.34"),
        ),
    ])

    db_session.flush()

    # Calculate net balances.
    balances = calculate_group_balances(
        db=db_session,
        group_id=group.id,
    )

    assert balances[alice.id] == Decimal("66.67")
    assert balances[bob.id] == Decimal("-33.33")
    assert balances[charlie.id] == Decimal("-33.34")

    # Every cent must be accounted for.
    assert sum(balances.values()) == Decimal("0.00")



def test_group_balances_are_isolated(db_session):
    # Create users.
    alice = User(
        full_name="Alice Isolation",
        email="isolation_alice@example.com",
        hashed_password="test_hash",
    )
    bob = User(
        full_name="Bob Isolation",
        email="isolation_bob@example.com",
        hashed_password="test_hash",
    )
    charlie = User(
        full_name="Charlie Isolation",
        email="isolation_charlie@example.com",
        hashed_password="test_hash",
    )

    db_session.add_all([alice, bob, charlie])
    db_session.flush()

    # Create two separate groups.
    group_a = Group(name="Group A", created_by=alice.id)
    group_b = Group(name="Group B", created_by=alice.id)

    db_session.add_all([group_a, group_b])
    db_session.flush()

    # Add members to their respective groups.
    db_session.add_all([
        GroupMember(
            group_id=group_a.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group_a.id,
            user_id=bob.id,
            role="member",
        ),
        GroupMember(
            group_id=group_b.id,
            user_id=alice.id,
            role="owner",
        ),
        GroupMember(
            group_id=group_b.id,
            user_id=charlie.id,
            role="member",
        ),
    ])
    db_session.flush()

    # Record separate expenses.
    expense_a = Expense(
        group_id=group_a.id,
        paid_by=alice.id,
        description="Groceries",
        amount=Decimal("100.00"),
    )
    expense_b = Expense(
        group_id=group_b.id,
        paid_by=alice.id,
        description="Dinner",
        amount=Decimal("80.00"),
    )

    db_session.add_all([expense_a, expense_b])
    db_session.flush()

    # Record expense splits.
    db_session.add_all([
        ExpenseSplit(
            expense_id=expense_a.id,
            user_id=alice.id,
            amount_owed=Decimal("50.00"),
        ),
        ExpenseSplit(
            expense_id=expense_a.id,
            user_id=bob.id,
            amount_owed=Decimal("50.00"),
        ),
        ExpenseSplit(
            expense_id=expense_b.id,
            user_id=alice.id,
            amount_owed=Decimal("40.00"),
        ),
        ExpenseSplit(
            expense_id=expense_b.id,
            user_id=charlie.id,
            amount_owed=Decimal("40.00"),
        ),
    ])
    db_session.flush()

    # Calculate balances independently.
    balances_a = calculate_group_balances(
        db_session, group_a.id
    )
    balances_b = calculate_group_balances(
        db_session, group_b.id
    )

    assert balances_a == {
        alice.id: Decimal("50.00"),
        bob.id: Decimal("-50.00"),
    }

    assert balances_b == {
        alice.id: Decimal("40.00"),
        charlie.id: Decimal("-40.00"),
    }

    assert sum(balances_a.values()) == Decimal("0.00")
    assert sum(balances_b.values()) == Decimal("0.00")
