"""
任务管理器数据模型

定义异步任务和定时任务的数据模型，使用SQLite存储。
"""

import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from .config import get_config


class TaskStage(str, Enum):
    """任务阶段枚举"""
    MARK = "mark"           # 标记阶段
    ANALYSIS = "analysis"   # 分析阶段
    DECISION = "decision"   # 决策阶段
    TRADE = "trade"         # 交易阶段
    LISTEN = "listen"       # 监听阶段


class TaskStatus(str, Enum):
    """任务状态枚举"""
    WAITING = "waiting"         # 等待中
    PROCESSING = "processing"   # 处理中
    FINISHED = "finished"       # 已完成
    FAILED = "failed"           # 失败


class AsyncTask:
    """
    异步任务模型

    属性:
        id: 任务ID（自增主键）
        stage: 任务阶段
        status: 任务状态
        metadata: 任务元数据（JSON格式）
        result: 任务执行结果（JSON格式）
        error_msg: 错误信息
        create_time: 创建时间
        update_time: 更新时间
    """

    def __init__(
        self,
        id: Optional[int] = None,
        stage: TaskStage = TaskStage.MARK,
        status: TaskStatus = TaskStatus.WAITING,
        metadata: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error_msg: Optional[str] = None,
        create_time: Optional[datetime] = None,
        update_time: Optional[datetime] = None
    ):
        self.id = id
        self.stage = stage if isinstance(stage, TaskStage) else TaskStage(stage)
        self.status = status if isinstance(status, TaskStatus) else TaskStatus(status)
        self.metadata = metadata or {}
        self.result = result or {}
        self.error_msg = error_msg
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "stage": self.stage.value,
            "status": self.status.value,
            "metadata": self.metadata,
            "result": self.result,
            "error_msg": self.error_msg,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AsyncTask":
        """从字典创建任务实例"""
        return cls(
            id=data.get("id"),
            stage=TaskStage(data["stage"]),
            status=TaskStatus(data["status"]),
            metadata=data.get("metadata", {}),
            result=data.get("result", {}),
            error_msg=data.get("error_msg"),
            create_time=datetime.fromisoformat(data["create_time"]) if data.get("create_time") else None,
            update_time=datetime.fromisoformat(data["update_time"]) if data.get("update_time") else None,
        )


class ScheduledTask:
    """
    定时任务模型

    属性:
        id: 任务ID（自增主键）
        name: 任务名称
        task_type: 任务类型（cron表达式或interval）
        schedule: 调度配置（cron表达式或秒数）
        enabled: 是否启用
        last_run: 上次运行时间
        next_run: 下次运行时间
        metadata: 任务元数据
        create_time: 创建时间
        update_time: 更新时间
    """

    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        task_type: str = "interval",
        schedule: str = "3600",
        enabled: bool = True,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        create_time: Optional[datetime] = None,
        update_time: Optional[datetime] = None
    ):
        self.id = id
        self.name = name
        self.task_type = task_type
        self.schedule = schedule
        self.enabled = enabled
        self.last_run = last_run
        self.next_run = next_run
        self.metadata = metadata or {}
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "metadata": self.metadata,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }


