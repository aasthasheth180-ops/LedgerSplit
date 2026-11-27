import pytest
from fastapi import HTTPException
from sqlalchemy import select, func
from tests.test_payment_service import payment_setup
from app.models.group import Group
from app.models.group_member import GroupMember
from app.services.group_service import create_group


def test_group_retry_and_conflict(db_session,payment_setup):
    db,d=db_session,payment_setup
    uid=d["alice_id"]
    g=create_group(db,"Retry group",uid,idempotency_key="group-1")
    gid=g.id
    assert create_group(db,"Retry group",uid,idempotency_key="group-1").id==gid
    assert db.scalar(select(func.count()).select_from(GroupMember).where(GroupMember.group_id==gid))==1
    with pytest.raises(HTTPException) as e:
        create_group(db,"Changed group",uid,idempotency_key="group-1")
    assert e.value.status_code==409
    assert create_group(db,"Retry group",uid,idempotency_key="group-2").id!=gid
    assert create_group(db,"Retry group",d["bob_id"],idempotency_key="group-1").id!=gid
    assert db.scalar(select(func.count()).select_from(Group).where(Group.created_by==uid,Group.idempotency_key=="group-1"))==1
