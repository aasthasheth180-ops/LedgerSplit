
import asyncio

from httpx2 import ASGITransport, AsyncClient

from app.main import app


async def check_root():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to LedgerSplit API",
        "version": "0.1.0",
    }


async def check_health():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "ledgersplit-api",
    }


def test_root():
    asyncio.run(check_root())


def test_health_check():
    asyncio.run(check_health())
