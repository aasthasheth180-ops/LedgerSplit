
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.group_member import GroupMember
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User


def create_group(
    db: Session,
    name: str,
    creator_id: int,
) -> Group:
    try:
        # Step 1: Create the group
        group = Group(
            name=name.strip(),
            created_by=creator_id,
        )

        db.add(group)
        db.flush()

        # Step 2: Make the creator an owner
        owner = GroupMember(
            group_id=group.id,
            user_id=creator_id,
            role="owner",
        )

        db.add(owner)

        # Step 3: Save both records together
        db.commit()
        db.refresh(group)

        return group

    except Exception:
        db.rollback()
        raise




def get_user_groups(
    db: Session,
    user_id: int,
) -> list[Group]:
    statement = (
        select(Group)
        .join(
            GroupMember,
            Group.id == GroupMember.group_id,
        )
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc(), Group.id.desc())
    )

    return list(db.scalars(statement).all())




def add_group_member(
    db: Session,
    group_id: int,
    user_id: int,
    requester_id: int,
) -> GroupMember:
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    owner = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == requester_id,
            GroupMember.role == "owner",
        )
    )

    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group owners can add members",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    existing_member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )

    if existing_member is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a group member",
        )

    try:
        member = GroupMember(
            group_id=group_id,
            user_id=user_id,
            role="member",
        )

        db.add(member)
        db.commit()
        db.refresh(member)

        return member

    except Exception:
        db.rollback()
        raise





def get_group_members(
    db: Session,
    group_id: int,
    requester_id: int,
) -> list[GroupMember]:
    # Check whether the group exists.
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # Check whether the requester belongs to the group.
    requester_membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == requester_id,
        )
    )

    if requester_membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # Return all members of the group.
    statement = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.id)
    )

    return list(db.scalars(statement).all())
