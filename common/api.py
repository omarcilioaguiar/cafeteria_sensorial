from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from common import database


def create_app(title, seeds):
    @asynccontextmanager
    async def lifespan(app):
        database.initialize(seeds)
        yield

    app = FastAPI(title=title, version="1.0.0", lifespan=lifespan)

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": "Banco de dados temporariamente indisponível."})

    @app.get("/health", tags=["Operação"])
    def health():
        with database.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "service": title}

    return app


def find_or_404(record_id):
    record = database.get_record(record_id)
    if record is None:
        raise HTTPException(404, "Registro não encontrado.")
    return record
