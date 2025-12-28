# 每日投资报告邮件功能

## 功能概述

`generate_daily_report_foremail` 函数用于生成并发送每日投资报告邮件，包含以下内容：

1. **资金状态** - 总资金、可用资金、锁定资金
2. **今日活动** - 新投资、今日盈亏、结算金额、操作次数
3. **持仓情况** - 活跃持仓、已结算持仓
4. **操作记录** - 详细的操作记录表格
5. **AI 总结** - 由 Coze AI 生成的中文总结

## 使用方法

### 基本使用

```python
from backend.record import generate_daily_report_foremail

# 生成并发送每日报告邮件
success = generate_daily_report_foremail()

if success:
    print("邮件发送成功！")
else:
    print("邮件发送失败！")
```

### 在定时任务中使用

可以将此函数集成到定时任务系统中，实现每日自动发送报告：

```python
from backend.task_manager import DynamicScheduler
from backend.record import generate_daily_report_foremail

# 在调度器中注册任务
scheduler = DynamicScheduler()
scheduler.register_task(
    name="daily_investment_report",
    func=generate_daily_report_foremail,
    cron_expr="0 20 * * *"  # 每天晚上8点发送
)
```

## 邮件内容

### HTML 邮件

邮件采用美观的 HTML 格式，包含：

- **响应式设计** - 适配不同设备
- **数据表格** - 清晰展示各项数据
- **颜色标识** - 盈亏用不同颜色标识（绿色为正，红色为负）
- **操作类型标识** - BUY/SELL/SETTLE 用不同颜色区分
- **AI 总结区域** - 特殊样式展示 AI 生成的总结

### 纯文本邮件

同时提供纯文本版本，确保在不支持 HTML 的邮件客户端中也能正常显示。

## 数据来源

1. **基础数据** - 通过 `RecordManager.get_today_detail_report()` 获取
2. **AI 总结** - 通过 `generate_summary_report()` 调用 Coze AI 生成

## 邮件配置

邮件发送使用数据库中的配置，可通过以下方式修改：

```python
from backend.sys_configs import get_email_config, save_email_config

# 获取当前配置
config = get_email_config()

# 修改配置
config['to_emails'] = ['your_email@example.com']
save_email_config(config)
```

## 错误处理

函数包含完整的错误处理机制：

- 数据获取失败时记录错误日志
- 邮件发送失败时记录错误日志
- 所有异常都会被捕获并记录

## 日志记录

函数会记录以下日志事件：

- `DAILY_REPORT.EMAIL.START` - 开始生成报告
- `DAILY_REPORT.EMAIL.SUCCESS` - 邮件发送成功
- `DAILY_REPORT.EMAIL.DATA_ERROR` - 数据获取失败
- `DAILY_REPORT.EMAIL.SEND_FAILED` - 邮件发送失败
- `DAILY_REPORT.EMAIL.ERROR` - 其他异常

## 测试

运行测试脚本：

```bash
python test_daily_report_email.py
```

## 注意事项

1. 确保已正确配置邮件服务器信息
2. 确保 Coze AI API 配置正确
3. 确保数据库中有当日的交易数据
4. 邮件主题格式：`📊 每日投资报告 - {日期}`

