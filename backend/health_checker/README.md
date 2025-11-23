# 健康检查系统 (Health Checker)

基于 asyncio 实现的定时健康检查系统，用于监控 Polymarket API 端点的可用性和网络延迟。

## 特性

- ✅ **定时检查**：每60秒自动执行一次健康检查（可配置）
- ✅ **延迟测试**：测量每个端点的响应时间（毫秒级精度）
- ✅ **单例模式**：全局唯一实例，避免重复创建
- ✅ **异步并发**：使用 asyncio 并发检查多个端点
- ✅ **VLogger 集成**：结构化日志输出，便于分析和监控
- ✅ **异常处理**：完善的超时和错误处理机制
- ✅ **灵活配置**：支持动态添加/移除端点

## 依赖

```bash
pip install aiohttp
```

## 快速开始

### 1. 基础使用

```python
import asyncio
from backend.health_checker.health_check import HealthChecker

async def main():
    # 获取健康检查器实例（单例模式）
    checker = await HealthChecker.get_instance(check_interval=60)
    
    # 执行一次手动检查
    results = await checker.check_all_endpoints()
    
    # 打印结果
    for result in results:
        print(f"{result.endpoint_name}: {result.latency_ms:.2f}ms")

asyncio.run(main())
```

### 2. 启动定时检查

```python
import asyncio
from backend.health_checker.health_check import start_health_checker

async def main():
    # 启动定时健康检查（每60秒）
    await start_health_checker(check_interval=60)
    
    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("停止健康检查...")

asyncio.run(main())
```

### 3. 使用便捷函数

```python
import asyncio
from backend.health_checker.health_check import (
    run_health_check_once,
    start_health_checker,
    stop_health_checker
)

async def main():
    # 执行一次检查
    results = await run_health_check_once()
    
    # 启动定时检查
    await start_health_checker(check_interval=60)
    
    # 运行一段时间...
    await asyncio.sleep(300)
    
    # 停止检查
    await stop_health_checker()

asyncio.run(main())
```

### 4. 自定义端点配置

```python
import asyncio
from backend.health_checker.health_check import (
    HealthChecker,
    EndpointConfig,
    EndpointType
)

async def main():
    checker = await HealthChecker.get_instance()
    
    # 添加自定义端点
    custom_endpoint = EndpointConfig(
        name="Custom API",
        url="https://api.example.com/health",
        endpoint_type=EndpointType.HTTPS,
        timeout=15,
        enabled=True
    )
    checker.add_endpoint(custom_endpoint)
    
    # 执行检查
    results = await checker.check_all_endpoints()

asyncio.run(main())
```

## 默认端点配置

系统默认监控以下 Polymarket API 端点：

| 端点名称 | URL | 超时时间 |
|---------|-----|---------|
| Data API | https://data-api.polymarket.com/ | 10秒 |
| CLOB API | https://clob.polymarket.com/ | 10秒 |
| Gamma API | https://gamma-api.polymarket.com/ | 10秒 |

## 日志输出

健康检查系统使用 VLogger 记录所有检查结果，日志包含以下信息：

### 成功检查日志

```json
{
  "ts": "2025-01-09T12:34:56.789Z",
  "level": "INFO",
  "event": "HEALTH.CHECK.SUCCESS",
  "event_code": "EVT-HC-005",
  "trace_id": "TRC-20250109123456-a1b2c3d4e5f6",
  "service": "voidpoly",
  "msg": "端点检查成功",
  "extra": {
    "endpoint_name": "Data API",
    "url": "https://data-api.polymarket.com/",
    "latency_ms": 123.45,
    "status_code": 200
  }
}
```

### 失败检查日志

```json
{
  "ts": "2025-01-09T12:34:56.789Z",
  "level": "WARN",
  "event": "HEALTH.CHECK.FAILED",
  "event_code": "EVT-HC-006",
  "trace_id": "TRC-20250109123456-a1b2c3d4e5f6",
  "service": "voidpoly",
  "msg": "端点检查失败",
  "extra": {
    "endpoint_name": "CLOB API",
    "url": "https://clob.polymarket.com/",
    "error_message": "请求超时（10秒）",
    "latency_ms": 10000.0
  }
}
```

### 汇总日志

```json
{
  "ts": "2025-01-09T12:34:56.789Z",
  "level": "INFO",
  "event": "HEALTH.CHECK.COMPLETE",
  "event_code": "EVT-HC-007",
  "trace_id": "TRC-20250109123456-a1b2c3d4e5f6",
  "service": "voidpoly",
  "msg": "健康检查完成",
  "extra": {
    "total_endpoints": 3,
    "success_count": 2,
    "failed_count": 1,
    "avg_latency_ms": 150.25
  }
}
```

## 事件码和错误码

### 事件码 (EVT-HC-xxx)

