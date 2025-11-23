# 事件过滤器模块

基于多步骤过滤流程和数据库持久化的事件（Event）数据过滤系统，专为 Polymarket 事件数据设计。

## 功能特性

- ✅ **多步骤过滤流程**：Tag、标题关键词、描述关键词、数据库去重、AI 处理（预留）
- ✅ **数据库持久化**：SQLite 存储黑名单配置和已处理事件记录
- ✅ **可配置黑名单**：支持动态添加/删除/更新黑名单规则
- ✅ **去重机制**：自动跟踪已处理的事件，避免重复处理
- ✅ **VLogger 集成**：完整的日志记录和统计信息
- ✅ **AI 接口预留**：为未来 AI 过滤功能预留接口

## 目录结构

```
backend/filter/
├── __init__.py              # 模块导出
├── event_filter.py          # 事件过滤器核心逻辑
├── market_filter.py         # 市场过滤器（已废弃）
├── database/                # 数据库模块
│   ├── __init__.py
│   ├── db_manager.py        # 数据库管理器
│   └── filter.db            # SQLite 数据库文件（自动创建）
├── test_event_filter.py     # 事件过滤器测试脚本
└── README.md                # 本文档
```

## 快速开始

### 1. 初始化数据库

```python
from backend.filter import init_database

# 初始化数据库（创建表结构并插入默认黑名单配置）
success = init_database()
if success:
    print("数据库初始化成功")
```

### 2. 过滤事件数据

```python
from backend.filter import filter_events
from polymarket_api import PolymarketGammaClient

# 创建客户端
client = PolymarketGammaClient()

# 获取最新事件
events = client.get_new_events(limit=10)

# 执行过滤
filtered_events = filter_events(events)

print(f"输入: {len(events)} 个事件")
print(f"输出: {len(filtered_events)} 个事件")
```

### 3. 管理黑名单配置

```python
from backend.filter import (
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    update_blacklist_item,
)

# 获取所有黑名单配置
blacklist = get_blacklist()
print(blacklist)
# 输出: {'tag': ['china', 'sports', 'elections'], ...}

# 获取特定类型的黑名单
tag_blacklist = get_blacklist('tag')
print(tag_blacklist)
# 输出: {'tag': ['china', 'sports', 'elections']}

# 添加黑名单项
add_blacklist_item('tag', 'meme')
add_blacklist_item('title_keyword', 'celebrity')
add_blacklist_item('description_keyword', 'scam')

# 删除黑名单项
remove_blacklist_item('tag', 'meme')

# 更新黑名单项状态（启用/禁用）
update_blacklist_item(item_id=1, is_active=False)
```

### 4. 管理已处理事件

```python
from backend.filter import (
    is_market_processed,
    mark_market_as_processed,
    clear_processed_markets,
)
from datetime import datetime, timedelta

# 检查事件是否已处理
if is_market_processed("event_id_123"):
    print("该事件已处理过")

# 手动标记事件为已处理
mark_market_as_processed("event_id_456")

# 清理 7 天前的已处理记录
seven_days_ago = datetime.now() - timedelta(days=7)
count = clear_processed_markets(before_date=seven_days_ago)
print(f"清理了 {count} 条记录")

# 清理所有已处理记录
count = clear_processed_markets()
print(f"清理了 {count} 条记录")
```

## 过滤流程详解

### 步骤 1: Tag 过滤

排除 `tags` 字段包含任何黑名单值的事件。

**默认黑名单**：`['china', 'sports', 'elections']`

**示例**：
```python
# 这个事件会被过滤掉
event = Event(
    id="e1",
    title="China Economic Growth",
    tags=[{"label": "china", "slug": "china"}]  # 包含黑名单标签
)
```

### 步骤 2: 标题关键词过滤

排除 `title` 字段中包含任何黑名单关键词的事件（不区分大小写）。

**默认黑名单**：`[]`（空，可根据需要添加）

**示例**：
```python
# 添加标题关键词黑名单
add_blacklist_item('title_keyword', 'scam')

# 这个事件会被过滤掉
event = Event(
    id="e2",
    title="Crypto Scam Alert",  # 包含 "scam"
)
```

### 步骤 3: 描述关键词过滤

排除 `description` 字段中包含任何黑名单关键词的事件（不区分大小写）。

**默认黑名单**：`[]`（空，可根据需要添加）

**示例**：
```python
# 添加描述关键词黑名单
add_blacklist_item('description_keyword', 'gambling')

# 这个事件会被过滤掉
event = Event(
    id="e3",
    description="Online gambling market predictions"  # 包含 "gambling"
)
```

### 步骤 4: 数据库去重检查

