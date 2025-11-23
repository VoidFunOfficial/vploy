"""
系统监控模块

提供系统资源监控功能，包括：
- CPU 使用率
- 内存使用率
- 磁盘使用率
- 系统运行时间
- TPS 统计
"""

import psutil
import time
from datetime import datetime
from typing import Dict, Any
from collections import deque


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.start_time = time.time()
        self.transaction_queue = deque(maxlen=10800)  # 保存近 3 小时的数据（每秒一个点）
        self.last_transaction_count = 0
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """
        获取 CPU 信息
        
        返回:
            Dict: CPU 信息字典
        """
        return {
            'cpu_percent': round(psutil.cpu_percent(interval=1), 1),
            'cpu_count': psutil.cpu_count()
        }
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        获取内存信息
        
        返回:
            Dict: 内存信息字典
        """
        memory = psutil.virtual_memory()
        return {
            'memory_percent': round(memory.percent, 1),
            'memory_total': memory.total,
            'memory_used': memory.used,
            'memory_available': memory.available
        }
    
    def get_disk_info(self) -> Dict[str, Any]:
        """
        获取磁盘信息
        
        返回:
            Dict: 磁盘信息字典
        """
        disk = psutil.disk_usage('/')
        return {
            'disk_percent': round(disk.percent, 1),
            'disk_total': disk.total,
            'disk_used': disk.used,
            'disk_free': disk.free
        }
    
    def get_uptime_info(self) -> Dict[str, Any]:
        """
        获取系统运行时间信息
        
        返回:
            Dict: 运行时间信息字典
        """
        boot_timestamp = psutil.boot_time()
        boot_time = datetime.fromtimestamp(boot_timestamp)
        uptime_seconds = int(time.time() - boot_timestamp)
        
        return {
            'uptime': uptime_seconds,
            'boot_time': boot_time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def record_transaction(self):
        """记录一次事务"""
        current_time = time.time()
        self.transaction_queue.append(current_time)
        self.last_transaction_count += 1
    
    def get_tps_info(self) -> Dict[str, Any]:
        """
        获取 TPS 统计信息
        
        返回:
            Dict: TPS 信息字典
        """
        current_time = time.time()
        
        # 清理 3 小时前的数据
        three_hours_ago = current_time - 10800
        while self.transaction_queue and self.transaction_queue[0] < three_hours_ago:
            self.transaction_queue.popleft()
        
        # 计算当前 TPS（最近 1 秒）
        one_second_ago = current_time - 1
        current_tps = sum(1 for t in self.transaction_queue if t >= one_second_ago)
        
        # 计算平均 TPS（最近 1 分钟）
        one_minute_ago = current_time - 60
        recent_transactions = [t for t in self.transaction_queue if t >= one_minute_ago]
        avg_tps = round(len(recent_transactions) / 60, 2) if recent_transactions else 0
        
        # 计算峰值 TPS（最近 3 小时内每秒的最大值）
        max_tps = 0
        if self.transaction_queue:
            # 按秒分组统计
            second_counts = {}
            for t in self.transaction_queue:
                second = int(t)
                second_counts[second] = second_counts.get(second, 0) + 1
            max_tps = max(second_counts.values()) if second_counts else 0
        
        return {
            'current_tps': current_tps,
            'avg_tps': avg_tps,
            'max_tps': max_tps,
            'total_transactions': self.last_transaction_count
        }
    
    def get_all_info(self) -> Dict[str, Any]:
        """
        获取所有监控信息
        
        返回:
            Dict: 完整的监控信息字典
        """
        info = {}
        info.update(self.get_cpu_info())
        info.update(self.get_memory_info())
        info.update(self.get_disk_info())
        info.update(self.get_uptime_info())
        info.update(self.get_tps_info())
        
        return info


# 全局监控器实例
_system_monitor = None


def get_system_monitor() -> SystemMonitor:
    """
    获取系统监控器实例（单例模式）
    
    返回:
        SystemMonitor: 系统监控器实例
    """
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor

