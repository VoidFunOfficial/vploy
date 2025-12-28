import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.sys_configs.global_event_reg import vlogger

DB_PATH = "record.db"

class RecordDBManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize database tables"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # Operations table
                # Storing history of operations. 
                # Although the prompt mentioned "update or insert with market_id as primary key",
                # the requirement for "history" and "get_info returning list" necessitates a separate ID.
                # We will index market_id for fast lookups.
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        market_id TEXT NOT NULL,
                        side TEXT NOT NULL,
                        end_date TEXT,
                        operation TEXT NOT NULL,
                        price REAL NOT NULL,
                        amount REAL NOT NULL,
                        tips TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check if tau_data column exists and rename it if necessary (Migration)
                try:
                    cursor.execute("PRAGMA table_info(operations)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'tau_data' in columns and 'end_date' not in columns:
                        vlogger.info("RECORD.DB.MIGRATE", msg="Migrating tau_data to end_date")
                        cursor.execute("ALTER TABLE operations RENAME COLUMN tau_data TO end_date")
                except Exception as e:
                    vlogger.warn("RECORD.DB.MIGRATE_WARN", msg="Migration check failed (safe to ignore if new db)", extra={"error": str(e)})

                # Index for market_id
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_operations_market_id ON operations(market_id)
                """)

                # Daily Summary table
                # Fields:
                #   update_count: Number of operations today
                #   new_invest: Number of markets recorded today
                #   profit_today: Total unrealized profit (currency)
                #   settled_today: Number of markets settled today
                #   locked_amount: Current locked funds (currency)
                #   available_amount: Current available funds (currency)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_summary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL UNIQUE,
                        update_count INTEGER DEFAULT 0,
                        new_invest REAL DEFAULT 0,
                        profit_today REAL DEFAULT 0,
                        settled_today REAL DEFAULT 0,
                        locked_amount REAL DEFAULT 0,
                        available_amount REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
        except Exception as e:
            vlogger.error("RECORD.DB.INIT_ERROR", msg="Failed to initialize record database", extra={"error": str(e)})
            raise

    def add_operation(self, market_id: str, side: str, end_date: str, operation: str, price: float, amount: float, tips: str = ""):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO operations (market_id, side, end_date, operation, price, amount, tips)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (market_id, side, end_date, operation, price, amount, tips))
                conn.commit()
            
            vlogger.info("RECORD.OP.ADD", msg="Operation recorded", extra={
                "market_id": market_id,
                "operation": operation,
                "amount": amount
            })
        except Exception as e:
            vlogger.error("RECORD.OP.ADD_ERROR", msg="Failed to add operation", extra={
                "market_id": market_id,
                "error": str(e)
            })
            raise

    def get_operations(self, market_id: str) -> List[Dict]:
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM operations WHERE market_id = ? ORDER BY created_at ASC
                """, (market_id,))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    item = dict(row)
                    # No longer need to parse JSON for end_date as it is TEXT
                    # Keep backward compatibility if some rows still have JSON from tau_data before migration (unlikely with rename)
                    # But if we renamed column, the data is still TEXT. If it was JSON string, it is still JSON string.
                    # Ideally we assume new data is yyyy-mm-dd string.
                    results.append(item)
                return results
        except Exception as e:
            vlogger.error("RECORD.OP.GET_ERROR", msg="Failed to get operations", extra={
                "market_id": market_id,
                "error": str(e)
            })
            return []

    def get_all_market_ids(self) -> List[str]:
        """Get all unique market IDs from operations"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT market_id FROM operations")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            vlogger.error("RECORD.DB.GET_IDS_ERROR", msg="Failed to get all market IDs", extra={"error": str(e)})
            return []

    def add_daily_summary(self, update_data: int, new_invest: float, profit_today: float, settled_today: float, locked_amount: float, available_amount: float):
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                # Use REPLACE to update if exists for today, or INSERT
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_summary (date, update_count, new_invest, profit_today, settled_today, locked_amount, available_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (today, update_data, new_invest, profit_today, settled_today, locked_amount, available_amount))
                conn.commit()

            vlogger.info("RECORD.DAILY.ADD", msg="Daily summary recorded", extra={
                "date": today,
                "profit": profit_today
            })
        except Exception as e:
            vlogger.error("RECORD.DAILY.ADD_ERROR", msg="Failed to record daily summary", extra={"error": str(e)})
            raise

    def get_daily_summary(self, date: str) -> Optional[Dict]:
        """Get daily summary for a specific date"""
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM daily_summary WHERE date = ?
                """, (date,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            vlogger.error("RECORD.DAILY.GET_ERROR", msg="Failed to get daily summary", extra={
                "date": date,
                "error": str(e)
            })
            return None

    def get_operations_by_date(self, date: str) -> List[Dict]:
        """Get all operations for a specific date (based on created_at)"""
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM operations
                    WHERE DATE(created_at) = ?
                    ORDER BY created_at ASC
                """, (date,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            vlogger.error("RECORD.OP.GET_BY_DATE_ERROR", msg="Failed to get operations by date", extra={
                "date": date,
                "error": str(e)
            })
            return []

    def get_settle_operations_by_date(self, date: str) -> List[Dict]:
        """Get all SETTLE operations for a specific date"""
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM operations
                    WHERE operation = 'SETTLE' AND DATE(created_at) = ?
                    ORDER BY created_at ASC
                """, (date,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            vlogger.error("RECORD.OP.GET_SETTLE_ERROR", msg="Failed to get settle operations", extra={
                "date": date,
                "error": str(e)
            })
            return []
