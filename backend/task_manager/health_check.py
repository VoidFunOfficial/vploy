"""
健康检查模块

实现API节点延迟检测和统计报告功能。
"""

import time
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..vlogger import get_logger, TraceContext
from .config import get_config


# 初始化日志记录器
logger = get_logger("health_check")


# ==================== 配置 ====================

# API节点列表
API_NODES = [
    "https://clob.polymarket.com/",
    "https://gamma-api.polymarket.com/",
    "https://data-api.polymarket.com/",
    "https://cc01.plusai.io/",
]

# 告警阈值配置
TIMEOUT_THRESHOLD = 5000  # 超时阈值（毫秒）
LATENCY_HIGH_THRESHOLD = 2000  # 延迟过高阈值（毫秒）
LATENCY_WARNING_THRESHOLD = 1000  # 延迟警告阈值（毫秒）
REQUEST_TIMEOUT = 10  # HTTP请求超时时间（秒）

# 数据保留配置
DATA_RETENTION_DAYS = 7  # 数据保留天数


# ==================== 数据模型 ====================

@dataclass
class HealthCheckResult:
    """健康检查结果"""
    node_url: str
    latency_ms: Optional[float]
    status: str  # success, timeout, failed
    error_msg: Optional[str]
    check_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_url": self.node_url,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error_msg": self.error_msg,
            "check_time": self.check_time.isoformat()
        }


@dataclass
class NodeStats:
    """节点统计数据"""
    node_url: str
    avg_latency: float
    max_latency: float
    min_latency: float
    success_rate: float
    total_checks: int
    successful_checks: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_url": self.node_url,
            "avg_latency": round(self.avg_latency, 2),
            "max_latency": round(self.max_latency, 2),
            "min_latency": round(self.min_latency, 2),
            "success_rate": round(self.success_rate * 100, 2),
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks
        }


# ==================== 数据库管理 ====================

