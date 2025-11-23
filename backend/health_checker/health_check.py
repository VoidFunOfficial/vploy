"""
健康检查系统

基于 asyncio 实现的定时健康检查系统，支持：
- 每60秒自动执行一次健康检查
- 测试所有已配置的API端点网络延迟
- 使用 VLogger 记录检查结果
- 单例模式确保全局唯一实例
- 异常和超时处理
- 结构化日志输出

使用示例:
    >>> import asyncio
    >>> from backend.health_checker.health_check import HealthChecker
    >>>
    >>> # 获取健康检查器实例（单例模式）
    >>> checker = HealthChecker.get_instance()
    >>>
    >>> # 启动定时健康检查
    >>> asyncio.run(checker.start())
    >>>
    >>> # 或者手动执行一次检查
    >>> asyncio.run(checker.check_all_endpoints())
"""

import asyncio
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
import sys

import aiohttp

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger


# ==================== 端点类型枚举 ====================

class EndpointType(str, Enum):
    """端点类型枚举"""
    HTTP = "HTTP"
    HTTPS = "HTTPS"
    WEBSOCKET = "WEBSOCKET"


# ==================== 端点配置数据结构 ====================

@dataclass
class EndpointConfig:
    """
    端点配置数据结构

    属性:
        name: 端点名称
        url: 端点URL
        endpoint_type: 端点类型（HTTP/HTTPS/WEBSOCKET）
        timeout: 超时时间（秒）
        enabled: 是否启用检查
    """
    name: str
    url: str
    endpoint_type: EndpointType = EndpointType.HTTPS
    timeout: int = 10
    enabled: bool = True


# ==================== 健康检查结果数据结构 ====================

@dataclass
class HealthCheckResult:
    """
    健康检查结果数据结构

    属性:
        endpoint_name: 端点名称
        url: 端点URL
        success: 是否成功
        latency_ms: 延迟时间（毫秒）
        status_code: HTTP状态码（如果适用）
        error_message: 错误信息（如果失败）
        timestamp: 检查时间戳
    """
    endpoint_name: str
    url: str
    success: bool
    latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "endpoint_name": self.endpoint_name,
            "url": self.url,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 2) if self.latency_ms is not None else None,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }


# ==================== 健康检查器（单例模式） ====================