| 事件码 | 事件名称 | 说明 |
|--------|---------|------|
| EVT-HC-001 | HEALTH.CHECKER.INIT | 健康检查器初始化 |
| EVT-HC-002 | HEALTH.ENDPOINT.ADD | 添加端点配置 |
| EVT-HC-003 | HEALTH.ENDPOINT.REMOVE | 移除端点配置 |
| EVT-HC-004 | HEALTH.CHECK.START | 开始健康检查 |
| EVT-HC-005 | HEALTH.CHECK.SUCCESS | 端点检查成功 |
| EVT-HC-006 | HEALTH.CHECK.FAILED | 端点检查失败 |
| EVT-HC-007 | HEALTH.CHECK.COMPLETE | 健康检查完成 |
| EVT-HC-008 | HEALTH.LOOP.START | 定时健康检查循环启动 |
| EVT-HC-009 | HEALTH.LOOP.CANCEL | 定时健康检查循环被取消 |
| EVT-HC-010 | HEALTH.LOOP.ERROR | 定时健康检查循环异常 |
| EVT-HC-011 | HEALTH.LOOP.STOP | 定时健康检查循环已停止 |
| EVT-HC-012 | HEALTH.CHECKER.ALREADY_RUNNING | 健康检查器已在运行中 |
| EVT-HC-013 | HEALTH.CHECKER.START | 健康检查器已启动 |
| EVT-HC-014 | HEALTH.CHECKER.NOT_RUNNING | 健康检查器未在运行 |
| EVT-HC-015 | HEALTH.CHECKER.STOP | 健康检查器已停止 |

### 错误码 (E-HC-xxx)

| 错误码 | 错误名称 | 说明 | 严重性 |
|--------|---------|------|--------|
| E-HC-001 | HEALTH_CHECK_LOOP_ERROR | 定时健康检查循环异常 | ERROR |
| E-HC-002 | HEALTH_CHECK_TIMEOUT | 健康检查超时 | WARNING |
| E-HC-003 | HEALTH_CHECK_CONNECTION_ERROR | 健康检查连接错误 | WARNING |
| E-HC-004 | HEALTH_CHECK_UNKNOWN_ERROR | 健康检查未知错误 | ERROR |

## API 参考

### HealthChecker 类

#### 类方法

- `get_instance(check_interval: int = 60) -> HealthChecker`：获取单例实例（异步）
- `get_instance_sync(check_interval: int = 60) -> HealthChecker`：获取单例实例（同步）

#### 实例方法

- `add_endpoint(endpoint: EndpointConfig)`：添加端点配置
- `remove_endpoint(endpoint_name: str) -> bool`：移除端点配置
- `check_all_endpoints() -> List[HealthCheckResult]`：检查所有端点
- `start()`：启动定时健康检查
- `stop()`：停止定时健康检查
- `get_status() -> Dict[str, Any]`：获取健康检查器状态

### 便捷函数

- `get_health_checker(check_interval: int = 60) -> HealthChecker`：获取实例（同步）
- `get_health_checker_async(check_interval: int = 60) -> HealthChecker`：获取实例（异步）
- `run_health_check_once() -> List[HealthCheckResult]`：执行一次检查
- `start_health_checker(check_interval: int = 60)`：启动定时检查
- `stop_health_checker()`：停止定时检查

## 运行测试

直接运行 health_check.py 文件可以进行测试：

```bash
cd backend/health_checker
python health_check.py
```

这将：
1. 执行一次手动健康检查并显示结果
2. 启动定时健康检查（每60秒）
3. 持续运行直到按 Ctrl+C 停止

## 注意事项

1. **单例模式**：HealthChecker 使用单例模式，全局只有一个实例
2. **异步运行**：所有检查方法都是异步的，需要在 asyncio 事件循环中运行
3. **WebSocket 支持**：当前版本暂不支持 WebSocket 端点检查
4. **超时设置**：默认超时时间为10秒，可根据网络情况调整
5. **日志位置**：日志输出到 `backend/logs/vlogger.log`

## 集成到其他模块

在其他模块中使用健康检查系统：

```python
# 在应用启动时启动健康检查
import asyncio
from backend.health_checker.health_check import start_health_checker

async def app_startup():
    # 启动健康检查（每60秒）
    await start_health_checker(check_interval=60)
    
    # 其他启动逻辑...

# 在应用关闭时停止健康检查
from backend.health_checker.health_check import stop_health_checker

async def app_shutdown():
    # 停止健康检查
    await stop_health_checker()
    
    # 其他清理逻辑...
```

## 故障排查

### 问题：导入错误

确保已安装 aiohttp：
```bash
pip install aiohttp
```

### 问题：日志未输出

检查 VLogger 配置是否正确，确保日志目录存在：
```bash
mkdir -p backend/logs
```

### 问题：检查超时

调整端点的超时时间：
```python
endpoint.timeout = 30  # 增加到30秒
```

