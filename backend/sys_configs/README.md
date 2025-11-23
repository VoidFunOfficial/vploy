# 统一配置管理系统

## 简介

统一配置管理系统使用 SQLite 数据库集中管理所有系统配置，包括：
- VLogger 日志配置
- 邮件告警配置
- Filter 黑名单配置
- 已处理事件记录

## 快速开始

### 1. 初始化数据库

```python
from backend.sys_configs import init_config_database

# 初始化统一配置数据库（会创建所有表并插入默认配置）
init_config_database()
```

### 2. 使用 VLogger 配置

```python
from backend.vlogger import get_logger

# 自动从数据库加载配置
logger = get_logger("my_service", use_db_config=True)
logger.info("APP.START", msg="应用启动")
```

### 3. 使用 Filter 配置

```python
from backend.filter import EventFilter
from backend.sys_configs import add_blacklist_item

# 创建过滤器（自动使用统一配置数据库）
event_filter = EventFilter()

# 添加黑名单项
add_blacklist_item('tag', 'unwanted_tag')

# 过滤事件
filtered_events = event_filter.filter_events(events)
```

## 主要功能

### VLogger 配置管理

```python
from backend.sys_configs import (
    get_vlogger_config,
    save_vlogger_config,
    get_vlogger_config_value,
    set_vlogger_config_value,
)

# 获取所有配置
config = get_vlogger_config()

# 修改配置
config['min_level'] = 'DEBUG'
save_vlogger_config(config)

# 获取/设置单个配置项
level = get_vlogger_config_value('min_level', default='INFO')
set_vlogger_config_value('min_level', 'DEBUG')
```

### 邮件配置管理

```python
from backend.sys_configs import (
    get_email_config,
    save_email_config,
)

# 获取邮件配置
email_config = get_email_config()

# 修改配置
email_config['to_emails'] = ['admin@example.com']
save_email_config(email_config)
```

### Filter 黑名单管理

```python
from backend.sys_configs import (
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    update_blacklist_item,
)

# 获取黑名单
blacklist = get_blacklist()  # 获取所有类型
tag_blacklist = get_blacklist('tag')  # 获取指定类型

# 添加黑名单项
add_blacklist_item('tag', 'sports')
add_blacklist_item('category', 'politics')
add_blacklist_item('description_keyword', 'gambling')

# 删除黑名单项
remove_blacklist_item('tag', 'sports')

# 更新黑名单项状态
update_blacklist_item(item_id=1, is_active=False)
```

### 已处理事件管理

```python
from backend.sys_configs import (
    is_market_processed,
    mark_market_as_processed,
    clear_processed_markets,
)

# 检查市场是否已处理
if not is_market_processed('market_123'):
    # 处理市场
    process_market('market_123')
    # 标记为已处理
    mark_market_as_processed('market_123')

# 清理旧记录
from datetime import datetime, timedelta
before_date = datetime.now() - timedelta(days=30)
clear_processed_markets(before_date)
```

## 数据库结构

### 数据库位置
- **统一配置数据库**: `backend/sys_configs/system_config.db`

### 数据库表

1. **vlogger_config**: VLogger 日志配置（14 个配置项）
2. **email_config**: 邮件告警配置（7 个配置项）
3. **filter_blacklist**: Filter 黑名单配置（支持 tag/category/description_keyword）
4. **processed_markets**: 已处理市场记录（用于去重）
5. **config_metadata**: 配置元数据（版本管理）

详细的表结构请参考 [MIGRATION_SUMMARY.md](./MIGRATION_SUMMARY.md)。

## 配置项说明

### VLogger 配置项

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| service_name | string | "core" | 服务名称 |
| log_dir | string | "./logs" | 日志目录 |
| log_file_prefix | string | "app" | 日志文件前缀 |
| rotation | string | "500 MB" | 日志轮转大小 |
| retention | string | "30 days" | 日志保留时间 |
| compression | string | "zip" | 日志压缩格式 |
| enable_console | boolean | true | 是否启用控制台输出 |
| enable_file | boolean | true | 是否启用文件输出 |
| enable_json | boolean | true | 是否启用 JSON 格式 |
| min_level | string | "INFO" | 最小日志级别 |
| sample_rates | json | {} | 采样率配置 |
| enable_sanitization | boolean | true | 是否启用敏感信息脱敏 |
| enable_alerts | boolean | true | 是否启用告警 |
| extra_fields | json | {} | 额外字段 |

### 邮件配置项

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| smtp_server | string | "smtp.163.com" | SMTP 服务器 |
| smtp_port | integer | 465 | SMTP 端口 |
| username | string | "imzfat@163.com" | 邮箱用户名 |
| password | string | "VUnyu33GQ3guVmct" | 邮箱密码 |
| from_name | string | "VLogger 告警系统" | 发件人名称 |
| to_emails | json | ["imzfat@163.com"] | 收件人列表 |
| use_ssl | boolean | true | 是否使用 SSL |

### Filter 黑名单类型

- **tag**: 标签黑名单（默认: china, sports, elections）
- **category**: 分类黑名单
- **description_keyword**: 描述关键词黑名单

## 测试

运行测试脚本验证所有功能：

```bash
python backend/sys_configs/test_config_migration.py
```

测试包括：
1. 数据库初始化测试
2. VLogger 配置读写测试
3. 邮件配置读写测试
4. Filter 黑名单配置测试
5. 已处理事件管理测试
6. VLogger 集成测试
7. Filter 集成测试

## 向后兼容性

所有修改都保持了向后兼容性：
- VLogger 原有的文件配置方式仍然可用
- Filter 原有的函数签名保持不变
- 所有函数都接受 `db_path` 参数，可以手动指定数据库路径

## 文件说明

- **config_manager.py**: 核心配置管理器（单例模式，线程安全）
- **vlogger_config.py**: VLogger 配置访问接口
- **filter_config.py**: Filter 配置访问接口
- **test_config_migration.py**: 配置迁移测试脚本
- **MIGRATION_SUMMARY.md**: 详细的迁移总结文档
- **README.md**: 本文件

## 注意事项

1. **数据库备份**: 定期备份 `system_config.db` 文件
2. **线程安全**: 配置管理器使用单例模式和线程本地存储，确保线程安全
3. **类型转换**: 配置值会根据 `config_type` 字段自动进行类型转换
4. **默认值**: 首次初始化会插入默认配置，后续初始化不会覆盖已有配置

## 更多信息

详细的迁移说明和数据库设计请参考 [MIGRATION_SUMMARY.md](./MIGRATION_SUMMARY.md)。

