from pathlib import Path
from tempfile import NamedTemporaryFile

from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse
from starlette.types import Receive, Scope, Send

from ..core.service.transaction_export_formats import ExportFormat, MIME_TYPES, write_export
from ..core.service.transaction_export_service import ExportRow


class ExportFileResponse(FileResponse):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            Path(self.path).unlink(missing_ok=True)


async def build_export_response(rows: list[ExportRow], format: ExportFormat) -> ExportFileResponse:
    with NamedTemporaryFile(prefix="expenis-export-", suffix=f".{format}", delete=False) as file:
        path = Path(file.name)
    try:
        # run_in_threadpool shields the worker: cleanup cannot race an unfinished writer.
        await run_in_threadpool(write_export, path, rows, format)
        return ExportFileResponse(
            path, filename=f"ExPenis-transactions.{format}",
            media_type=MIME_TYPES[format], headers={"Cache-Control": "no-store"},
        )
    except BaseException:
        path.unlink(missing_ok=True)
        raise
