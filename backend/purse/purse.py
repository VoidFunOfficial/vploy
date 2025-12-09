"""
Purse - 本地钱包管理模块

基于SQLite实现的单例模式钱包管理系统，提供：
- 全局单例模式访问
- SQLite数据库持久化存储
- 线程安全的资金操作
- 事务支持确保数据一致性
- VLogger日志系统集成

使用示例:
    >>> from backend.purse.purse import Purse
    >>> purse = Purse.get_instance()
    >>> purse.initialize(total_fund=10000.0)
    >>> purse.lock_fund(100.0)
    >>> status = purse.get_status()
"""

import sqlite3
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager

# 导入VLogger日志系统
try:
    from backend.vlogger import get_logger
except ImportError:
    from vlogger import get_logger


class Purse:
    """
    钱包管理类 - 单例模式

    管理本地钱包的所有资金状态，包括：
    - 总资金(total_fund)
    - 锁定资金(locked_fund)
    - 可用现金(available_cash)
    - 总亏损(loss)
    - 预期盈利(expect_profit)
    - 实际盈利(real_profit)
    - 成功市场数(success_market)
    - 失败市场数(lost_market)
    """

    _instance: Optional['Purse'] = None
    _lock = threading.Lock()  # 线程锁，确保单例模式的线程安全

    def __init__(self, db_path: str = "purse.db"):
        """
        初始化钱包管理器

        参数:
            db_path: SQLite数据库文件路径
        """
        if Purse._instance is not None:
            raise RuntimeError("Purse是单例类，请使用Purse.get_instance()获取实例")

        self.db_path = db_path
        self.logger = get_logger("purse")
        self._db_lock = threading.Lock()  # 数据库操作锁

        # 初始化数据库
        self._init_database()

        self.logger.info(
            "PURSE.INIT",
            msg="钱包管理器初始化成功",
            extra={"db_path": self.db_path}
        )

    @classmethod
    def get_instance(cls, db_path: str = "purse.db") -> 'Purse':
        """
        获取Purse单例实例（线程安全）

        参数:
            db_path: SQLite数据库文件路径

        返回:
            Purse: 钱包管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接的上下文管理器

        使用示例:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
                conn.commit()
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            self.logger.error(
                "PURSE.DB.ERROR",
                msg="数据库操作失败",
                error_code="E-PURSE-001",
                extra={"error": str(e)}
            )
            raise
        finally:
            conn.close()

    def _init_database(self):
        """
        初始化数据库表结构

        创建purse_status表和daily_profit_records表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 创建钱包状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS purse_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_fund REAL NOT NULL DEFAULT 0.0,
                    locked_fund REAL NOT NULL DEFAULT 0.0,
                    available_cash REAL NOT NULL DEFAULT 0.0,
                    loss REAL NOT NULL DEFAULT 0.0,
                    expect_profit REAL NOT NULL DEFAULT 0.0,
                    real_profit REAL NOT NULL DEFAULT 0.0,
                    success_market INTEGER NOT NULL DEFAULT 0,
                    lost_market INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 检查是否已有记录，如果没有则插入初始记录
            cursor.execute("SELECT COUNT(*) as count FROM purse_status WHERE id = 1")
            if cursor.fetchone()['count'] == 0:
                cursor.execute("""
                    INSERT INTO purse_status (
                        id, total_fund, locked_fund, available_cash,
                        loss, expect_profit, real_profit,
                        success_market, lost_market
                    ) VALUES (1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)
                """)

            # 创建每日收益记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_profit_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_date DATE NOT NULL UNIQUE,
                    expect_profit REAL NOT NULL DEFAULT 0.0,
                    real_profit REAL NOT NULL DEFAULT 0.0,
                    total_fund REAL NOT NULL DEFAULT 0.0,
                    success_market INTEGER NOT NULL DEFAULT 0,
                    lost_market INTEGER NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建日期索引以提高查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_record_date
                ON daily_profit_records(record_date)
            """)

            conn.commit()

        self.logger.info(
            "PURSE.DB.INIT",
            msg="数据库初始化完成",
            extra={"db_path": self.db_path}
        )

    def initialize(self, total_fund: float) -> bool:
        """
        初始化钱包总资金

        参数:
            total_fund: 初始投入资金

        返回:
            bool: 操作是否成功
        """
        if total_fund < 0:
            self.logger.error(
                "PURSE.INIT.INVALID",
                msg="初始资金不能为负数",
                error_code="E-PURSE-002",
                extra={"total_fund": total_fund}
            )
            return False

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE purse_status
                    SET total_fund = ?,
                        available_cash = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (total_fund, total_fund))
                conn.commit()

        self.logger.info(
            "PURSE.INIT.SUCCESS",
            msg="钱包初始化成功",
            extra={"total_fund": total_fund}
        )
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        获取钱包当前状态

        返回:
            dict: 包含所有钱包状态字段的字典
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT total_fund, locked_fund, available_cash,
                           loss, expect_profit, real_profit,
                           success_market, lost_market, updated_at
                    FROM purse_status WHERE id = 1
                """)
                row = cursor.fetchone()

                if row is None:
                    return {}

                status = {
                    "total_fund": row['total_fund'],
                    "locked_fund": row['locked_fund'],
                    "available_cash": row['available_cash'],
                    "loss": row['loss'],
                    "expect_profit": row['expect_profit'],
                    "real_profit": row['real_profit'],
                    "success_market": row['success_market'],
                    "lost_market": row['lost_market'],
                    "updated_at": row['updated_at']
                }

        self.logger.debug(
            "PURSE.STATUS.QUERY",
            msg="查询钱包状态",
            extra=status
        )
        return status

    def lock_fund(self, amount: float) -> bool:
        """
        锁定资金（用于下注）

        参数:
            amount: 要锁定的金额

        返回:
            bool: 操作是否成功
        """
        if amount <= 0:
            self.logger.error(
                "PURSE.LOCK.INVALID",
                msg="锁定金额必须大于0",
                error_code="E-PURSE-003",
                extra={"amount": amount}
            )
            return False

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 检查可用资金是否足够
                cursor.execute("SELECT available_cash FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                available = row['available_cash']

                if available < amount:
                    self.logger.error(
                        "PURSE.LOCK.INSUFFICIENT",
                        msg="可用资金不足",
                        error_code="E-PURSE-004",
                        extra={"available": available, "required": amount}
                    )
                    return False

                # 锁定资金
                cursor.execute("""
                    UPDATE purse_status
                    SET locked_fund = locked_fund + ?,
                        available_cash = available_cash - ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount, amount))
                conn.commit()

        self.logger.info(
            "PURSE.LOCK.SUCCESS",
            msg="资金锁定成功",
            extra={"amount": amount}
        )
        return True

    def unlock_fund(self, amount: float) -> bool:
        """
        解锁资金（取消下注或订单完成）

        参数:
            amount: 要解锁的金额

        返回:
            bool: 操作是否成功
        """
        if amount <= 0:
            self.logger.error(
                "PURSE.UNLOCK.INVALID",
                msg="解锁金额必须大于0",
                error_code="E-PURSE-005",
                extra={"amount": amount}
            )
            return False

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 检查锁定资金是否足够
                cursor.execute("SELECT locked_fund FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                locked = row['locked_fund']

                if locked < amount:
                    self.logger.error(
                        "PURSE.UNLOCK.INSUFFICIENT",
                        msg="锁定资金不足",
                        error_code="E-PURSE-006",
                        extra={"locked": locked, "required": amount}
                    )
                    return False

                # 解锁资金
                cursor.execute("""
                    UPDATE purse_status
                    SET locked_fund = locked_fund - ?,
                        available_cash = available_cash + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount, amount))
                conn.commit()

        self.logger.info(
            "PURSE.UNLOCK.SUCCESS",
            msg="资金解锁成功",
            extra={"amount": amount}
        )
        return True

    def record_profit(self, amount: float, unlock_amount: float) -> bool:
        """
        记录实际盈利（订单结算后）

        参数:
            amount: 盈利金额
            unlock_amount: 需要解锁的本金金额

        返回:
            bool: 操作是否成功
        """
        if unlock_amount <= 0:
            self.logger.error(
                "PURSE.PROFIT.INVALID",
                msg="解锁金额必须大于0",
                error_code="E-PURSE-007",
                extra={"unlock_amount": unlock_amount}
            )
            return False

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 检查锁定资金是否足够
                cursor.execute("SELECT locked_fund FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                locked = row['locked_fund']

                if locked < unlock_amount:
                    self.logger.error(
                        "PURSE.PROFIT.INSUFFICIENT",
                        msg="锁定资金不足",
                        error_code="E-PURSE-008",
                        extra={"locked": locked, "required": unlock_amount}
                    )
                    return False

                # 记录盈利并解锁资金
                cursor.execute("""
                    UPDATE purse_status
                    SET real_profit = real_profit + ?,
                        locked_fund = locked_fund - ?,
                        available_cash = available_cash + ? + ?,
                        total_fund = total_fund + ?,
                        success_market = success_market + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount, unlock_amount, unlock_amount, amount, amount))
                conn.commit()

        self.logger.trade(
            "PURSE.PROFIT.RECORD",
            msg="记录盈利成功",
            extra={"profit": amount, "unlock_amount": unlock_amount}
        )
        return True

    def record_loss(self, amount: float, unlock_amount: float) -> bool:
        """
        记录亏损（订单结算后）

        参数:
            amount: 亏损金额（正数）
            unlock_amount: 需要解锁的剩余本金金额

        返回:
            bool: 操作是否成功
        """
        if amount < 0:
            self.logger.error(
                "PURSE.LOSS.INVALID",
                msg="亏损金额不能为负数",
                error_code="E-PURSE-009",
                extra={"amount": amount}
            )
            return False

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 检查锁定资金是否足够
                cursor.execute("SELECT locked_fund FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                locked = row['locked_fund']

                if locked < unlock_amount:
                    self.logger.error(
                        "PURSE.LOSS.INSUFFICIENT",
                        msg="锁定资金不足",
                        error_code="E-PURSE-010",
                        extra={"locked": locked, "required": unlock_amount}
                    )
                    return False

                # 记录亏损并解锁剩余资金
                cursor.execute("""
                    UPDATE purse_status
                    SET loss = loss + ?,
                        locked_fund = locked_fund - ?,
                        available_cash = available_cash + ?,
                        total_fund = total_fund - ?,
                        lost_market = lost_market + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount, unlock_amount, unlock_amount, amount))
                conn.commit()

        self.logger.trade(
            "PURSE.LOSS.RECORD",
            msg="记录亏损成功",
            extra={"loss": amount, "unlock_amount": unlock_amount}
        )
        return True

    def update_expect_profit(self, amount: float) -> bool:
        """
        更新预期盈利（未结算订单的潜在盈利）

        参数:
            amount: 预期盈利金额（可以为负数表示减少）

        返回:
            bool: 操作是否成功
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE purse_status
                    SET expect_profit = expect_profit + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount,))
                conn.commit()

        self.logger.debug(
            "PURSE.EXPECT.UPDATE",
            msg="更新预期盈利",
            extra={"amount": amount}
        )
        return True

    def set_expect_profit(self, amount: float) -> bool:
        """
        设置预期盈利（直接设置值，而非增量更新）

        参数:
            amount: 预期盈利金额

        返回:
            bool: 操作是否成功
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE purse_status
                    SET expect_profit = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount,))
                conn.commit()

        self.logger.debug(
            "PURSE.EXPECT.SET",
            msg="设置预期盈利",
            extra={"amount": amount}
        )
        return True

    def get_available_cash(self) -> float:
        """
        获取当前可用现金

        返回:
            float: 可用现金金额
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT available_cash FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                return row['available_cash'] if row else 0.0

    def get_total_fund(self) -> float:
        """
        获取总资金

        返回:
            float: 总资金金额
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT total_fund FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                return row['total_fund'] if row else 0.0

    def get_locked_fund(self) -> float:
        """
        获取锁定资金

        返回:
            float: 锁定资金金额
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT locked_fund FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                return row['locked_fund'] if row else 0.0

    def get_profit_loss_summary(self) -> Dict[str, Any]:
        """
        获取盈亏汇总信息

        返回:
            dict: 包含盈亏统计的字典
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT loss, expect_profit, real_profit,
                           success_market, lost_market
                    FROM purse_status WHERE id = 1
                """)
                row = cursor.fetchone()

                if row is None:
                    return {}

                total_markets = row['success_market'] + row['lost_market']
                win_rate = (row['success_market'] / total_markets * 100) if total_markets > 0 else 0.0

                summary = {
                    "loss": row['loss'],
                    "expect_profit": row['expect_profit'],
                    "real_profit": row['real_profit'],
                    "net_profit": row['real_profit'] - row['loss'],
                    "success_market": row['success_market'],
                    "lost_market": row['lost_market'],
                    "total_market": total_markets,
                    "win_rate": round(win_rate, 2)
                }

        return summary

    def reset(self) -> bool:
        """
        重置钱包状态（清空所有数据）

        警告: 此操作会清空所有钱包数据，请谨慎使用！

        返回:
            bool: 操作是否成功
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE purse_status
                    SET total_fund = 0.0,
                        locked_fund = 0.0,
                        available_cash = 0.0,
                        loss = 0.0,
                        expect_profit = 0.0,
                        real_profit = 0.0,
                        success_market = 0,
                        lost_market = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """)
                conn.commit()

        self.logger.warn(
            "PURSE.RESET",
            msg="钱包已重置",
            error_code="E-PURSE-011"
        )
        return True

    def add_fund(self, amount: float) -> bool:
        """
        追加资金（增加总资金和可用现金）

        参数:
            amount: 追加的资金金额

        返回:
            bool: 操作是否成功
        """
        if amount <= 0:
            self.logger.error(
                "PURSE.ADD.INVALID",
                msg="追加资金必须大于0",
                error_code="E-PURSE-012",
                extra={"amount": amount}
            )
            return False

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE purse_status
                    SET total_fund = total_fund + ?,
                        available_cash = available_cash + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount, amount))
                conn.commit()

        self.logger.info(
            "PURSE.ADD.SUCCESS",
            msg="追加资金成功",
            extra={"amount": amount}
        )
        return True

    def withdraw_fund(self, amount: float) -> bool:
        """
        提取资金（减少总资金和可用现金）

        参数:
            amount: 提取的资金金额

        返回:
            bool: 操作是否成功
        """
        if amount <= 0:
            self.logger.error(
                "PURSE.WITHDRAW.INVALID",
                msg="提取资金必须大于0",
                error_code="E-PURSE-013",
                extra={"amount": amount}
            )
            return False

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 检查可用资金是否足够
                cursor.execute("SELECT available_cash FROM purse_status WHERE id = 1")
                row = cursor.fetchone()
                available = row['available_cash']

                if available < amount:
                    self.logger.error(
                        "PURSE.WITHDRAW.INSUFFICIENT",
                        msg="可用资金不足",
                        error_code="E-PURSE-014",
                        extra={"available": available, "required": amount}
                    )
                    return False

                # 提取资金
                cursor.execute("""
                    UPDATE purse_status
                    SET total_fund = total_fund - ?,
                        available_cash = available_cash - ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (amount, amount))
                conn.commit()

        self.logger.info(
            "PURSE.WITHDRAW.SUCCESS",
            msg="提取资金成功",
            extra={"amount": amount}
        )
        return True

    def update_status(self, **kwargs) -> bool:
        """
        更新钱包状态字段（直接设置值）

        参数:
            **kwargs: 要更新的字段和值，支持的字段包括:
                - total_fund: 总资金
                - locked_fund: 锁定资金
                - available_cash: 可用现金
                - loss: 总亏损
                - expect_profit: 预期盈利
                - real_profit: 实际盈利
                - success_market: 成功市场数
                - lost_market: 失败市场数

        返回:
            bool: 操作是否成功
        """
        # 允许更新的字段列表
        allowed_fields = {
            'total_fund', 'locked_fund', 'available_cash',
            'loss', 'expect_profit', 'real_profit',
            'success_market', 'lost_market'
        }

        # 过滤出有效的字段
        update_fields = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                update_fields[key] = value
            else:
                self.logger.warn(
                    "PURSE.UPDATE.INVALID_FIELD",
                    msg=f"忽略无效字段: {key}",
                    extra={"field": key}
                )

        if not update_fields:
            self.logger.warn(
                "PURSE.UPDATE.NO_FIELDS",
                msg="没有提供有效的更新字段"
            )
            return False

        # 构建SQL更新语句
        set_clauses = [f"{field} = ?" for field in update_fields.keys()]
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values = list(update_fields.values())

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                sql = f"""
                    UPDATE purse_status
                    SET {', '.join(set_clauses)}
                    WHERE id = 1
                """
                cursor.execute(sql, values)
                conn.commit()

        self.logger.info(
            "PURSE.UPDATE.SUCCESS",
            msg="钱包状态更新成功",
            extra=update_fields
        )
        return True

    # ==================== 每日收益记录管理 ====================

    def add_daily_record(self, record_date: str, expect_profit: float,
                        real_profit: float, total_fund: float = None,
                        success_market: int = None, lost_market: int = None,
                        notes: str = None) -> bool:
        """
        添加每日收益记录

        参数:
            record_date: 记录日期 (格式: YYYY-MM-DD)
            expect_profit: 预期收益
            real_profit: 实际收益
            total_fund: 总资金 (可选,默认使用当前总资金)
            success_market: 成功市场数 (可选,默认使用当前值)
            lost_market: 失败市场数 (可选,默认使用当前值)
            notes: 备注 (可选)

        返回:
            bool: 操作是否成功
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 如果未提供可选参数,从当前状态获取
                if total_fund is None or success_market is None or lost_market is None:
                    cursor.execute("""
                        SELECT total_fund, success_market, lost_market
                        FROM purse_status WHERE id = 1
                    """)
                    row = cursor.fetchone()
                    if total_fund is None:
                        total_fund = row['total_fund']
                    if success_market is None:
                        success_market = row['success_market']
                    if lost_market is None:
                        lost_market = row['lost_market']

                try:
                    cursor.execute("""
                        INSERT INTO daily_profit_records
                        (record_date, expect_profit, real_profit, total_fund,
                         success_market, lost_market, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (record_date, expect_profit, real_profit, total_fund,
                          success_market, lost_market, notes))
                    conn.commit()

                    self.logger.info(
                        "PURSE.DAILY.ADD",
                        msg="添加每日收益记录成功",
                        extra={
                            "date": record_date,
                            "expect_profit": expect_profit,
                            "real_profit": real_profit
                        }
                    )
                    return True

                except sqlite3.IntegrityError:
                    self.logger.error(
                        "PURSE.DAILY.ADD.DUPLICATE",
                        msg="该日期的记录已存在",
                        error_code="E-PURSE-015",
                        extra={"date": record_date}
                    )
                    return False

    def update_daily_record(self, record_date: str, expect_profit: float = None,
                           real_profit: float = None, total_fund: float = None,
                           success_market: int = None, lost_market: int = None,
                           notes: str = None) -> bool:
        """
        更新每日收益记录

        参数:
            record_date: 记录日期 (格式: YYYY-MM-DD)
            expect_profit: 预期收益 (可选)
            real_profit: 实际收益 (可选)
            total_fund: 总资金 (可选)
            success_market: 成功市场数 (可选)
            lost_market: 失败市场数 (可选)
            notes: 备注 (可选)

        返回:
            bool: 操作是否成功
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 构建更新语句
                update_fields = []
                update_values = []

                if expect_profit is not None:
                    update_fields.append("expect_profit = ?")
                    update_values.append(expect_profit)
                if real_profit is not None:
                    update_fields.append("real_profit = ?")
                    update_values.append(real_profit)
                if total_fund is not None:
                    update_fields.append("total_fund = ?")
                    update_values.append(total_fund)
                if success_market is not None:
                    update_fields.append("success_market = ?")
                    update_values.append(success_market)
                if lost_market is not None:
                    update_fields.append("lost_market = ?")
                    update_values.append(lost_market)
                if notes is not None:
                    update_fields.append("notes = ?")
                    update_values.append(notes)

                if not update_fields:
                    self.logger.warn(
                        "PURSE.DAILY.UPDATE.NOFIELDS",
                        msg="没有提供要更新的字段"
                    )
                    return False

                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(record_date)

                sql = f"""
                    UPDATE daily_profit_records
                    SET {', '.join(update_fields)}
                    WHERE record_date = ?
                """

                cursor.execute(sql, update_values)

                if cursor.rowcount == 0:
                    self.logger.error(
                        "PURSE.DAILY.UPDATE.NOTFOUND",
                        msg="未找到该日期的记录",
                        error_code="E-PURSE-016",
                        extra={"date": record_date}
                    )
                    return False

                conn.commit()

                self.logger.info(
                    "PURSE.DAILY.UPDATE",
                    msg="更新每日收益记录成功",
                    extra={"date": record_date}
                )
                return True

    def delete_daily_record(self, record_date: str) -> bool:
        """
        删除每日收益记录

        参数:
            record_date: 记录日期 (格式: YYYY-MM-DD)

        返回:
            bool: 操作是否成功
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM daily_profit_records
                    WHERE record_date = ?
                """, (record_date,))

                if cursor.rowcount == 0:
                    self.logger.error(
                        "PURSE.DAILY.DELETE.NOTFOUND",
                        msg="未找到该日期的记录",
                        error_code="E-PURSE-017",
                        extra={"date": record_date}
                    )
                    return False

                conn.commit()

                self.logger.info(
                    "PURSE.DAILY.DELETE",
                    msg="删除每日收益记录成功",
                    extra={"date": record_date}
                )
                return True

    def get_daily_record(self, record_date: str) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的收益记录

        参数:
            record_date: 记录日期 (格式: YYYY-MM-DD)

        返回:
            dict: 收益记录数据,如果不存在则返回None
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT record_date, expect_profit, real_profit, total_fund,
                           success_market, lost_market, notes,
                           created_at, updated_at
                    FROM daily_profit_records
                    WHERE record_date = ?
                """, (record_date,))
                row = cursor.fetchone()

                if row is None:
                    return None

                return {
                    "record_date": row['record_date'],
                    "expect_profit": row['expect_profit'],
                    "real_profit": row['real_profit'],
                    "total_fund": row['total_fund'],
                    "success_market": row['success_market'],
                    "lost_market": row['lost_market'],
                    "notes": row['notes'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                }

    def get_daily_records(self, start_date: str = None, end_date: str = None,
                         limit: int = None) -> list:
        """
        获取每日收益记录列表

        参数:
            start_date: 开始日期 (格式: YYYY-MM-DD, 可选)
            end_date: 结束日期 (格式: YYYY-MM-DD, 可选)
            limit: 返回记录数量限制 (可选)

        返回:
            list: 收益记录列表,按日期降序排列
        """
        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 构建查询条件
                where_clauses = []
                params = []

                if start_date:
                    where_clauses.append("record_date >= ?")
                    params.append(start_date)
                if end_date:
                    where_clauses.append("record_date <= ?")
                    params.append(end_date)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
                limit_sql = f"LIMIT {limit}" if limit else ""

                sql = f"""
                    SELECT record_date, expect_profit, real_profit, total_fund,
                           success_market, lost_market, notes,
                           created_at, updated_at
                    FROM daily_profit_records
                    {where_sql}
                    ORDER BY record_date DESC
                    {limit_sql}
                """

                cursor.execute(sql, params)
                rows = cursor.fetchall()

                records = []
                for row in rows:
                    records.append({
                        "record_date": row['record_date'],
                        "expect_profit": row['expect_profit'],
                        "real_profit": row['real_profit'],
                        "total_fund": row['total_fund'],
                        "success_market": row['success_market'],
                        "lost_market": row['lost_market'],
                        "notes": row['notes'],
                        "created_at": row['created_at'],
                        "updated_at": row['updated_at']
                    })

                return records


# 便捷函数：获取全局Purse实例
def get_purse(db_path: str = "purse.db") -> Purse:
    """
    获取全局Purse实例的便捷函数

    参数:
        db_path: SQLite数据库文件路径

    返回:
        Purse: 钱包管理器实例
    """
    return Purse.get_instance(db_path)
