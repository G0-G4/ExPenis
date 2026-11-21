import csv
import io
import json
import os
import re
from datetime import date
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import httpx
from playwright.sync_api import Page, expect

from e2e.helpers import PASSWORD, expect_transactions_screen, login_via_ui, open_app, unique_username

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def seed_history():
    username = unique_username('e2e-export')
    api = httpx.Client(base_url=os.environ.get('E2E_API_URL', 'http://127.0.0.1:8000'))
    response = api.post('/api/register', json={'username': username, 'password': PASSWORD})
    response.raise_for_status()
    api.headers['Authorization'] = 'Bearer ' + response.json()['access_token']
    category = api.post('/api/categories', json={'name': 'Еда 🍕', 'type': 'expense'})
    category.raise_for_status()
    category_id = category.json()['id']
    accounts = []
    for name in ['Кошелёк 💰', 'Старый']:
        response = api.post('/api/accounts/account', json={'name': name, 'amount': 0, 'currency_code': 'RUB'})
        response.raise_for_status()
        accounts.append(response.json()['id'])
    today = date.today().isoformat()
    description = '=1+1,"текст"\nстрока'
    for account, when, amount in [(accounts[0], '2000-01-01', 1), (accounts[0], today, 12.5), (accounts[1], today, -2.5)]:
        response = api.post('/api/transactions', json={
            'account_id': account, 'category_id': category_id, 'amount': amount,
            'created_at': when + 'T12:34:56', 'description': description,
            'tags': ['еда,дом', 'Отпуск "лето"'],
        })
        response.raise_for_status()
    response = api.delete(f'/api/accounts/account/{accounts[1]}')
    response.raise_for_status()
    api.close()
    return username, description


def read_download(download, format):
    assert download.suggested_filename == f'ExPenis-transactions.{format}'
    content = download.path().read_bytes()
    if format == 'csv':
        assert content.startswith(b'\xef\xbb\xbf')
        return list(csv.reader(io.StringIO(content.decode('utf-8-sig'))))
    with ZipFile(io.BytesIO(content)) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        assert workbook.find('s:sheets/s:sheet', NS).attrib['name'] == 'Операции'
        root = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        return [[cell.find('s:is/s:t', NS).text if cell.attrib.get('t') == 'inlineStr'
                 else cell.find('s:v', NS).text for cell in row]
                for row in root.findall('s:sheetData/s:row', NS)]


def test_export_csv_xlsx_filters_and_errors(page: Page, tmp_path):
    username, description = seed_history()
    open_app(page)
    login_via_ui(page, username, PASSWORD)
    expect_transactions_screen(page)
    page.get_by_role('button', name='Settings', exact=True).click()
    page.get_by_role('button', name='Экспорт операций', exact=True).click()
    expect(page.get_by_role('heading', name='Экспорт операций')).to_be_visible()
    button = page.get_by_role('button', name='Экспортировать', exact=True)
    expect(button).to_be_enabled()
    for format in ['csv', 'xlsx']:
        page.get_by_role('button', name=format.upper(), exact=True).click()
        with page.expect_download() as result:
            button.click()
        rows = read_download(result.value, format)
        assert len(rows) == 4 and all(len(row) == 10 for row in rows)
        assert rows[1][0].startswith('2000-01-01') if format == 'csv' else float(rows[1][0]) < 40000
        assert rows[2][4] == 'Кошелёк 💰' and rows[3][4] == 'Старый (удалён)'
        assert rows[2][6] == description
        assert json.loads(rows[2][9]) == ['Отпуск "лето"', 'еда,дом']
        assert float(rows[2][7]) == 1 and float(rows[2][8]) == 12.5
        assert float(rows[3][2]) == -2.5
        expect(button).to_be_enabled()
    # Use the selected current-month range and only the deleted account.
    page.get_by_role('switch', name='За всё время').click()
    page.get_by_role('button', name='Выбрать период').click()
    page.get_by_role('button', name='Выбрать', exact=True).click()
    page.get_by_role('switch', name='Все счета').click()
    page.get_by_role('checkbox', name='Старый (удалён)').click()
    for format in ['csv', 'xlsx']:
        page.get_by_role('button', name=format.upper(), exact=True).click()
        with page.expect_download() as result:
            button.click()
        rows = read_download(result.value, format)
        assert len(rows) == 2 and rows[1][4] == 'Старый (удалён)'
        expect(button).to_be_enabled()
    downloads = []
    page.on('download', lambda download: downloads.append(download))
    page.route('**/api/exports/transactions?*', lambda route: route.fulfill(
        status=422, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'},
        body='{"detail":"Проверочная ошибка экспорта"}',
    ))
    with page.expect_response(re.compile(r'/api/exports/transactions\?')) as failure:
        button.click()
    assert failure.value.status == 422
    expect(button).to_be_enabled()
    expect(page.get_by_text('Проверочная ошибка экспорта', exact=True).last).to_be_visible()
    assert not downloads
    page.screenshot(path=str(tmp_path / 'export-error.png'), full_page=True)
    page.unroute('**/api/exports/transactions?*')
    with page.expect_download() as result:
        button.click()
    assert len(read_download(result.value, 'xlsx')) == 2
    expect(button).to_be_enabled()
    page.screenshot(path=str(tmp_path / 'export-screen.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    page.screenshot(path=str(tmp_path / 'export-mobile.png'))
