import asyncio
import csv
import json
import os
import resource
import sqlite3
import tempfile
import time
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

root = Path.cwd()
workspace = Path(tempfile.mkdtemp(prefix='expenis-export-bench-'))
os.environ['EXPENIS_DB_PATH'] = str(workspace / 'benchmark.db')
with sqlite3.connect(os.environ['EXPENIS_DB_PATH']) as connection:
    for migration in sorted((root/'migrations').glob('*.sql')):
        connection.executescript(migration.read_text())
from src.expenis.core.models import Account, Category, Transaction, db
from src.expenis.core.service.transaction_export_service import ExportFilter, get_export_rows
from src.expenis.server.export_response import build_export_response

async def main():
    count=20_000
    async with db:
        account = await db.run(lambda: Account.create(user_id=1, name='Benchmark', currency_code='EUR'))
        category = await db.run(lambda: Category.create(user_id=1, name='Расход', type='expense'))
        for offset in range(0,count,500):
            await db.run(lambda: Transaction.insert_many([
                dict(user_id=1, account=account.id, category=category.id,
                     amount=12.5, exchange_rate=100, description='Тест, "строка"\nданные',
                     created_at=datetime(2026,11,21,12,34,56))
                for _ in range(500)
            ]).execute())
        results={}
        for format in ['csv','xlsx']:
            start=time.perf_counter()
            rows=await get_export_rows(1,ExportFilter())
            response=await build_export_response(rows,format)
            path=Path(response.path)
            if format=='csv':
                with path.open(encoding='utf-8-sig',newline='') as file:
                    actual=sum(1 for _ in csv.reader(file))-1
            else:
                with ZipFile(path) as archive:
                    actual=sum(1 for _,element in ET.iterparse(archive.open('xl/worksheets/sheet1.xml'))
                               if element.tag.endswith('}row'))-1
            assert actual==count, (format,actual)
            size=path.stat().st_size
            async def send(message): pass
            async def receive(): return {'type':'http.disconnect'}
            await response({'type':'http','method':'GET','headers':[]},receive,send)
            assert not path.exists()
            results[format]={'rows':actual,'seconds':round(time.perf_counter()-start,3),'bytes':size}
        results['peak_rss_mib']=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024/1024,1)
        print(json.dumps(results,indent=2))
        (root/'openspec/changes/add-transaction-export/benchmark.json').write_text(json.dumps(results,indent=2)+'\n')
    await db.close_pool()

asyncio.run(main())
