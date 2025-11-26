# 序列号管理器 (Sequence Manager)

基于 SQLite 实现的企业级序列号管理系统，为不同业务模块提供线程安全的自增序列号服务。

## 特性

- ✅ **线程安全**: 使用数据库事务保证序列号获取的原子性
- ✅ **单例模式**: 全局唯一的数据库连接管理
- ✅ **多序列支持**: 支持多种业务序列类型
- ✅ **完整日志**: 集成 VLogger 日志系统，记录所有操作
- ✅ **灵活管理**: 支持序列初始化、重置、查询、删除等操作
- ✅ **结果追踪**: 每次序列更新可记录完成结果/备注

## 支持的序列类型

系统预定义了以下序列类型：

| 序列名称 | 用途 | 说明 |
|---------|------|------|
| `filter_sequence` | 过滤系统 | 用于事件过滤模块的序列号 |
| `analysis_sequence` | 分析系统 | 用于AI分析模块的序列号 |
| `trade_sequence` | 交易系统 | 用于交易执行模块的序列号 |
| `position_sequence` | 持仓系统 | 用于持仓管理模块的序列号 |
| `decision_sequence` | 决策系统 | 用于决策引擎模块的序列号 |

## 数据库结构

### sequences 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `sequence_name` | TEXT | 序列名称（主键） |
| `current_value` | INTEGER | 当前序列值 |
| `step` | INTEGER | 步长（默认为1） |
| `result` | TEXT | 完成结果/备注 |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 最后更新时间 |

## 安装

序列管理器是 VoidPoly 项目的一部分，无需单独安装。

## 快速开始

### 基础使用

```python
from backend.sequence_manager import get_sequence_manager

# 获取序列管理器实例（单例）
seq_mgr = get_sequence_manager()

# 获取下一个序列号
filter_id = seq_mgr.get_next_sequence('filter_sequence')
print(f"Filter序列号: {filter_id}")

# 获取序列号并记录结果
trade_id = seq_mgr.get_next_sequence('trade_sequence', result='订单提交成功')
print(f"Trade序列号: {trade_id}")
```

### 查询序列状态

```python
# 查询当前序列值（不更新）
current_value = seq_mgr.get_current_value('analysis_sequence')
print(f"Analysis当前值: {current_value}")

# 获取序列完整信息
info = seq_mgr.get_sequence_info('position_sequence')
print(f"序列信息: {info}")
# 输出: {'sequence_name': 'position_sequence', 'current_value': 42, 'step': 1, ...}

# 列出所有序列
all_sequences = seq_mgr.list_all_sequences()
for name, info in all_sequences.items():
    print(f"{name}: 当前值={info['current_value']}, 步长={info['step']}")
```

### 序列管理

```python
# 初始化新序列（如果已存在则跳过）
seq_mgr.init_sequence('custom_sequence', initial_value=1000, step=1, result='自定义序列')

# 重置序列到指定值
seq_mgr.reset_sequence('filter_sequence', value=0, result='月度重置')

# 删除自定义序列（预定义序列不能删除）
seq_mgr.delete_sequence('custom_sequence')
```

## API 参考

### SequenceManager 类

#### `get_next_sequence(sequence_name: str, result: Optional[str] = None) -> int`

获取下一个序列号（原子操作，线程安全）。

**参数:**
- `sequence_name` (str): 序列名称
- `result` (str, 可选): 完成结果/备注

**返回:**
- `int`: 下一个序列号

**异常:**
- `ValueError`: 如果序列名称不存在

**示例:**
```python
seq_id = seq_mgr.get_next_sequence('trade_sequence', result='订单已执行')
```

---

#### `get_current_value(sequence_name: str) -> int`

查询当前序列值（不更新）。

**参数:**
- `sequence_name` (str): 序列名称

**返回:**
- `int`: 当前序列值

**异常:**
- `ValueError`: 如果序列名称不存在

**示例:**
```python
current = seq_mgr.get_current_value('filter_sequence')
```

---

#### `reset_sequence(sequence_name: str, value: int = 0, result: Optional[str] = None)`

重置序列到指定值。

**参数:**
- `sequence_name` (str): 序列名称
- `value` (int): 重置后的值（默认为0）
- `result` (str, 可选): 重置原因/备注

**异常:**
- `ValueError`: 如果序列名称不存在

**示例:**
```python
seq_mgr.reset_sequence('analysis_sequence', value=0, result='季度重置')
```

---

#### `init_sequence(sequence_name: str, initial_value: int = 0, step: int = 1, result: Optional[str] = None)`

初始化新序列（如果序列已存在则不做任何操作）。

**参数:**
- `sequence_name` (str): 序列名称
- `initial_value` (int): 初始值（默认为0）
- `step` (int): 步长（默认为1）
- `result` (str, 可选): 初始化备注

**示例:**
```python
seq_mgr.init_sequence('report_sequence', initial_value=1, step=1, result='报表序列')
```

---

#### `get_sequence_info(sequence_name: str) -> Dict[str, Any]`

获取序列的完整信息。

**参数:**
- `sequence_name` (str): 序列名称