class HealthCheckDatabase:
    """健康检查数据库管理器"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器

        参数:
            db_path: 数据库文件路径
        """
        self.db_path = db_path or get_config().db_path
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建健康检查日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_check_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_url TEXT NOT NULL,
                latency_ms REAL,
                status TEXT NOT NULL,
                error_msg TEXT,
                check_time TEXT NOT NULL
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_check_node_time
            ON health_check_logs(node_url, check_time)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_check_time
            ON health_check_logs(check_time)
        """)

        conn.commit()
        conn.close()

        logger.info(
            "HEALTH_CHECK.DB.INIT",
            msg="健康检查数据库初始化完成"
        )

    def save_result(self, result: HealthCheckResult):
        """
        保存检查结果

        参数:
            result: 检查结果
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO health_check_logs (node_url, latency_ms, status, error_msg, check_time)
            VALUES (?, ?, ?, ?, ?)
        """, (
            result.node_url,
            result.latency_ms,
            result.status,
            result.error_msg,
            result.check_time.isoformat()
        ))

        conn.commit()
        conn.close()

    def get_stats(
        self,
        node_url: Optional[str] = None,
        hours: int = 24
    ) -> List[NodeStats]:
        """
        获取节点统计数据

        参数:
            node_url: 节点URL，如果为None则返回所有节点
            hours: 统计时间范围（小时）

        返回:
            List[NodeStats]: 统计数据列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 计算时间范围
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        # 构建查询
        if node_url:
            query = """
                SELECT
                    node_url,
                    AVG(latency_ms) as avg_latency,
                    MAX(latency_ms) as max_latency,
                    MIN(latency_ms) as min_latency,
                    COUNT(*) as total_checks,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_checks
                FROM health_check_logs
                WHERE node_url = ? AND check_time >= ?
                GROUP BY node_url
            """
            cursor.execute(query, (node_url, start_time))
        else:
            query = """
                SELECT
                    node_url,
                    AVG(latency_ms) as avg_latency,
                    MAX(latency_ms) as max_latency,
                    MIN(latency_ms) as min_latency,
                    COUNT(*) as total_checks,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_checks
                FROM health_check_logs
                WHERE check_time >= ?
                GROUP BY node_url
            """
            cursor.execute(query, (start_time,))

        rows = cursor.fetchall()
        conn.close()

        stats_list = []
        for row in rows:
            stats = NodeStats(
                node_url=row["node_url"],
                avg_latency=row["avg_latency"] or 0,
                max_latency=row["max_latency"] or 0,
                min_latency=row["min_latency"] or 0,
                total_checks=row["total_checks"],
                successful_checks=row["successful_checks"] or 0,
                success_rate=(row["successful_checks"] or 0) / row["total_checks"] if row["total_checks"] > 0 else 0
            )
            stats_list.append(stats)

        return stats_list

    def cleanup_old_data(self, days: int = DATA_RETENTION_DAYS):
        """
        清理旧数据

        参数:
            days: 保留天数
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            DELETE FROM health_check_logs
            WHERE check_time < ?
        """, (cutoff_time,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(
                "HEALTH_CHECK.CLEANUP",
                msg=f"清理旧数据完成，删除 {deleted_count} 条记录",
                extra={"deleted_count": deleted_count, "days": days}
            )

        return deleted_count


# 全局数据库实例
_db: Optional[HealthCheckDatabase] = None


def get_db() -> HealthCheckDatabase:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = HealthCheckDatabase()
    return _db


# ==================== 节点检测 ====================

def _check_node(node_url: str) -> HealthCheckResult:
    """检测单个节点的延迟（内部函数）"""
    check_time = datetime.now()

    try:
        start_time = time.time()
        response = requests.get(
            node_url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "VoidPoly-HealthCheck/1.0"}
        )
        latency_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            status = "success"
            error_msg = None
        else:
            status = "failed"
            error_msg = f"HTTP {response.status_code}"

        result = HealthCheckResult(
            node_url=node_url,
            latency_ms=latency_ms,
            status=status,
            error_msg=error_msg,
            check_time=check_time
        )

    except requests.exceptions.Timeout:
        result = HealthCheckResult(
            node_url=node_url,
            latency_ms=REQUEST_TIMEOUT * 1000,
            status="timeout",
            error_msg=f"请求超时 (>{REQUEST_TIMEOUT}s)",
            check_time=check_time
        )

    except Exception as e:
        result = HealthCheckResult(
            node_url=node_url,
            latency_ms=None,
            status="failed",
            error_msg=str(e),
            check_time=check_time
        )

    return result


def check_all_nodes() -> List[HealthCheckResult]:
    """
    检测所有节点

    返回:
        List[HealthCheckResult]: 所有节点的检测结果
    """
    with TraceContext() as trace_id:
        logger.info(
            "HEALTH_CHECK.CHECK_ALL.START",
            msg="开始检测所有API节点",
            extra={"node_count": len(API_NODES)},
            trace_id=trace_id
        )

        results = []
        for node_url in API_NODES:
            result = _check_node(node_url)
            results.append(result)

            # 保存到数据库
            db = get_db()
            db.save_result(result)

        logger.info(
            "HEALTH_CHECK.CHECK_ALL.COMPLETE",
            msg="所有节点检测完成",
            extra={
                "total": len(results),
                "success": sum(1 for r in results if r.status == "success"),
                "timeout": sum(1 for r in results if r.status == "timeout"),
                "failed": sum(1 for r in results if r.status == "failed")
            },
            trace_id=trace_id
        )

        return results



# ==================== 统计报告 ====================

def get_health_report(hours_12: bool = True, hours_72: bool = True) -> Dict[str, Any]:
    """
    获取健康检查报告

    参数:
        hours_12: 是否包含近12小时统计
        hours_72: 是否包含近3天统计

    返回:
        Dict[str, Any]: 报告数据
    """
    db = get_db()
    report = {}

    if hours_12:
        stats_12h = db.get_stats(hours=12)
        report["12_hours"] = {
            "period": "近12小时",
            "nodes": [stat.to_dict() for stat in stats_12h]
        }

    if hours_72:
        stats_72h = db.get_stats(hours=72)
        report["72_hours"] = {
            "period": "近3天",
            "nodes": [stat.to_dict() for stat in stats_72h]
        }

    report["generated_at"] = datetime.now().isoformat()

    return report
