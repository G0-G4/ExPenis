import uvicorn

from ..config import DEV
from ..core.logging_config import setup_logging


def main():
    log_config = setup_logging()
    options = {"host": "0.0.0.0", "port": 8000, "log_config": log_config}
    if DEV:
        options["reload"] = True
        options["reload_excludes"] = ["logs/"]
    uvicorn.run("src.expenis.server.application:app", **options)

if __name__ == "__main__":
    main()