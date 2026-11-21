import asyncio
import re
import sqlite3
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.expenis.core.models import db
from src.expenis.core.service.category_service import (
    create_category, create_default_categories, delete_category,
    get_category_by_id, get_user_categories, update_category,
)
from src.expenis.core.utils.category_colors import CATEGORY_COLORS
from src.expenis.server.application import app, auth

ROOT = Path(__file__).resolve().parents[1]


def test_palette_matches_migration_and_client():
    assert len(set(CATEGORY_COLORS)) == 32
    assert all(re.fullmatch(r"#[0-9A-F]{6}", value) for value in CATEGORY_COLORS)
    assert "#BAB0AC" not in CATEGORY_COLORS
    for path in ("migrations/008_category_colors.sql", "frontend/lib/utils/category_colors.dart"):
        values = re.findall(r"#[0-9A-F]{6}", (ROOT / path).read_text())
        assert tuple(dict.fromkeys(values)) == CATEGORY_COLORS


def test_migration_assigns_colors_per_user_without_changing_transactions():
    with sqlite3.connect(":memory:") as conn:
        migrations = sorted((ROOT / "migrations").glob("*.sql"))
        for migration in migrations[:-1]:
            conn.executescript(migration.read_text())
        for user in (1, 2):
            conn.executemany(
                "INSERT INTO categories(user_id, name, type) VALUES (?, ?, 'expense')",
                [(user, f"Category {i}") for i in range(35)],
            )
        conn.execute("INSERT INTO accounts(user_id, name, currency_code) VALUES (1, 'Cash', 'RUB')")
        conn.execute("INSERT INTO transactions(user_id, account_id, category_id, amount) VALUES (1, 1, 1, 123)")
        before = conn.execute("SELECT * FROM transactions").fetchall()
        conn.executescript(migrations[-1].read_text())
        for user in (1, 2):
            rows = conn.execute("SELECT color FROM categories WHERE user_id = ? ORDER BY id", (user,)).fetchall()
            assert [row[0] for row in rows] == [CATEGORY_COLORS[i % 32] for i in range(35)]
        assert conn.execute("SELECT * FROM transactions").fetchall() == before
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


@pytest.mark.asyncio
async def test_colors_reuse_only_after_exhaustion_and_are_user_scoped():
    async with db:
        categories = [await create_category(1, str(i), "expense") for i in range(33)]
        assert [c.color for c in categories[:32]] == list(CATEGORY_COLORS)
        assert categories[32].color == CATEGORY_COLORS[0]
        other_user = await create_category(2, "Other user", "income")
        assert other_user.color == CATEGORY_COLORS[0]
        assert await get_category_by_id(2, categories[0].id) is None
        freed = categories[10].color
        await delete_category(categories[10])
        replacement = await create_category(1, "Replacement", "income")
        assert replacement.color == freed
        category = categories[0]
        await update_category(category, name="Renamed", type="income")
        assert (await get_category_by_id(1, category.id)).color == category.color


@pytest.mark.asyncio
async def test_concurrent_creation_uses_distinct_free_colors():
    async with db:
        async def create(index: int):
            try:
                return await create_category(1, str(index), "expense")
            finally:
                await db.aclose()
        categories = await asyncio.gather(*(create(i) for i in range(12)))
        assert len({category.color for category in categories}) == 12


@pytest.mark.asyncio
async def test_default_colors_are_assigned_once():
    async with db:
        await create_default_categories(1)
        income, expense = await get_user_categories(1)
        before = {c.id: c.color for c in income + expense}
        assert len(set(before.values())) == 14
        await create_default_categories(1)
        income, expense = await get_user_categories(1)
        assert {c.id: c.color for c in income + expense} == before


@pytest.fixture
async def clients():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as first:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as second:
                for client in (first, second):
                    client.headers["Authorization"] = f"Bearer {auth.create_access_token(uid='1')}"
                yield first, second


@pytest.mark.asyncio
async def test_api_color_changes_are_shared_and_legacy_updates_preserve_them(clients):
    first, second = clients
    created = await first.post("/api/categories", json={"name": "Food", "type": "expense"})
    assert created.status_code == 200, created.text
    category = created.json()
    assert category["color"] in CATEGORY_COLORS
    path = f"/api/categories/{category['id']}"
    updated = await first.put(path, json={"name": "Food", "type": "expense", "color": CATEGORY_COLORS[20]})
    assert updated.status_code == 200, updated.text
    assert updated.json()["color"] == CATEGORY_COLORS[20]
    legacy = await second.put(path, json={"name": "Renamed", "type": "income"})
    assert legacy.status_code == 200
    assert legacy.json()["color"] == CATEGORY_COLORS[20]
    assert (await first.get(path)).json()["color"] == CATEGORY_COLORS[20]
    listed = (await second.get("/api/categories")).json()["categories"]
    assert listed[str(category["id"])]["color"] == CATEGORY_COLORS[20]
    new_category = (await first.post("/api/categories", json={"name": "Other", "type": "expense"})).json()
    duplicate = await first.put(f"/api/categories/{new_category['id']}", json={"name": "Other", "type": "expense", "color": CATEGORY_COLORS[20]})
    assert duplicate.status_code == 200
    assert duplicate.json()["color"] == CATEGORY_COLORS[20]


@pytest.mark.asyncio
@pytest.mark.parametrize("color", [None, "#BAB0AC", "#000000", "bad"])
async def test_api_rejects_invalid_colors_without_partial_update(clients, color):
    first, _ = clients
    category = (await first.post("/api/categories", json={"name": "Original", "type": "expense"})).json()
    path = f"/api/categories/{category['id']}"
    response = await first.put(path, json={"name": "Changed", "type": "income", "color": color})
    assert response.status_code == 422, response.text
    assert (await first.get(path)).json() == category


@pytest.mark.asyncio
async def test_api_hides_foreign_and_missing_categories(clients):
    first, second = clients
    category = (await first.post("/api/categories", json={"name": "Private", "type": "expense"})).json()
    second.headers["Authorization"] = f"Bearer {auth.create_access_token(uid='2')}"
    for category_id in (category["id"], 99999):
        path = f"/api/categories/{category_id}"
        assert (await second.get(path)).status_code == 404
        response = await second.put(path, json={"name": "Changed", "type": "income", "color": CATEGORY_COLORS[2]})
        assert response.status_code == 404
    assert (await first.get(f"/api/categories/{category['id']}")).json() == category


@pytest.mark.asyncio
async def test_metadata_save_does_not_overwrite_a_newer_color():
    async with db:
        category = await create_category(1, "Original", "expense")
        stale = await get_category_by_id(1, category.id)
        await update_category(category, color=CATEGORY_COLORS[5])
        updated = await update_category(stale, name="Renamed")
        assert updated.color == CATEGORY_COLORS[5]
        assert (await get_category_by_id(1, category.id)).color == CATEGORY_COLORS[5]
