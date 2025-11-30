"""
任务管理器配置模块

提供Huey任务队列和SQLite数据库的配置管理。
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class TaskManagerConfig:
    """
    任务管理器配置
    
    属性:
        db_path: SQLite数据库文件路径
        huey_db_path: Huey任务队列数据库路径
        immediate: 是否立即执行任务（用于测试）
        workers: 工作进程数量
        max_delay: 最大延迟时间（秒）
        scheduler_interval: 调度器检查间隔（秒）
    """
    
    db_path: str = "./backend/task_manager/tasks.db"
    huey_db_path: str = "./backend/task_manager/huey.db"
    immediate: bool = False
    workers: int = 4
    max_delay: int = 3600
    scheduler_interval: int = 60
    
    def __post_init__(self):
        """初始化后处理，确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        huey_db_dir = Path(self.huey_db_path).parent
        huey_db_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例
_config: Optional[TaskManagerConfig] = None


def get_config() -> TaskManagerConfig:
    """
    获取任务管理器配置实例
    
    返回:
        TaskManagerConfig: 配置实例
    """
    global _config
    if _config is None:
        _config = TaskManagerConfig()
    return _config


def set_config(config: TaskManagerConfig):
    """
    设置任务管理器配置
    
    参数:
        config: 新的配置实例
    """
    global _config
    _config = config

