"""Infraestrutura compartilhada; cada processo acessa somente seu próprio banco."""
import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


@contextmanager
def connection():
    with psycopg.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=2,
        options="-c statement_timeout=2000",
        row_factory=dict_row,
    ) as conn:
        yield conn


def initialize(seeds):
    with connection() as conn:
        # Serializa a inicialização para evitar seeds duplicados entre processos.
        conn.execute("SELECT pg_advisory_xact_lock(20260920)")
        conn.execute("""CREATE TABLE IF NOT EXISTS registros (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            dados jsonb NOT NULL CHECK (jsonb_typeof(dados) = 'object')
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS registros_dados_idx ON registros USING gin (dados)")
        if not conn.execute("SELECT 1 FROM registros LIMIT 1").fetchone():
            for seed in seeds:
                conn.execute("INSERT INTO registros (dados) VALUES (%s)", (Jsonb(seed),))


def list_records(filters=None):
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, dados FROM registros WHERE dados @> %s ORDER BY id",
            (Jsonb(filters or {}),),
        ).fetchall()
        return [{**row["dados"], "id": row["id"]} for row in rows]


def get_record(record_id):
    with connection() as conn:
        row = conn.execute("SELECT id, dados FROM registros WHERE id = %s", (record_id,)).fetchone()
        return {**row["dados"], "id": row["id"]} if row else None


def create_record(data):
    with connection() as conn:
        row = conn.execute(
            "INSERT INTO registros (dados) VALUES (%s) RETURNING id", (Jsonb(data),)
        ).fetchone()
        return {**data, "id": row["id"]}
