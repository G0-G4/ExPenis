import csv
import json
from pathlib import Path
from typing import Literal

import xlsxwriter  # type: ignore[import-untyped]

from .transaction_export_service import ExportRow, ExportValidationError

ExportFormat = Literal["csv", "xlsx"]
HEADERS = (
    "Дата и время", "Тип", "Сумма", "Валюта", "Счёт", "Категория",
    "Комментарий", "Курс к рублю", "Сумма в рублях", "Теги",
)
MIME_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
XLSX_MAX_ROWS = 1_048_576
XLSX_MAX_STRING = 32_767


def row_values(row: ExportRow) -> list[str | float]:
    return [
        row.created_at.isoformat(), "Доход" if row.type == "income" else "Расход",
        row.amount, row.currency, row.account, row.category, row.description,
        row.exchange_rate, row.amount_rubles, json.dumps(row.tags, ensure_ascii=False),
    ]


def write_export(path: Path, rows: list[ExportRow], format: ExportFormat) -> None:
    if format == "csv":
        with path.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(HEADERS)
            writer.writerows(row_values(row) for row in rows)
        return
    if format != "xlsx":
        raise ExportValidationError("Неизвестный формат экспорта")
    if len(rows) + 1 > XLSX_MAX_ROWS:
        raise ExportValidationError("Слишком много строк для XLSX. Выберите CSV или сократите период")
    with xlsxwriter.Workbook(path, {"constant_memory": True}) as workbook:
        sheet = workbook.add_worksheet("Операции")
        date_format = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss"})
        sheet.set_column(0, 0, 22)
        sheet.set_column(1, 9, 20)
        for col, header in enumerate(HEADERS):
            sheet.write_string(0, col, header)
        for index, row in enumerate(rows, start=1):
            for col, value in enumerate(row_values(row)):
                if col == 0:
                    result = sheet.write_datetime(
                        index, col, row.created_at.replace(tzinfo=None), date_format,
                    )
                elif isinstance(value, str):
                    if len(value) > XLSX_MAX_STRING:
                        raise ExportValidationError("Текст превышает предел XLSX. Выберите CSV")
                    result = sheet.write_string(index, col, value)
                else:
                    result = sheet.write_number(index, col, value)
                if result != 0:
                    raise ExportValidationError("Не удалось записать значение XLSX без потерь")