class HealthChecker:
    """
    健康检查器（单例模式）

    功能:
        - 定时检查所有配置的API端点
        - 测量网络延迟
        - 记录检查结果到 VLogger
        - 异常和超时处理
    """

    _instance: Optional['HealthChecker'] = None
    _lock = asyncio.Lock()

    # 默认端点配置
    DEFAULT_ENDPOINTS = [
        EndpointConfig(
            name="Data API",
            url="https://data-api.polymarket.com/",
            endpoint_type=EndpointType.HTTPS,
            timeout=10
        ),
        EndpointConfig(
            name="CLOB API",
            url="https://clob.polymarket.com/",
            endpoint_type=EndpointType.HTTPS,
            timeout=10
        ),
        EndpointConfig(
            name="Gamma API",
            url="https://gamma-api.polymarket.com/",
            endpoint_type=EndpointType.HTTPS,
            timeout=10
        ),
        # 注意: WebSocket 端点需要特殊处理，暂时不包含在默认配置中
        # 如需添加 WebSocket 检查，需要实现专门的 WebSocket 连接测试逻辑
    ]

    def __init__(self, check_interval: int = 60):
        """
        初始化健康检查器

        参数:
            check_interval: 检查间隔（秒），默认60秒
        """
        self.check_interval = check_interval
        self.endpoints: List[EndpointConfig] = self.DEFAULT_ENDPOINTS.copy()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

        vlogger.info("EVT-HC-001", msg="健康检查器初始化完成", extra={
            "check_interval": check_interval,
            "endpoints_count": len(self.endpoints)
        })

    @classmethod
    async def get_instance(cls, check_interval: int = 60) -> 'HealthChecker':
        """
        获取健康检查器单例实例（异步方法）

        参数:
            check_interval: 检查间隔（秒），默认60秒

        返回:
            HealthChecker: 健康检查器实例
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(check_interval)
        return cls._instance

    @classmethod
    def get_instance_sync(cls, check_interval: int = 60) -> 'HealthChecker':
        """
        获取健康检查器单例实例（同步方法）

        参数:
            check_interval: 检查间隔（秒），默认60秒

        返回:
            HealthChecker: 健康检查器实例
        """
        if cls._instance is None:
            cls._instance = cls(check_interval)
        return cls._instance


    def add_endpoint(self, endpoint: EndpointConfig):
        """
        添加端点配置

        参数:
            endpoint: 端点配置对象
        """
        self.endpoints.append(endpoint)
        vlogger.info("EVT-HC-002", msg="添加端点配置", extra={
            "endpoint_name": endpoint.name,
            "url": endpoint.url
        })

    def remove_endpoint(self, endpoint_name: str) -> bool:
        """
        移除端点配置

        参数:
            endpoint_name: 端点名称

        返回:
            bool: 是否成功移除
        """
        for i, endpoint in enumerate(self.endpoints):
            if endpoint.name == endpoint_name:
                self.endpoints.pop(i)
                vlogger.info("EVT-HC-003", msg="移除端点配置", extra={
                    "endpoint_name": endpoint_name
                })
                return True
        return False

    async def check_http_endpoint(self, endpoint: EndpointConfig) -> HealthCheckResult:
        """
        检查 HTTP/HTTPS 端点

        参数:
            endpoint: 端点配置

        返回:
            HealthCheckResult: 检查结果
        """
        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=endpoint.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(endpoint.url) as response:
                    latency_ms = (time.time() - start_time) * 1000

                    result = HealthCheckResult(
                        endpoint_name=endpoint.name,
                        url=endpoint.url,
                        success=response.status < 400,
                        latency_ms=latency_ms,
                        status_code=response.status
                    )

                    return result

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                success=False,
                latency_ms=latency_ms,
                error_message=f"请求超时（{endpoint.timeout}秒）"
            )

        except aiohttp.ClientError as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                success=False,
                latency_ms=latency_ms,
                error_message=f"连接错误: {str(e)}"
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                success=False,
                latency_ms=latency_ms,
                error_message=f"未知错误: {str(e)}"
            )

    async def check_single_endpoint(self, endpoint: EndpointConfig) -> HealthCheckResult:
        """
        检查单个端点

        参数:
            endpoint: 端点配置

        返回:
            HealthCheckResult: 检查结果
        """
        if not endpoint.enabled:
            return HealthCheckResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                success=False,
                error_message="端点已禁用"
            )

        # 根据端点类型选择检查方法
        if endpoint.endpoint_type in (EndpointType.HTTP, EndpointType.HTTPS):
            return await self.check_http_endpoint(endpoint)
        elif endpoint.endpoint_type == EndpointType.WEBSOCKET:
            # WebSocket 检查需要特殊处理，暂时返回未实现
            return HealthCheckResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                success=False,
                error_message="WebSocket 检查暂未实现"
            )
        else:
            return HealthCheckResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                success=False,
                error_message=f"不支持的端点类型: {endpoint.endpoint_type}"
            )

    async def check_all_endpoints(self) -> List[HealthCheckResult]:
        """
        检查所有端点

        返回:
            List[HealthCheckResult]: 所有端点的检查结果列表
        """
        vlogger.info("EVT-HC-004", msg="开始健康检查", extra={
            "endpoints_count": len(self.endpoints)
        })

        # 并发检查所有端点
        tasks = [self.check_single_endpoint(endpoint) for endpoint in self.endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        check_results = []
        success_count = 0
        failed_count = 0
        total_latency = 0.0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 处理异常情况
                endpoint = self.endpoints[i]
                result = HealthCheckResult(
                    endpoint_name=endpoint.name,
                    url=endpoint.url,
                    success=False,
                    error_message=f"检查异常: {str(result)}"
                )

            check_results.append(result)

            # 统计结果
            if result.success:
                success_count += 1
                if result.latency_ms is not None:
                    total_latency += result.latency_ms
            else:
                failed_count += 1

            # 记录单个端点检查结果
            if result.success:
                vlogger.info("EVT-HC-005", msg="端点检查成功", extra={
                    "endpoint_name": result.endpoint_name,
                    "url": result.url,
                    "latency_ms": round(result.latency_ms, 2) if result.latency_ms else None,
                    "status_code": result.status_code
                })
            else:
                vlogger.warn("EVT-HC-006", msg="端点检查失败", extra={
                    "endpoint_name": result.endpoint_name,
                    "url": result.url,
                    "error_message": result.error_message,
                    "latency_ms": round(result.latency_ms, 2) if result.latency_ms else None
                })

        # 记录汇总结果
        avg_latency = total_latency / success_count if success_count > 0 else 0
        vlogger.info("EVT-HC-007", msg="健康检查完成", extra={
            "total_endpoints": len(self.endpoints),
            "success_count": success_count,
            "failed_count": failed_count,
            "avg_latency_ms": round(avg_latency, 2)
        })

        return check_results


    async def _scheduled_check_loop(self):
        """
        定时检查循环（内部方法）
        """
        vlogger.info("EVT-HC-008", msg="定时健康检查循环启动", extra={
            "check_interval": self.check_interval
        })

        while self.is_running:
            try:
                # 执行健康检查
                await self.check_all_endpoints()

                # 等待下次检查
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                # 任务被取消，正常退出
                vlogger.info("EVT-HC-009", msg="定时健康检查循环被取消")
                break

            except Exception as e:
                # 记录异常但继续运行
                vlogger.error("EVT-HC-010", msg="定时健康检查循环异常",
                            error_code="E-HC-001", extra={
                    "exception": str(e)
                })
                # 等待一段时间后继续
                await asyncio.sleep(self.check_interval)

        vlogger.info("EVT-HC-011", msg="定时健康检查循环已停止")

    async def start(self):
        """
        启动定时健康检查

        该方法会启动一个后台任务，每隔 check_interval 秒执行一次健康检查。
        """
        if self.is_running:
            vlogger.warn("EVT-HC-012", msg="健康检查器已在运行中")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._scheduled_check_loop())

        vlogger.info("EVT-HC-013", msg="健康检查器已启动", extra={
            "check_interval": self.check_interval
        })

    async def stop(self):
        """
        停止定时健康检查
        """
        if not self.is_running:
            vlogger.warn("EVT-HC-014", msg="健康检查器未在运行")
            return

        self.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        vlogger.info("EVT-HC-015", msg="健康检查器已停止")

    def get_status(self) -> Dict[str, Any]:
        """
        获取健康检查器状态

        返回:
            dict: 状态信息
        """
        return {
            "is_running": self.is_running,
            "check_interval": self.check_interval,
            "endpoints_count": len(self.endpoints),
            "endpoints": [
                {
                    "name": ep.name,
                    "url": ep.url,
                    "type": ep.endpoint_type.value,
                    "enabled": ep.enabled
                }
                for ep in self.endpoints
            ]
        }


# ==================== 便捷函数 ====================

def get_health_checker(check_interval: int = 60) -> HealthChecker:
    """
    获取健康检查器实例的便捷函数（同步版本）

    参数:
        check_interval: 检查间隔（秒），默认60秒

    返回:
        HealthChecker: 健康检查器实例
    """
    return HealthChecker.get_instance_sync(check_interval)


async def get_health_checker_async(check_interval: int = 60) -> HealthChecker:
    """
    获取健康检查器实例的便捷函数（异步版本）

    参数:
        check_interval: 检查间隔（秒），默认60秒

    返回:
        HealthChecker: 健康检查器实例
    """
    return await HealthChecker.get_instance(check_interval)


async def run_health_check_once() -> List[HealthCheckResult]:
    """
    执行一次健康检查的便捷函数

    返回:
        List[HealthCheckResult]: 检查结果列表
    """
    checker = await get_health_checker_async()
    return await checker.check_all_endpoints()


async def start_health_checker(check_interval: int = 60):
    """
    启动健康检查器的便捷函数

    参数:
        check_interval: 检查间隔（秒），默认60秒
    """
    checker = await get_health_checker_async(check_interval)
    await checker.start()


async def stop_health_checker():
    """
    停止健康检查器的便捷函数
    """
    checker = await get_health_checker_async()
    await checker.stop()


# ==================== 主程序入口（用于测试） ====================

async def main():
    """
    主程序入口（用于测试）
    """
    # 获取健康检查器实例
    checker = await get_health_checker_async(check_interval=60)

    # 执行一次手动检查
    print("执行一次手动健康检查...")
    results = await checker.check_all_endpoints()

    print("\n检查结果:")
    for result in results:
        status = "✓" if result.success else "✗"
        latency = f"{result.latency_ms:.2f}ms" if result.latency_ms else "N/A"
        print(f"{status} {result.endpoint_name}: {latency}")
        if not result.success:
            print(f"  错误: {result.error_message}")

    # 启动定时检查
    print(f"\n启动定时健康检查（每{checker.check_interval}秒）...")
    await checker.start()

    # 运行一段时间后停止（用于测试）
    try:
        # 保持运行，直到收到中断信号
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n收到中断信号，停止健康检查...")
        await checker.stop()


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
