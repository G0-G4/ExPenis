from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.expenis.core.models import PersonalGreeting, User, db
from src.expenis.core.service.personal_greeting_service import assign_greetings, inspect_greeting
from src.expenis.server.application import app, auth


@pytest.fixture
async def clients():
    async with db:
        users = [await db.run(lambda: User.create(username=name)) for name in ("alice", "bob")]
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as a:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as b:
                for client, user in zip((a, b), users):
                    client.headers["Authorization"] = f"Bearer {auth.create_access_token(uid=str(user.id))}"
                yield a, b, users


@pytest.mark.asyncio
async def test_read_dismiss_replace_and_isolate(clients):
    a, b, users = clients
    uid = users[0].id
    assert (await a.get("/api/me/greeting")).json() == {"greeting": None}
    await assign_greetings([uid], "Hello 🎉\nCongrats")
    response = await a.get("/api/me/greeting")
    assert response.status_code == 200
    first = response.json()["greeting"]
    assert first == {"id": (await inspect_greeting(uid)).assignment_id,
                     "text": "Hello 🎉\nCongrats", "expires_at": None}
    assert (await b.get("/api/me/greeting")).json() == {"greeting": None}
    path = f"/api/me/greeting/{first['id']}/dismiss"
    assert (await b.post(path)).status_code == 204
    assert (await a.get("/api/me/greeting")).json()["greeting"] == first
    assert (await a.post(path)).status_code == 204
    assert (await a.post(path)).status_code == 204
    assert (await a.get("/api/me/greeting")).json() == {"greeting": None}
    await assign_greetings([uid], first["text"])
    assert (await a.post(path)).status_code == 204
    assert (await a.get("/api/me/greeting")).json()["greeting"]["id"] != first["id"]
    assert (await a.post(f"/api/me/greeting/{uuid4()}/dismiss")).status_code == 204
    assert (await a.post("/api/me/greeting/invalid/dismiss")).status_code == 422


@pytest.mark.asyncio
async def test_expiration_and_authorization(clients):
    a, b, users = clients
    uid = users[0].id
    day = (datetime.now(UTC) + timedelta(days=1)).date()
    await assign_greetings([uid], "Timed", day)
    greeting = (await a.get("/api/me/greeting")).json()["greeting"]
    assert greeting["expires_at"].endswith("Z")
    await db.run(lambda: PersonalGreeting.update(expires_at=datetime.now(UTC) - timedelta(seconds=1))
                 .where(PersonalGreeting.user == uid).execute())
    assert (await a.get("/api/me/greeting")).json() == {"greeting": None}
    a.headers.clear()
    assert (await a.get("/api/me/greeting")).status_code == 401
    assert (await a.post(f"/api/me/greeting/{greeting['id']}/dismiss")).status_code == 401
    a.headers["Authorization"] = "Bearer invalid"
    assert (await a.get("/api/me/greeting")).status_code == 401
