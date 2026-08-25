from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from src.expenis.core.models import db
from src.expenis.core.service import register_user
from src.expenis.server.application import app, auth


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register_and_login(client: AsyncClient, username: str = "alice") -> dict:
    async with db:
        await register_user(username, "s3cret-pw")
    response = await client.post(
        "/api/login",
        json={"username": username, "password": "s3cret-pw"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_refresh_issues_new_pair_and_old_refresh_still_works(client: AsyncClient):
    tokens = await _register_and_login(client)
    refresh = await client.post(
        "/api/refresh",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert refresh.status_code == 200, refresh.text
    body = refresh.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["access_token"] != tokens["access_token"]
    assert body["refresh_token"] != tokens["refresh_token"]

    me = await client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


@pytest.mark.asyncio
async def test_expired_access_token_returns_401(client: AsyncClient):
    tokens = await _register_and_login(client)
    me = await client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    user_id = str(me.json()["id"])
    expired = auth.create_access_token(uid=user_id, expiry=timedelta(seconds=-5))
    response = await client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401
    assert response.json()["error_type"] == "JWTDecodeError"


@pytest.mark.asyncio
async def test_expired_refresh_token_returns_401(client: AsyncClient):
    tokens = await _register_and_login(client)
    me = await client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    user_id = str(me.json()["id"])
    expired = auth.create_refresh_token(uid=user_id, expiry=timedelta(seconds=-5))
    response = await client.post(
        "/api/refresh",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_token_cannot_be_used_to_refresh(client: AsyncClient):
    tokens = await _register_and_login(client)
    response = await client.post(
        "/api/refresh",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code in (401, 422)
