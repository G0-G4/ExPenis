import csv
import json
from datetime import datetime
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pytest

from src.expenis.core.service.transaction_export_formats import HEADERS, write_export
from src.expenis.core.service.transaction_export_service import ExportRow, ExportValidationError

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@pytest.fixture
def row():
    return ExportRow(
        datetime.fromisoformat("2026-11-21T23:59:59+03:00"), "expense", -12.56789,
        "EUR", "Кошелёк 💰", "https://example.org", '=1+1,"текст"\nстрока',
        100.123, -12.56789 * 100.123, ('еда,дом', 'тег "два"'),
    )


def test_csv_round_trip(tmp_path, row):
    path = tmp_path / "data.csv"
    write_export(path, [row], "csv")
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as file:
        header, values = list(csv.reader(file))
    assert header == list(HEADERS) and len(values) == 10
    assert values[0] == row.created_at.isoformat()
    assert values[1] == "Расход" and float(values[2]) == row.amount
    assert values[4:7] == [row.account, row.category, row.description]
    assert float(values[7]) == row.exchange_rate and float(values[8]) == row.amount_rubles
    assert json.loads(values[9]) == list(row.tags)


def test_xlsx_types_and_wall_clock(tmp_path, row):
    path = tmp_path / "data.xlsx"
    write_export(path, [row], "xlsx")
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        assert [s.attrib['name'] for s in workbook.findall("s:sheets/s:sheet", NS)] == ["Операции"]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = sheet.findall("s:sheetData/s:row", NS)
        assert len(rows) == 2
        cells = {c.attrib['r']: c for c in rows[1]}
        assert cells['A2'].attrib.get('t', 'n') == 'n'
        expected_date = (row.created_at.replace(tzinfo=None) - datetime(1899, 12, 30)).total_seconds() / 86400
        assert float(cells['A2'].find('s:v', NS).text) == pytest.approx(expected_date)
        for ref, value in [('C2', row.amount), ('H2', row.exchange_rate), ('I2', row.amount_rubles)]:
            assert float(cells[ref].find('s:v', NS).text) == pytest.approx(value)
        assert cells['G2'].find('s:is/s:t', NS).text == row.description
        assert cells['F2'].find('s:is/s:t', NS).text == row.category
        assert not sheet.findall('.//s:f', NS) and not sheet.findall('.//s:hyperlink', NS)
        assert 'yyyy-mm-dd hh:mm:ss' in archive.read('xl/styles.xml').decode()


@pytest.mark.parametrize('format', ['csv', 'xlsx'])
def test_empty_export_has_headers(tmp_path, format):
    path = tmp_path / ('empty.' + format)
    write_export(path, [], format)
    if format == 'csv':
        assert list(csv.reader(path.read_text(encoding='utf-8-sig').splitlines())) == [list(HEADERS)]
    else:
        with ZipFile(path) as archive:
            sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            assert len(sheet.findall('s:sheetData/s:row', NS)) == 1


def test_xlsx_limits_are_errors(tmp_path, row, monkeypatch):
    monkeypatch.setattr('src.expenis.core.service.transaction_export_formats.XLSX_MAX_ROWS', 1)
    with pytest.raises(ExportValidationError, match='Слишком много строк'):
        write_export(tmp_path / 'large.xlsx', [row], 'xlsx')
    monkeypatch.setattr('src.expenis.core.service.transaction_export_formats.XLSX_MAX_ROWS', 100)
    monkeypatch.setattr('src.expenis.core.service.transaction_export_formats.XLSX_MAX_STRING', 2)
    with pytest.raises(ExportValidationError, match='Текст превышает'):
        write_export(tmp_path / 'long.xlsx', [row], 'xlsx')