检查事件 ID 是否已在 `processed_markets` 表中。如果已存在，则跳过该事件。

通过所有过滤的事件会自动记录到数据库中。

### 步骤 5: AI 处理（预留接口）

```python
async def ai_process_event(event: Event) -> bool:
    """
    AI 处理单个事件（预留接口）

    返回:
        bool: 是否通过 AI 过滤
    """
    # TODO: 实现 AI 过滤逻辑
    return True
```

当前实现直接返回 `True`（通过过滤）。未来可以集成 LLM API 进行智能分析。

## 数据库结构

### processed_markets 表

记录已处理过的市场 ID 和处理时间戳。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| market_id | TEXT | 市场 ID（唯一） |
| processed_at | TIMESTAMP | 处理时间 |
| created_at | TIMESTAMP | 创建时间 |

### blacklist_config 表

存储可配置的黑名单规则。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| blacklist_type | TEXT | 黑名单类型（tag/title_keyword/description_keyword） |
| value | TEXT | 黑名单值 |
| is_active | INTEGER | 是否启用（1=启用，0=禁用） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## API 参考

### 过滤函数

#### `filter_events(events: List[Event]) -> List[Event]`

执行完整的事件过滤流程。

**参数**：
- `events`: 待过滤的事件列表

**返回**：
- `List[Event]`: 通过所有过滤步骤的事件列表

### 黑名单管理函数

#### `get_blacklist(blacklist_type: Optional[str] = None) -> Dict[str, List[str]]`

获取黑名单配置（仅返回激活的配置）。

#### `add_blacklist_item(blacklist_type: str, value: str) -> bool`

添加黑名单配置项。

#### `remove_blacklist_item(blacklist_type: str, value: str) -> bool`

删除黑名单配置项。

#### `update_blacklist_item(item_id: int, is_active: bool) -> bool`

更新黑名单配置项的激活状态。

### 已处理事件管理函数

#### `is_market_processed(event_id: str) -> bool`

检查事件是否已处理。

#### `mark_market_as_processed(event_id: str) -> bool`

标记事件为已处理。

#### `clear_processed_markets(before_date: Optional[datetime] = None) -> int`

清理已处理事件记录。

## 日志系统

模块使用 VLogger 记录所有关键操作和统计信息。

### 事件类型码（EVT-8xxx 系列）

| 事件码 | 事件名称 | 描述 |
|--------|----------|------|
| EVT-8001 | FILTER.INIT | 过滤器初始化 |
| EVT-8002 | FILTER.START | 过滤流程开始 |
| EVT-8003 | FILTER.COMPLETE | 过滤流程完成 |
| EVT-8011 | FILTER.CATEGORY.COMPLETE | Category 过滤完成 |
| EVT-8021 | FILTER.TAG.COMPLETE | Tag 过滤完成 |
| EVT-8031 | FILTER.DESCRIPTION.COMPLETE | 描述关键词过滤完成 |
| EVT-8041 | FILTER.DATABASE.COMPLETE | 数据库去重检查完成 |
| EVT-8051 | FILTER.AI.SKIP | AI 过滤跳过 |

### 错误码（E-FILTER-xxx 系列）

| 错误码 | 错误名称 | 描述 |
|--------|----------|------|
| E-FILTER-001 | FILTER_DB_QUERY_ERROR | 数据库查询错误 |
| E-FILTER-002 | FILTER_DB_UPDATE_ERROR | 数据库更新错误 |
| E-FILTER-003 | FILTER_DB_INIT_ERROR | 数据库初始化错误 |

## 运行测试

```bash
cd backend/filter
python test_event_filter.py
```

测试脚本会验证以下功能：
1. 数据库初始化
2. 黑名单配置管理
3. 事件过滤流程
4. 已处理事件管理
5. 真实 API 数据测试

## 注意事项

1. **线程安全**：数据库管理器使用线程本地存储，支持多线程并发访问
2. **数据库路径**：默认数据库路径为 `backend/filter/database/filter.db`，可通过参数自定义
3. **黑名单类型**：目前支持三种类型：`tag`、`title_keyword`、`description_keyword`
4. **AI 接口**：`ai_process_event` 是异步函数，为未来 AI 集成预留
5. **默认黑名单**：默认只启用 Tag 黑名单，标题和描述关键词黑名单需要手动添加

## 未来扩展

- [ ] 实现 AI 过滤逻辑（集成 LLM API）
- [ ] 添加更多黑名单类型（如交易量、流动性阈值等）
- [ ] 支持正则表达式匹配
- [ ] 添加白名单机制
- [ ] 提供 Web UI 管理界面

