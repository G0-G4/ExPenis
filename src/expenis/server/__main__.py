import uvicorn

from ..core.logging_config import setup_logging


def main():
    log_config = setup_logging()
    uvicorn.run("src.expenis.server.application:app", host="0.0.0.0", port=8000, reload=True, log_config=log_config)

if __name__ == "__main__":
    main()