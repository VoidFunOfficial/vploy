"""
Token 刷新管理模块

提供自动化的 token 过期检查和告警功能，支持多种 token 类型管理。
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .config_manager import get_config_manager
from ..vlogger import get_logger, AlertLevel


class TokenType(str, Enum):
    """Token 类型枚举"""
    COZE_TOKEN = "coze_token"
    AUTH_TOKEN = "auth_token"
    ACCESS_TOKEN = "access_token"


@dataclass
class TokenConfig:
    """
    Token 配置
    
    属性:
        token_type: Token 类型
        validity_days: 有效期（天）
        description: 描述信息
    """
    token_type: TokenType
    validity_days: int
    description: str


# 默认 Token 配置
DEFAULT_TOKEN_CONFIGS = {
    TokenType.COZE_TOKEN: TokenConfig(
        token_type=TokenType.COZE_TOKEN,
        validity_days=30,
        description="Coze API Token"
    ),
    TokenType.AUTH_TOKEN: TokenConfig(
        token_type=TokenType.AUTH_TOKEN,
        validity_days=7,
        description="认证 Token"
    ),
    TokenType.ACCESS_TOKEN: TokenConfig(
        token_type=TokenType.ACCESS_TOKEN,
        validity_days=1,
        description="访问 Token"
    ),
}


class TokenRefresher:
    """
    Token 刷新管理器
    
    功能：
    - 管理多种类型的 token 及其过期时间
    - 定期检查 token 是否过期
    - 通过 VLogger 发送邮件告警
    - 支持手动标记 token 为过期状态
    """
    
    def __init__(
        self,
        db_path: str = "backend/sys_configs/system_config.db",
        check_interval_minutes: int = 10,
        auto_start: bool = True
    ):
        """
        初始化 Token 刷新管理器
        
        参数:
            db_path: 数据库文件路径
            check_interval_minutes: 检查间隔（分钟），默认 10 分钟
            auto_start: 是否自动启动检查线程，默认 True
        """
        self.db_path = db_path
        self.config_manager = get_config_manager(db_path)
        self.logger = get_logger("TokenRefresher")
        
        # 从配置中读取检查间隔，如果没有则使用传入的参数
        self.check_interval_minutes = self._get_check_interval() or check_interval_minutes
        
        # 后台检查线程
        self._check_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 初始化数据库表
        self._init_tables()
        
        # 初始化默认 token 配置
        self._init_default_configs()
        
        # 自动启动检查线程
        if auto_start:
            self.start()
        
        self.logger.info(
            "TOKEN.REFRESHER.INIT",
            msg="Token 刷新管理器初始化完成",
            extra={
                "check_interval_minutes": self.check_interval_minutes,
                "auto_start": auto_start
            }
        )
    
    def _init_tables(self):
        """初始化数据库表"""
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建 token 配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_configs (
                    token_type TEXT PRIMARY KEY,
                    validity_days INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建 token 状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_status (
                    token_type TEXT PRIMARY KEY,
                    token_value TEXT,
                    expires_at TIMESTAMP NOT NULL,
                    is_expired INTEGER DEFAULT 0,
                    last_checked_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (token_type) REFERENCES token_configs (token_type)
                )
            """)
            
            # 创建 token 刷新配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_refresher_config (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    config_type TEXT DEFAULT 'string',
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
            self.logger.info(
                "TOKEN.REFRESHER.TABLE_INIT",
                msg="Token 刷新管理器数据库表初始化成功"
            )
            
        except Exception as e:
            conn.rollback()
            self.logger.error(
                "TOKEN.REFRESHER.TABLE_INIT_ERROR",
                msg="Token 刷新管理器数据库表初始化失败",
                error_code="E-SYS-004",
                extra={"error": str(e)}
            )
            raise
    
    def _init_default_configs(self):
        """初始化默认 token 配置"""
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()

        try:
            for token_type, config in DEFAULT_TOKEN_CONFIGS.items():
                # 插入 token 配置
                cursor.execute("""
                    INSERT OR IGNORE INTO token_configs (token_type, validity_days, description)
                    VALUES (?, ?, ?)
                """, (token_type.value, config.validity_days, config.description))

                # 为每个 token 类型创建初始状态记录（如果不存在）
                # 默认过期时间设置为当前时间，表示需要更新
                cursor.execute("""
                    INSERT OR IGNORE INTO token_status (
                        token_type,
                        token_value,
                        expires_at,
                        is_expired,
                        last_checked_at
                    )
                    VALUES (?, NULL, datetime('now'), 1, NULL)
                """, (token_type.value,))

            # 初始化默认检查间隔配置
            cursor.execute("""
                INSERT OR IGNORE INTO token_refresher_config (config_key, config_value, config_type, description)
                VALUES ('check_interval_minutes', '10', 'integer', '检查间隔（分钟）')
            """)

            conn.commit()

        except Exception as e:
            conn.rollback()
            self.logger.error(
                "TOKEN.REFRESHER.CONFIG_INIT_ERROR",
                msg="初始化默认 token 配置失败",
                error_code="E-SYS-004",
                extra={"error": str(e)}
            )
    
    def _get_check_interval(self) -> Optional[int]:
        """从数据库读取检查间隔配置"""
        try:
            query = """
                SELECT config_value FROM token_refresher_config
                WHERE config_key = 'check_interval_minutes'
            """
            rows = self.config_manager.execute_query(query)
            if rows:
                return int(rows[0]['config_value'])
        except Exception:
            pass
        return None
    
    def set_check_interval(self, minutes: int) -> bool:
        """
        设置检查间隔
        
        参数:
            minutes: 检查间隔（分钟）
            
        返回:
            bool: 设置是否成功
        """
        try:
            query = """
                INSERT OR REPLACE INTO token_refresher_config (config_key, config_value, config_type, updated_at)
                VALUES ('check_interval_minutes', ?, 'integer', CURRENT_TIMESTAMP)
            """
            self.config_manager.execute_update(query, (str(minutes),))
            
            with self._lock:
                self.check_interval_minutes = minutes
            
            self.logger.info(
                "TOKEN.REFRESHER.INTERVAL_UPDATED",
                msg="检查间隔已更新",
                extra={"check_interval_minutes": minutes}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "TOKEN.REFRESHER.INTERVAL_UPDATE_ERROR",
                msg="更新检查间隔失败",
                error_code="E-SYS-004",
                extra={"error": str(e)}
            )
            return False

    def add_token_type(
        self,
        token_type: str,
        validity_days: int,
        description: str = ""
    ) -> bool:
        """
        添加新的 token 类型配置

        参数:
            token_type: Token 类型名称
            validity_days: 有效期（天）
            description: 描述信息

        返回:
            bool: 添加是否成功
        """
        try:
            query = """
                INSERT INTO token_configs (token_type, validity_days, description)
                VALUES (?, ?, ?)
            """
            self.config_manager.execute_update(query, (token_type, validity_days, description))

            self.logger.info(
                "TOKEN.REFRESHER.TYPE_ADDED",
                msg="添加新的 token 类型",
                extra={
                    "token_type": token_type,
                    "validity_days": validity_days,
                    "description": description
                }
            )

            return True

        except Exception as e:
            self.logger.error(
                "TOKEN.REFRESHER.TYPE_ADD_ERROR",
                msg="添加 token 类型失败",
                error_code="E-SYS-004",
                extra={
                    "token_type": token_type,
                    "error": str(e)
                }
            )
            return False

    def update_token(
        self,
        token_type: str,
        token_value: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        更新 token 信息

        参数:
            token_type: Token 类型
            token_value: Token 值（可选）
            expires_at: 过期时间（可选，如果不提供则根据配置自动计算）

        返回:
            bool: 更新是否成功
        """
        try:
            # 如果没有提供过期时间，根据配置计算
            if expires_at is None:
                query = "SELECT validity_days FROM token_configs WHERE token_type = ?"
                rows = self.config_manager.execute_query(query, (token_type,))
                if not rows:
                    self.logger.warn(
                        "TOKEN.REFRESHER.TYPE_NOT_FOUND",
                        msg="Token 类型不存在",
                        extra={"token_type": token_type}
                    )
                    return False

                validity_days = rows[0]['validity_days']
                expires_at = datetime.now() + timedelta(days=validity_days)

            # 更新或插入 token 状态
            query = """
                INSERT INTO token_status (token_type, token_value, expires_at, is_expired, updated_at)
                VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(token_type) DO UPDATE SET
                    token_value = COALESCE(excluded.token_value, token_value),
                    expires_at = excluded.expires_at,
                    is_expired = 0,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.config_manager.execute_update(
                query,
                (token_type, token_value, expires_at.isoformat())
            )

            self.logger.info(
                "TOKEN.REFRESHER.TOKEN_UPDATED",
                msg="Token 信息已更新",
                extra={
                    "token_type": token_type,
                    "expires_at": expires_at.isoformat(),
                    "has_value": token_value is not None
                }
            )

            return True

        except Exception as e:
            self.logger.error(
                "TOKEN.REFRESHER.TOKEN_UPDATE_ERROR",
                msg="更新 token 信息失败",
                error_code="E-SYS-004",
                extra={
                    "token_type": token_type,
                    "error": str(e)
                }
            )
            return False

    def get_token_status(self, token_type: str) -> Optional[Dict[str, Any]]:
        """
        获取 token 状态

        参数:
            token_type: Token 类型

        返回:
            Optional[Dict]: Token 状态信息，不存在则返回 None
        """
        try:
            query = """
                SELECT token_type, token_value, expires_at, is_expired, last_checked_at
                FROM token_status
                WHERE token_type = ?
            """
            rows = self.config_manager.execute_query(query, (token_type,))

            if not rows:
                return None

            row = rows[0]
            return {
                "token_type": row['token_type'],
                "token_value": row['token_value'],
                "expires_at": row['expires_at'],
                "is_expired": bool(row['is_expired']),
                "last_checked_at": row['last_checked_at']
            }

        except Exception as e:
            self.logger.error(
                "TOKEN.REFRESHER.STATUS_GET_ERROR",
                msg="获取 token 状态失败",
                error_code="E-SYS-004",
                extra={
                    "token_type": token_type,
                    "error": str(e)
                }
            )
            return None

    def set_expired_immediate(self, token_type: str) -> bool:
        """
        立即将 token 标记为过期

        参数:
            token_type: Token 类型

        返回:
            bool: 标记是否成功
        """
        try:
            query = """
                UPDATE token_status
                SET is_expired = 1,
                    expires_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE token_type = ?
            """
            # 将过期时间设置为当前时间
            self.config_manager.execute_update(
                query,
                (datetime.now().isoformat(), token_type)
            )

            self.logger.warn(
                "TOKEN.REFRESHER.TOKEN_EXPIRED_MANUAL",
                msg="Token 已被手动标记为过期",
                extra={"token_type": token_type}
            )

            # 立即发送告警
            self._send_expiry_alert(token_type, manual=True)

            return True

        except Exception as e:
            self.logger.error(
                "TOKEN.REFRESHER.EXPIRE_ERROR",
                msg="标记 token 为过期失败",
                error_code="E-SYS-004",
                extra={
                    "token_type": token_type,
                    "error": str(e)
                }
            )
            return False

    def _send_expiry_alert(self, token_type: str, manual: bool = False):
        """
        发送 token 过期告警

        参数:
            token_type: Token 类型
            manual: 是否为手动标记过期
        """
        # 获取 token 配置信息
        query = "SELECT description FROM token_configs WHERE token_type = ?"
        rows = self.config_manager.execute_query(query, (token_type,))
        description = rows[0]['description'] if rows else token_type

        # 构建告警消息
        if manual:
            msg = f"Token 已被手动标记为过期: {description}"
        else:
            msg = f"Token 已过期，请及时更新: {description}"

        # 使用 ERROR 级别日志触发 P1 告警（邮件即时推送）
        self.logger.error(
            "TOKEN.REFRESHER.TOKEN_EXPIRED",
            msg=msg,
            error_code="E-TOKEN-001",
            extra={
                "token_type": token_type,
                "description": description,
                "manual_expire": manual
            }
        )

    def check_all_tokens(self) -> Dict[str, bool]:
        """
        检查所有 token 的过期状态

        返回:
            Dict[str, bool]: 各 token 类型的过期状态 {token_type: is_expired}
        """
        result = {}

        try:
            query = """
                SELECT token_type, expires_at, is_expired
                FROM token_status
            """
            rows = self.config_manager.execute_query(query)

            current_time = datetime.now()

            for row in rows:
                token_type = row['token_type']
                expires_at = datetime.fromisoformat(row['expires_at'])
                was_expired = bool(row['is_expired'])

                # 检查是否过期
                is_expired = current_time >= expires_at
                result[token_type] = is_expired

                # 如果状态发生变化（从未过期变为过期），发送告警
                if is_expired and not was_expired:
                    # 更新过期状态
                    update_query = """
                        UPDATE token_status
                        SET is_expired = 1,
                            last_checked_at = CURRENT_TIMESTAMP
                        WHERE token_type = ?
                    """
                    self.config_manager.execute_update(update_query, (token_type,))

                    # 发送告警
                    self._send_expiry_alert(token_type)

                    self.logger.warn(
                        "TOKEN.REFRESHER.TOKEN_EXPIRED_DETECTED",
                        msg="检测到 token 已过期",
                        extra={
                            "token_type": token_type,
                            "expires_at": expires_at.isoformat()
                        }
                    )
                else:
                    # 更新最后检查时间
                    update_query = """
                        UPDATE token_status
                        SET last_checked_at = CURRENT_TIMESTAMP
                        WHERE token_type = ?
                    """
                    self.config_manager.execute_update(update_query, (token_type,))

            if result:
                expired_count = sum(1 for is_exp in result.values() if is_exp)
                self.logger.info(
                    "TOKEN.REFRESHER.CHECK_COMPLETED",
                    msg="Token 过期检查完成",
                    extra={
                        "total_tokens": len(result),
                        "expired_tokens": expired_count
                    }
                )

        except Exception as e:
            self.logger.error(
                "TOKEN.REFRESHER.CHECK_ERROR",
                msg="检查 token 过期状态失败",
                error_code="E-SYS-004",
                extra={"error": str(e)}
            )

        return result

    def _check_loop(self):
        """后台检查循环"""
        self.logger.info(
            "TOKEN.REFRESHER.THREAD_STARTED",
            msg="Token 检查线程已启动",
            extra={"check_interval_minutes": self.check_interval_minutes}
        )

        while not self._stop_event.is_set():
            try:
                # 执行检查
                self.check_all_tokens()

                # 等待下一次检查（使用 wait 而不是 sleep，以便能够及时响应停止信号）
                self._stop_event.wait(timeout=self.check_interval_minutes * 60)

            except Exception as e:
                self.logger.error(
                    "TOKEN.REFRESHER.LOOP_ERROR",
                    msg="Token 检查循环发生错误",
                    error_code="E-SYS-001",
                    extra={"error": str(e)}
                )
                # 发生错误后等待一段时间再继续
                self._stop_event.wait(timeout=60)

        self.logger.info(
            "TOKEN.REFRESHER.THREAD_STOPPED",
            msg="Token 检查线程已停止"
        )

    def start(self):
        """启动后台检查线程"""
        with self._lock:
            if self._check_thread is not None and self._check_thread.is_alive():
                self.logger.warn(
                    "TOKEN.REFRESHER.ALREADY_RUNNING",
                    msg="Token 检查线程已在运行中"
                )
                return

            self._stop_event.clear()
            self._check_thread = threading.Thread(
                target=self._check_loop,
                name="TokenRefresherThread",
                daemon=True
            )
            self._check_thread.start()

            self.logger.info(
                "TOKEN.REFRESHER.STARTED",
                msg="Token 刷新管理器已启动"
            )

    def stop(self):
        """停止后台检查线程"""
        with self._lock:
            if self._check_thread is None or not self._check_thread.is_alive():
                self.logger.warn(
                    "TOKEN.REFRESHER.NOT_RUNNING",
                    msg="Token 检查线程未在运行"
                )
                return

            self._stop_event.set()
            self._check_thread.join(timeout=5)

            self.logger.info(
                "TOKEN.REFRESHER.STOPPED",
                msg="Token 刷新管理器已停止"
            )

    def is_running(self) -> bool:
        """
        检查后台线程是否正在运行

        返回:
            bool: 是否正在运行
        """
        with self._lock:
            return self._check_thread is not None and self._check_thread.is_alive()

    def get_all_token_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有 token 的状态

        返回:
            Dict[str, Dict]: 所有 token 的状态信息
        """
        result = {}

        try:
            query = """
                SELECT ts.token_type, ts.token_value, ts.expires_at, ts.is_expired,
                       ts.last_checked_at, tc.validity_days, tc.description
                FROM token_status ts
                LEFT JOIN token_configs tc ON ts.token_type = tc.token_type
            """
            rows = self.config_manager.execute_query(query)

            for row in rows:
                token_type = row['token_type']
                result[token_type] = {
                    "token_value": row['token_value'],
                    "expires_at": row['expires_at'],
                    "is_expired": bool(row['is_expired']),
                    "last_checked_at": row['last_checked_at'],
                    "validity_days": row['validity_days'],
                    "description": row['description']
                }

        except Exception as e:
            self.logger.error(
                "TOKEN.REFRESHER.GET_ALL_STATUS_ERROR",
                msg="获取所有 token 状态失败",
                error_code="E-SYS-004",
                extra={"error": str(e)}
            )

        return result


# 全局 TokenRefresher 实例
_token_refresher: Optional[TokenRefresher] = None
_refresher_lock = threading.Lock()


def get_token_refresher(
    db_path: str = "backend/sys_configs/system_config.db",
    check_interval_minutes: int = 10,
    auto_start: bool = True
) -> TokenRefresher:
    """
    获取 TokenRefresher 实例（单例模式）

    参数:
        db_path: 数据库文件路径
        check_interval_minutes: 检查间隔（分钟）
        auto_start: 是否自动启动

    返回:
        TokenRefresher: TokenRefresher 实例
    """
    global _token_refresher
    if _token_refresher is None:
        with _refresher_lock:
            if _token_refresher is None:
                _token_refresher = TokenRefresher(
                    db_path=db_path,
                    check_interval_minutes=check_interval_minutes,
                    auto_start=auto_start
                )
    return _token_refresher

