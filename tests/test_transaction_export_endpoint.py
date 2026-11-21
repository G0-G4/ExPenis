import asyncio
import csv
import io
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.expenis.core.models import Account, db
from src.expenis.core.service.transaction_export_service import ExportValidationError
from src.expenis.server.application import app, auth
from src.expenis.server.export_response import ExportFileResponse, build_export_response


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.headers['Authorization'] = f'Bearer {auth.create_access_token(uid="1")}'
            yield client


@pytest.mark.asyncio
async def test_accounts_include_deleted_and_isolate_users(client):
    async with db:
        await db.run(lambda: Account.create(user_id=1, name="Старый", is_deleted=True))
        await db.run(lambda: Account.create(user_id=2, name="Чужой"))
    response = await client.get('/api/exports/accounts')
    assert response.status_code == 200
    assert len(response.json()['accounts']) == 1
    assert response.json()['accounts'][0]['is_deleted'] is True


@pytest.mark.asyncio
@pytest.mark.parametrize('format,mime', [
    ('csv', 'text/csv'), ('xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
])
async def test_download_response_and_cleanup(client, format, mime, monkeypatch, tmp_path):
    monkeypatch.setattr('tempfile.tempdir', str(tmp_path))
    response = await client.get('/api/exports/transactions', params={'format': format})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith(mime)
    assert response.headers['cache-control'] == 'no-store'
    assert f'ExPenis-transactions.{format}' in response.headers['content-disposition']
    if format == 'csv':
        assert len(list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))) == 1
    else:
        assert response.content.startswith(b'PK')
    assert not list(tmp_path.glob('expenis-export-*'))


@pytest.mark.asyncio
@pytest.mark.parametrize('params', [
    {'format':'qif'}, {'format':'csv', 'date_from':'2026-11-01'},
    {'format':'csv', 'date_from':'2026-11-02', 'date_to':'2026-11-01'},
    {'format':'csv', 'account_ids':''}, {'format':'csv', 'account_ids':0},
    {'format':'csv', 'date_from':'bad'}, {},
])
async def test_invalid_queries_do_not_return_files(client, params):
    response = await client.get('/api/exports/transactions', params=params)
    assert response.status_code == 422
    assert 'content-disposition' not in response.headers


@pytest.mark.asyncio
async def test_unknown_and_foreign_account_same_error(client):
    async with db:
        foreign = await db.run(lambda: Account.create(user_id=2, name="Чужой"))
    results = [await client.get('/api/exports/transactions', params={
        'format':'csv', 'account_ids': value,
    }) for value in [foreign.id, 99999]]
    assert [r.status_code for r in results] == [404, 404]
    assert results[0].json() == results[1].json()


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['/api/exports/accounts', '/api/exports/transactions?format=csv'])
async def test_no_auth_no_data(client, path):
    client.headers.pop('Authorization')
    response = await client.get(path)
    assert response.status_code in (401, 403, 422)
    assert 'content-disposition' not in response.headers


@pytest.mark.asyncio
async def test_render_failure_removes_temporary_file(client, monkeypatch, tmp_path):
    monkeypatch.setattr('tempfile.tempdir', str(tmp_path))
    def fail(path, *args):
        path.write_bytes(b'partial')
        raise ExportValidationError('Текст превышает предел XLSX')
    monkeypatch.setattr('src.expenis.server.export_response.write_export', fail)
    response = await client.get('/api/exports/transactions?format=xlsx')
    assert response.status_code == 422
    assert not list(tmp_path.glob('expenis-export-*'))


@pytest.mark.asyncio
async def test_cancelled_response_removes_file(tmp_path):
    path = tmp_path / 'partial.csv'
    path.write_text('text')
    response = ExportFileResponse(path)
    async def send(message):
        raise asyncio.CancelledError
    async def receive():
        return {'type': 'http.disconnect'}
    with pytest.raises(asyncio.CancelledError):
        await response({'type': 'http', 'method': 'GET', 'headers': []}, receive, send)
    assert not path.exists()


@pytest.mark.asyncio
async def test_cancelled_writer_removes_file(monkeypatch, tmp_path):
    monkeypatch.setattr('tempfile.tempdir', str(tmp_path))
    async def cancelled(*args):
        raise asyncio.CancelledError
    monkeypatch.setattr('src.expenis.server.export_response.run_in_threadpool', cancelled)
    with pytest.raises(asyncio.CancelledError):
        await build_export_response([], 'csv')
    assert not list(tmp_path.glob('expenis-export-*'))