**返回:**
- `dict`: 包含序列所有信息的字典

**异常:**
- `ValueError`: 如果序列名称不存在

**示例:**
```python
info = seq_mgr.get_sequence_info('trade_sequence')
print(info)
# {'sequence_name': 'trade_sequence', 'current_value': 123, 'step': 1, ...}
```

---

#### `list_all_sequences() -> Dict[str, Dict[str, Any]]`

列出所有序列及其信息。

**返回:**
- `dict`: 以序列名称为键的字典，值为序列信息

**示例:**
```python
all_seqs = seq_mgr.list_all_sequences()
for name, info in all_seqs.items():
    print(f"{name}: {info['current_value']}")
```

---

#### `delete_sequence(sequence_name: str)`

删除指定序列。

**参数:**
- `sequence_name` (str): 序列名称

**异常:**
- `ValueError`: 如果序列名称不存在或为预定义序列

**示例:**
```python
seq_mgr.delete_sequence('custom_sequence')
```

---

### 全局函数

#### `get_sequence_manager(db_path: str = "backend/sequence_manager/sequences.db") -> SequenceManager`

获取序列管理器实例（单例模式）。

**参数:**
- `db_path` (str): 数据库文件路径

**返回:**
- `SequenceManager`: 序列管理器实例

**示例:**
```python
from backend.sequence_manager import get_sequence_manager

seq_mgr = get_sequence_manager()
```

## 并发安全

序列管理器使用以下机制确保并发安全：

1. **数据库事务**: 使用 `IMMEDIATE` 事务级别，确保序列号获取的原子性
2. **单例模式**: 使用线程锁确保全局只有一个实例
3. **线程本地连接**: 每个线程使用独立的数据库连接

## 日志集成

序列管理器集成了 VLogger 日志系统，记录以下事件：

| 事件码 | 日志等级 | 说明 |
|--------|---------|------|
| `SEQ.MANAGER.INIT` | INFO | 序列管理器初始化 |
| `SEQ.DB.TABLES_CREATED` | INFO | 数据库表创建完成 |
| `SEQ.DEFAULT.INIT` | INFO | 默认序列初始化 |
| `SEQ.GET_NEXT` | DEBUG | 获取下一个序列号 |
| `SEQ.INIT` | INFO | 序列初始化成功 |
| `SEQ.RESET` | INFO | 序列重置成功 |
| `SEQ.DELETE` | INFO | 序列删除成功 |

错误码：

| 错误码 | 说明 |
|--------|------|
| `E-SEQ-001` | 数据库表创建失败 |
| `E-SEQ-002` | 默认序列初始化失败 |
| `E-SEQ-003` | 获取序列号失败 |
| `E-SEQ-004` | 查询序列值失败 |
| `E-SEQ-005` | 序列重置失败 |
| `E-SEQ-006` | 序列初始化失败 |
| `E-SEQ-007` | 获取序列信息失败 |
| `E-SEQ-008` | 列出序列失败 |
| `E-SEQ-009` | 序列删除失败 |

## 最佳实践

### 1. 使用单例模式

始终通过 `get_sequence_manager()` 获取实例，不要直接实例化 `SequenceManager`。

```python
# ✅ 推荐
seq_mgr = get_sequence_manager()

# ❌ 不推荐
seq_mgr = SequenceManager()
```

### 2. 记录操作结果

在获取序列号时记录操作结果，便于追踪和审计。

```python
# ✅ 推荐
seq_id = seq_mgr.get_next_sequence('trade_sequence', result='订单ID:12345已提交')

# ⚠️ 可以但不推荐
seq_id = seq_mgr.get_next_sequence('trade_sequence')
```

### 3. 定期重置序列

根据业务需求定期重置序列，避免序列值过大。

```python
# 月度重置示例
seq_mgr.reset_sequence('filter_sequence', value=0, result='2025-01月度重置')
```

### 4. 异常处理

始终处理可能的异常。

```python
try:
    seq_id = seq_mgr.get_next_sequence('trade_sequence')
except ValueError as e:
    print(f"序列不存在: {e}")
except Exception as e:
    print(f"获取序列号失败: {e}")
```

## 性能考虑

- **数据库位置**: 默认数据库位于 `backend/sequence_manager/sequences.db`
- **事务级别**: 使用 `IMMEDIATE` 事务级别，平衡性能和并发安全
- **索引优化**: 在 `sequence_name` 字段上创建索引，提高查询性能
- **连接池**: 每个线程维护独立的数据库连接，避免连接竞争

## 故障排查

### 问题: 序列号重复

**原因**: 可能是并发访问导致的竞态条件。

**解决方案**: 
- 确保使用 `get_sequence_manager()` 获取单例实例
- 检查数据库文件权限
- 查看日志中的错误信息

### 问题: 数据库锁定

**原因**: 长时间持有数据库连接或事务。

**解决方案**:
- 确保操作尽快完成
- 避免在事务中执行耗时操作
- 检查是否有未提交的事务

## 许可证

本模块是 VoidPoly 项目的一部分，遵循项目许可证。

