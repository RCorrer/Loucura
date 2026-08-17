"""Fake database client using SQLite for local development.

Drops the catalog.schema prefix from table references so that
standard SQLite can execute the queries transparently.
"""

import os
import re
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to the SQLite database file (lives next to this module)
DB_PATH = Path(__file__).parent / "local.db"


class FakeSQLiteClient:
    """SQLite-backed client that mirrors the DatabricksSQLClient interface."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)
        self._ensure_db()
        logger.info(f"\u2705 FakeSQLiteClient inicializado com DB: {self.db_path}")

    def _ensure_db(self):
        """Create and seed the database if it doesn't exist."""
        if not os.path.exists(self.db_path):
            logger.info("DB local n\u00e3o encontrado. Executando seed...")
            from src.db.seed import seed_database
            seed_database(self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        # Register custom functions to replace Databricks-specific SQL
        conn.create_function("approx_count_distinct", 1, None)  # placeholder
        return conn

    def _normalize_sql(self, sql: str) -> str:
        """Strip catalog.schema prefixes and adapt Databricks SQL to SQLite.

        Handles:
        - plataforma.segmentacao.table -> table
        - plataforma.metadata.table -> table
        - plataforma.publico.table -> table
        - plataforma.caracteristicas.table -> table
        - current_timestamp() -> datetime('now')
        - approx_count_distinct(x) -> COUNT(DISTINCT x)
        - ARRAY type handling
        """
        normalized = sql

        # Remove catalog.schema prefixes (3-part names)
        normalized = re.sub(
            r'plataforma\.(segmentacao|metadata|publico|caracteristicas)\.',
            '',
            normalized
        )

        # Replace current_timestamp() with SQLite equivalent
        normalized = re.sub(
            r'current_timestamp\(\)',
            "datetime('now')",
            normalized,
            flags=re.IGNORECASE
        )

        # Replace approx_count_distinct(x) with COUNT(DISTINCT x)
        normalized = re.sub(
            r'approx_count_distinct\(([^)]+)\)',
            r'COUNT(DISTINCT \1)',
            normalized,
            flags=re.IGNORECASE
        )

        return normalized

    def _convert_params(self, params: Optional[tuple]) -> Optional[tuple]:
        """Convert parameter types for SQLite compatibility."""
        if params is None:
            return None
        converted = []
        for p in params:
            if isinstance(p, list):
                # SQLite doesn't support arrays; store as JSON string
                import json
                converted.append(json.dumps(p))
            elif isinstance(p, bool):
                converted.append(int(p))
            else:
                converted.append(p)
        return tuple(converted)

    def execute_query(self, sql: str, params: tuple = None) -> list:
        """Execute a SELECT query and return rows as lists."""
        try:
            normalized = self._normalize_sql(sql)
            converted_params = self._convert_params(params)
            logger.debug(f"SQL (normalized): {normalized}")
            logger.debug(f"Params: {converted_params}")

            with self._get_connection() as conn:
                cursor = conn.cursor()
                if converted_params:
                    cursor.execute(normalized, converted_params)
                else:
                    cursor.execute(normalized)
                rows = cursor.fetchall()
                return [list(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro na query (SQLite): {e}")
            logger.error(f"SQL original: {sql}")
            logger.error(f"SQL normalizado: {self._normalize_sql(sql)}")
            raise

    def fetch_one(self, sql: str, params: tuple = None) -> list:
        """Execute query and return first row."""
        rows = self.execute_query(sql, params)
        return rows[0] if rows else None

    def fetch_all(self, sql: str, params: tuple = None) -> list:
        """Execute query and return all rows."""
        return self.execute_query(sql, params)

    def execute_insert(self, sql: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected row count."""
        try:
            normalized = self._normalize_sql(sql)
            converted_params = self._convert_params(params)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                if converted_params:
                    cursor.execute(normalized, converted_params)
                else:
                    cursor.execute(normalized)
                conn.commit()
                return cursor.rowcount or 0

        except Exception as e:
            logger.error(f"Erro no insert (SQLite): {e}")
            logger.error(f"SQL original: {sql}")
            raise