class TaskDatabase:
    """
    任务数据库管理器

    提供任务的CRUD操作和数据库初始化功能。
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器

        参数:
            db_path: 数据库文件路径，如果为None则使用配置中的路径
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

        # 创建异步任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS async_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata TEXT,
                result TEXT,
                error_msg TEXT,
                create_time TEXT NOT NULL,
                update_time TEXT NOT NULL
            )
        """)

        # 创建定时任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                task_type TEXT NOT NULL,
                schedule TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                metadata TEXT,
                create_time TEXT NOT NULL,
                update_time TEXT NOT NULL
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_async_tasks_stage_status
            ON async_tasks(stage, status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled
            ON scheduled_tasks(enabled)
        """)

        conn.commit()
        conn.close()

    def create_async_task(self, task: AsyncTask) -> int:
        """
        创建异步任务

        参数:
            task: 任务实例

        返回:
            int: 任务ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO async_tasks (stage, status, metadata, result, error_msg, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            task.stage.value,
            task.status.value,
            json.dumps(task.metadata, ensure_ascii=False),
            json.dumps(task.result, ensure_ascii=False),
            task.error_msg,
            task.create_time.isoformat(),
            task.update_time.isoformat()
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return task_id

    def get_async_task(self, task_id: int) -> Optional[AsyncTask]:
        """
        获取异步任务

        参数:
            task_id: 任务ID

        返回:
            AsyncTask: 任务实例，如果不存在则返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM async_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return self._row_to_async_task(row)

    def update_async_task(self, task: AsyncTask):
        """
        更新异步任务

        参数:
            task: 任务实例
        """
        task.update_time = datetime.now()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE async_tasks
            SET stage = ?, status = ?, metadata = ?, result = ?, error_msg = ?, update_time = ?
            WHERE id = ?
        """, (
            task.stage.value,
            task.status.value,
            json.dumps(task.metadata, ensure_ascii=False),
            json.dumps(task.result, ensure_ascii=False),
            task.error_msg,
            task.update_time.isoformat(),
            task.id
        ))

        conn.commit()
        conn.close()

    def query_async_tasks(
        self,
        stage: Optional[TaskStage] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[AsyncTask]:
        """
        查询异步任务

        参数:
            stage: 任务阶段过滤
            status: 任务状态过滤
            limit: 返回数量限制

        返回:
            List[AsyncTask]: 任务列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM async_tasks WHERE 1=1"
        params = []

        if stage is not None:
            query += " AND stage = ?"
            params.append(stage.value)

        if status is not None:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY create_time DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_async_task(row) for row in rows]

    def create_scheduled_task(self, task: ScheduledTask) -> int:
        """
        创建定时任务

        参数:
            task: 定时任务实例

        返回:
            int: 任务ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scheduled_tasks (name, task_type, schedule, enabled, last_run, next_run, metadata, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.name,
            task.task_type,
            task.schedule,
            1 if task.enabled else 0,
            task.last_run.isoformat() if task.last_run else None,
            task.next_run.isoformat() if task.next_run else None,
            json.dumps(task.metadata, ensure_ascii=False),
            task.create_time.isoformat(),
            task.update_time.isoformat()
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return task_id

    def get_scheduled_task(self, task_id: int) -> Optional[ScheduledTask]:
        """
        获取定时任务

        参数:
            task_id: 任务ID

        返回:
            ScheduledTask: 任务实例，如果不存在则返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return self._row_to_scheduled_task(row)

    def get_scheduled_task_by_name(self, name: str) -> Optional[ScheduledTask]:
        """
        根据名称获取定时任务

        参数:
            name: 任务名称

        返回:
            ScheduledTask: 任务实例，如果不存在则返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scheduled_tasks WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return self._row_to_scheduled_task(row)

    def update_scheduled_task(self, task: ScheduledTask):
        """
        更新定时任务

        参数:
            task: 定时任务实例
        """
        task.update_time = datetime.now()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE scheduled_tasks
            SET task_type = ?, schedule = ?, enabled = ?, last_run = ?, next_run = ?, metadata = ?, update_time = ?
            WHERE id = ?
        """, (
            task.task_type,
            task.schedule,
            1 if task.enabled else 0,
            task.last_run.isoformat() if task.last_run else None,
            task.next_run.isoformat() if task.next_run else None,
            json.dumps(task.metadata, ensure_ascii=False),
            task.update_time.isoformat(),
            task.id
        ))

        conn.commit()
        conn.close()



    def get_all_scheduled_tasks(self, enabled_only: bool = False) -> List[ScheduledTask]:
        """
        获取所有定时任务

        参数:
            enabled_only: 是否只返回启用的任务

        返回:
            List[ScheduledTask]: 任务列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if enabled_only:
            cursor.execute("SELECT * FROM scheduled_tasks WHERE enabled = 1 ORDER BY name")
        else:
            cursor.execute("SELECT * FROM scheduled_tasks ORDER BY name")

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_scheduled_task(row) for row in rows]

    def _row_to_async_task(self, row: sqlite3.Row) -> AsyncTask:
        """将数据库行转换为AsyncTask实例"""
        return AsyncTask(
            id=row["id"],
            stage=TaskStage(row["stage"]),
            status=TaskStatus(row["status"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            result=json.loads(row["result"]) if row["result"] else {},
            error_msg=row["error_msg"],
            create_time=datetime.fromisoformat(row["create_time"]),
            update_time=datetime.fromisoformat(row["update_time"])
        )

    def _row_to_scheduled_task(self, row: sqlite3.Row) -> ScheduledTask:
        """将数据库行转换为ScheduledTask实例"""
        return ScheduledTask(
            id=row["id"],
            name=row["name"],
            task_type=row["task_type"],
            schedule=row["schedule"],
            enabled=bool(row["enabled"]),
            last_run=datetime.fromisoformat(row["last_run"]) if row["last_run"] else None,
            next_run=datetime.fromisoformat(row["next_run"]) if row["next_run"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            create_time=datetime.fromisoformat(row["create_time"]),
            update_time=datetime.fromisoformat(row["update_time"])
        )

    def delete_async_task(self, task_id: int):
        """
        删除异步任务

        参数:
            task_id: 任务ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM async_tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

    def delete_scheduled_task(self, task_id: int):
        """
        删除定时任务

        参数:
            task_id: 任务ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
