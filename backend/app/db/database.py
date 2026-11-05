import asyncio
import json
import sqlite3
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from app.config import settings

class Database:
    def __init__(self, db_url: str):
        self.db_url = db_url
        if db_url.startswith("sqlite:///"):
            self.db_path = db_url.replace("sqlite:///", "")
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.is_sqlite = True
        else:
            self.db_path = str(settings.DATA_DIR / "creatrix_pulse.db")
            self.is_sqlite = True

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    async def init_db(self):
        await asyncio.to_thread(self._init_db_sync)

    def _init_db_sync(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            # Users
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")

            # Datasets
            cur.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                row_count INTEGER NOT NULL DEFAULT 0,
                column_count INTEGER NOT NULL DEFAULT 0,
                capabilities TEXT NOT NULL DEFAULT '{}',
                columns TEXT NOT NULL DEFAULT '[]',
                date_range TEXT DEFAULT NULL,
                filter_options TEXT NOT NULL DEFAULT '{"categories": [], "regions": []}',
                error_message TEXT DEFAULT NULL,
                schema_metadata TEXT DEFAULT NULL,
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                started_at INTEGER DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);")

            # Dataset Rows
            cur.execute("""
            CREATE TABLE IF NOT EXISTS dataset_rows (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                order_id TEXT,
                transaction_date TEXT NOT NULL,
                product_id TEXT,
                product_name TEXT NOT NULL,
                product_category TEXT,
                region TEXT,
                customer_identifier TEXT,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL DEFAULT 0.0,
                revenue REAL NOT NULL DEFAULT 0.0,
                cost REAL DEFAULT NULL,
                raw_payload TEXT DEFAULT NULL,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dataset_rows_dataset_date ON dataset_rows(dataset_id, transaction_date);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dataset_rows_category ON dataset_rows(dataset_id, product_category);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dataset_rows_region ON dataset_rows(dataset_id, region);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dataset_rows_customer ON dataset_rows(dataset_id, customer_identifier);")

            # Mappings
            cur.execute("""
            CREATE TABLE IF NOT EXISTS dataset_mappings (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                source_column TEXT NOT NULL,
                target_dimension TEXT NOT NULL,
                data_type TEXT NOT NULL DEFAULT 'string',
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            );
            """)

            # Reports
            cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                user_id TEXT,
                title TEXT NOT NULL,
                format TEXT NOT NULL DEFAULT 'csv',
                parameters TEXT NOT NULL DEFAULT '{}',
                row_count INTEGER NOT NULL DEFAULT 0,
                file_size_bytes INTEGER NOT NULL DEFAULT 0,
                file_path TEXT DEFAULT NULL,
                content TEXT DEFAULT NULL,
                download_url TEXT DEFAULT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_dataset_id ON reports(dataset_id);")
            conn.commit()

    # ---------------- Users ---------------- #

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        def _get():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,))
                row = cur.fetchone()
                return dict(row) if row else None
        return await asyncio.to_thread(_get)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        def _get():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        return await asyncio.to_thread(_get)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        def _create():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                INSERT INTO users (id, name, email, hashed_password, role, created_at, updated_at)
                VALUES (:id, :name, :email, :hashed_password, :role, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, user_data)
                conn.commit()
                return user_data
        return await asyncio.to_thread(_create)

    # ---------------- Datasets ---------------- #

    async def list_datasets(self) -> List[Dict[str, Any]]:
        def _list():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM datasets ORDER BY uploaded_at DESC")
                rows = cur.fetchall()
                out = []
                for r in rows:
                    d = dict(r)
                    d["capabilities"] = json.loads(d.get("capabilities") or "{}")
                    d["columns"] = json.loads(d.get("columns") or "[]")
                    d["date_range"] = json.loads(d.get("date_range") or "null") if d.get("date_range") else None
                    d["filter_options"] = json.loads(d.get("filter_options") or '{"categories": [], "regions": []}')
                    if d.get("schema_metadata"):
                        d["schema_metadata"] = json.loads(d["schema_metadata"])
                    out.append(d)
                return out
        return await asyncio.to_thread(_list)

    async def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        def _get():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                d["capabilities"] = json.loads(d.get("capabilities") or "{}")
                d["columns"] = json.loads(d.get("columns") or "[]")
                d["date_range"] = json.loads(d.get("date_range") or "null") if d.get("date_range") else None
                d["filter_options"] = json.loads(d.get("filter_options") or '{"categories": [], "regions": []}')
                if d.get("schema_metadata"):
                    d["schema_metadata"] = json.loads(d["schema_metadata"])
                return d
        return await asyncio.to_thread(_get)

    async def create_dataset(self, d: Dict[str, Any]) -> Dict[str, Any]:
        def _insert():
            data = d.copy()
            data["capabilities"] = json.dumps(data.get("capabilities") or {})
            data["columns"] = json.dumps(data.get("columns") or [])
            data["date_range"] = json.dumps(data.get("date_range")) if data.get("date_range") else None
            data["filter_options"] = json.dumps(data.get("filter_options") or {"categories": [], "regions": []})
            data["schema_metadata"] = json.dumps(data.get("schema_metadata")) if data.get("schema_metadata") else None
            
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                INSERT INTO datasets (
                    id, user_id, name, file_name, file_size, status, row_count, column_count,
                    capabilities, columns, date_range, filter_options, error_message,
                    schema_metadata, uploaded_at, started_at
                ) VALUES (
                    :id, :user_id, :name, :file_name, :file_size, :status, :row_count, :column_count,
                    :capabilities, :columns, :date_range, :filter_options, :error_message,
                    :schema_metadata, :uploaded_at, :started_at
                )
                """, data)
                conn.commit()
                return d
        return await asyncio.to_thread(_insert)

    async def update_dataset(self, dataset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        def _update():
            with self._get_connection() as conn:
                cur = conn.cursor()
                set_clauses = []
                params = {"id": dataset_id}
                for k, v in updates.items():
                    if k in ["capabilities", "columns", "date_range", "filter_options", "schema_metadata"]:
                        v_str = json.dumps(v) if v is not None else None
                        set_clauses.append(f"{k} = :{k}")
                        params[k] = v_str
                    else:
                        set_clauses.append(f"{k} = :{k}")
                        params[k] = v
                if not set_clauses:
                    return None
                sql = f"UPDATE datasets SET {', '.join(set_clauses)} WHERE id = :id"
                cur.execute(sql, params)
                conn.commit()
        await asyncio.to_thread(_update)
        return await self.get_dataset(dataset_id)

    async def delete_dataset(self, dataset_id: str) -> bool:
        def _del():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
                conn.commit()
                return cur.rowcount > 0
        return await asyncio.to_thread(_del)

    # ---------------- Dataset Rows ---------------- #

    async def insert_rows(self, dataset_id: str, rows: List[Dict[str, Any]]):
        def _insert():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.executemany("""
                INSERT INTO dataset_rows (
                    id, dataset_id, order_id, transaction_date, product_id, product_name,
                    product_category, region, customer_identifier, quantity, unit_price,
                    revenue, cost, raw_payload
                ) VALUES (
                    :id, :dataset_id, :order_id, :transaction_date, :product_id, :product_name,
                    :product_category, :region, :customer_identifier, :quantity, :unit_price,
                    :revenue, :cost, :raw_payload
                )
                """, rows)
                conn.commit()
        return await asyncio.to_thread(_insert)

    async def get_raw_rows(self, dataset_id: str) -> List[Dict[str, Any]]:
        def _get():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM dataset_rows WHERE dataset_id = ? ORDER BY transaction_date ASC", (dataset_id,))
                rows = cur.fetchall()
                out = []
                for r in rows:
                    d = dict(r)
                    if d.get("raw_payload"):
                        try:
                            d["raw_payload"] = json.loads(d["raw_payload"])
                        except Exception:
                            pass
                    out.append(d)
                return out
        return await asyncio.to_thread(_get)

    async def delete_rows(self, dataset_id: str):
        def _del():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM dataset_rows WHERE dataset_id = ?", (dataset_id,))
                conn.commit()
        return await asyncio.to_thread(_del)

    # ---------------- Reports ---------------- #

    async def create_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        def _insert():
            data = report_data.copy()
            data["parameters"] = json.dumps(data.get("parameters") or {})
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                INSERT INTO reports (
                    id, dataset_id, user_id, title, format, parameters,
                    row_count, file_size_bytes, file_path, content, download_url, created_at
                ) VALUES (
                    :id, :dataset_id, :user_id, :title, :format, :parameters,
                    :row_count, :file_size_bytes, :file_path, :content, :download_url, :created_at
                )
                """, data)
                conn.commit()
                return report_data
        return await asyncio.to_thread(_insert)

    async def list_reports(self, dataset_id: str) -> List[Dict[str, Any]]:
        def _list():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM reports WHERE dataset_id = ? ORDER BY created_at DESC", (dataset_id,))
                rows = cur.fetchall()
                out = []
                for r in rows:
                    d = dict(r)
                    d["parameters"] = json.loads(d.get("parameters") or "{}")
                    out.append(d)
                return out
        return await asyncio.to_thread(_list)

    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        def _get():
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                d["parameters"] = json.loads(d.get("parameters") or "{}")
                return d
        return await asyncio.to_thread(_get)

db = Database(settings.DATABASE_URL)
