"""
每日投资报告邮件生成模块

生成并发送每日投资报告邮件，包含资金状态、今日活动、持仓情况和AI总结。
"""

from datetime import datetime
from typing import Dict, Any
from ..vlogger.email_helper import email_send_with_db_config
from ..sys_configs.global_event_reg import vlogger


def _generate_fund_status_html(summary: Dict[str, Any]) -> str:
    """
    生成资金状态HTML表格

    参数:
        summary: 总结报告数据

    返回:
        str: HTML表格内容
    """
    total_fund = summary.get('total_fund', 0.0)
    available = summary.get('available_amount', 0.0)
    locked = summary.get('locked_amount', 0.0)

    return f"""
    <table class="data-table">
        <thead>
            <tr>
                <th>项目</th>
                <th>金额</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>总资金</td>
                <td class="amount">${total_fund:.2f}</td>
            </tr>
            <tr>
                <td>可用资金</td>
                <td class="amount">${available:.2f}</td>
            </tr>
            <tr>
                <td>锁定资金</td>
                <td class="amount">${locked:.2f}</td>
            </tr>
        </tbody>
    </table>
    """


def _generate_activity_html(summary: Dict[str, Any]) -> str:
    """
    生成今日活动HTML表格

    参数:
        summary: 总结报告数据

    返回:
        str: HTML表格内容
    """
    new_invest = summary.get('new_invest', 0.0)
    profit_today = summary.get('profit_today', 0.0)
    settled_today = summary.get('settled_today', 0.0)
    operations_count = summary.get('operations_count', 0)

    # 根据盈亏设置颜色
    profit_class = 'profit-positive' if profit_today >= 0 else 'profit-negative'
    profit_sign = '+' if profit_today >= 0 else ''

    return f"""
    <table class="data-table">
        <thead>
            <tr>
                <th>项目</th>
                <th>数值</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>新投资市场</td>
                <td>{new_invest:.0f}</td>
            </tr>
            <tr>
                <td>今日盈亏</td>
                <td class="{profit_class}">{profit_sign}${profit_today:.2f}</td>
            </tr>
            <tr>
                <td>结算金额</td>
                <td>${settled_today:.2f}</td>
            </tr>
            <tr>
                <td>操作次数</td>
                <td>{operations_count}</td>
            </tr>
        </tbody>
    </table>
    """


def _generate_positions_html(summary: Dict[str, Any]) -> str:
    """
    生成持仓情况HTML表格

    参数:
        summary: 总结报告数据

    返回:
        str: HTML表格内容
    """
    active_positions = summary.get('active_positions', 0)
    settled_positions = summary.get('settled_positions', 0)

    return f"""
    <table class="data-table">
        <thead>
            <tr>
                <th>类型</th>
                <th>数量</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>活跃持仓</td>
                <td>{active_positions}</td>
            </tr>
            <tr>
                <td>今日结算</td>
                <td>{settled_positions}</td>
            </tr>
        </tbody>
    </table>
    """


def _generate_operations_html(operations: list) -> str:
    """
    生成操作记录HTML表格

    参数:
        operations: 操作记录列表

    返回:
        str: HTML表格内容
    """
    if not operations:
        return '<p class="no-data">今日暂无操作记录</p>'

    rows = []
    for op in operations:
        market_id = op.get('market_id', 'N/A')
        side = op.get('side', 'N/A')
        operation = op.get('operation', 'N/A')
        price = op.get('price', 0.0)
        shares = op.get('shares', 0)
        tips = op.get('tips', '')
        created_at = op.get('created_at', '')

        # 根据操作类型设置样式
        operation_class = ''
        if operation == 'BUY':
            operation_class = 'operation-buy'
        elif operation == 'SELL':
            operation_class = 'operation-sell'
        elif operation == 'SETTLE':
            operation_class = 'operation-settle'

        rows.append(f"""
            <tr>
                <td>{market_id}</td>
                <td>{side}</td>
                <td class="{operation_class}">{operation}</td>
                <td>${price:.2f}</td>
                <td>{shares}</td>
                <td>{tips}</td>
                <td>{created_at}</td>
            </tr>
        """)

    return f"""
    <table class="data-table operations-table">
        <thead>
            <tr>
                <th>市场ID</th>
                <th>方向</th>
                <th>操作</th>
                <th>价格</th>
                <th>数量</th>
                <th>备注</th>
                <th>时间</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """


def _generate_summary_html(summary_text: str) -> str:
    """
    生成AI总结HTML内容

    参数:
        summary_text: AI生成的总结文本

    返回:
        str: HTML内容
    """
    # 将换行符转换为HTML段落
    paragraphs = summary_text.split('\n\n')
    html_paragraphs = []

    for para in paragraphs:
        if para.strip():
            # 处理单个换行符
            para = para.replace('\n', '<br>')
            html_paragraphs.append(f'<p>{para}</p>')

    return f"""
    <div class="ai-summary">
        {''.join(html_paragraphs)}
    </div>
    """


def _generate_daily_report_html(report_data: Dict[str, Any]) -> str:
    """
    生成完整的每日报告HTML

    参数:
        report_data: 报告数据，包含report和summary字段

    返回:
        str: 完整的HTML邮件内容
    """
    # 提取数据
    report = report_data.get('report', {})
    date = report.get('date', datetime.now().strftime('%Y-%m-%d'))
    summary = report.get('summary', {})
    operations = report.get('operations', [])
    ai_summary = report_data.get('summary', '暂无AI总结')

    # 生成各部分HTML
    fund_status_html = _generate_fund_status_html(summary)
    activity_html = _generate_activity_html(summary)
    positions_html = _generate_positions_html(summary)
    operations_html = _generate_operations_html(operations)
    summary_html = _generate_summary_html(ai_summary)

    # 组装完整HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日投资报告 - {date}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .data-table th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        .data-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .data-table tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        .amount {{
            font-weight: 600;
            color: #2c3e50;
        }}
        .profit-positive {{
            color: #27ae60;
            font-weight: 600;
        }}
        .profit-negative {{
            color: #e74c3c;
            font-weight: 600;
        }}
        .operation-buy {{
            color: #27ae60;
            font-weight: 600;
        }}
        .operation-sell {{
            color: #e67e22;
            font-weight: 600;
        }}
        .operation-settle {{
            color: #3498db;
            font-weight: 600;
        }}
        .operations-table {{
            font-size: 0.9em;
        }}
        .ai-summary {{
            background-color: #ecf0f1;
            border-left: 4px solid #9b59b6;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
            line-height: 1.8;
        }}
        .ai-summary p {{
            margin: 10px 0;
        }}
        .no-data {{
            text-align: center;
            color: #95a5a6;
            padding: 20px;
            font-style: italic;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 每日投资报告 - {date}</h1>

        <h2>💰 资金状态</h2>
        {fund_status_html}

        <h2>📈 今日活动</h2>
        {activity_html}

        <h2>📦 持仓情况</h2>
        {positions_html}

        <h2>📝 操作记录</h2>
        {operations_html}

        <h2>🤖 AI 总结</h2>
        {summary_html}

        <div class="footer">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>VoidPoly 投资管理系统 | Powered by VLogger</p>
        </div>
    </div>
</body>
</html>"""

    return html


def _generate_plain_text_report(report_data: Dict[str, Any]) -> str:
    """
    生成纯文本报告（用于邮件的纯文本部分）

    参数:
        report_data: 报告数据

    返回:
        str: 纯文本内容
    """
    report = report_data.get('report', {})
    date = report.get('date', datetime.now().strftime('%Y-%m-%d'))
    summary = report.get('summary', {})
    operations = report.get('operations', [])
    ai_summary = report_data.get('summary', '暂无AI总结')

    lines = [
        "=" * 60,
        f"每日投资报告 - {date}",
        "=" * 60,
        "",
        "【资金状态】",
        f"  总资金:     ${summary.get('total_fund', 0.0):.2f}",
        f"  可用资金:   ${summary.get('available_amount', 0.0):.2f}",
        f"  锁定资金:   ${summary.get('locked_amount', 0.0):.2f}",
        "",
        "【今日活动】",
        f"  新投资市场: {summary.get('new_invest', 0.0):.0f}",
        f"  今日盈亏:   ${summary.get('profit_today', 0.0):.2f}",
        f"  结算金额:   ${summary.get('settled_today', 0.0):.2f}",
        f"  操作次数:   {summary.get('operations_count', 0)}",
        "",
        "【持仓情况】",
        f"  活跃持仓:   {summary.get('active_positions', 0)}",
        f"  今日结算:   {summary.get('settled_positions', 0)}",
        "",
        "【操作记录】"
    ]

    if operations:
        for i, op in enumerate(operations, 1):
            lines.append(f"  {i}. {op.get('operation', 'N/A')} | "
                        f"市场:{op.get('market_id', 'N/A')} | "
                        f"方向:{op.get('side', 'N/A')} | "
                        f"价格:${op.get('price', 0.0):.2f} | "
                        f"数量:{op.get('shares', 0)}")
    else:
        lines.append("  暂无操作记录")

    lines.extend([
        "",
        "【AI 总结】",
        ai_summary,
        "",
        "=" * 60,
        f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "VoidPoly 投资管理系统 | Powered by VLogger",
        "=" * 60
    ])

    return "\n".join(lines)


def generate_daily_report_foremail() -> bool:
    """
    生成并发送每日投资报告邮件

    返回:
        bool: 邮件发送是否成功
    """
    try:
        # 延迟导入以避免循环依赖
        from ..ai_analysis import generate_summary_report

        vlogger.info(
            "DAILY_REPORT.EMAIL.START",
            msg="开始生成每日投资报告邮件"
        )

        # 1. 获取数据
        report_data = generate_summary_report()

        # 检查是否获取到有效数据
        if report_data == "unknown" or not isinstance(report_data, dict):
            vlogger.error(
                "DAILY_REPORT.EMAIL.DATA_ERROR",
                msg="获取报告数据失败",
                error_code="E-DAILY-REPORT-001"
            )
            return False

        # 2. 生成HTML和纯文本内容
        html_content = _generate_daily_report_html(report_data)
        text_content = _generate_plain_text_report(report_data)

        # 3. 发送邮件
        date = report_data.get('report', {}).get('date', datetime.now().strftime('%Y-%m-%d'))
        success = email_send_with_db_config(
            subject=f"📊 每日投资报告 - {date}",
            body_text=text_content,
            body_html=html_content
        )

        if success:
            vlogger.info(
                "DAILY_REPORT.EMAIL.SUCCESS",
                msg="每日投资报告邮件发送成功",
                extra={"date": date}
            )
        else:
            vlogger.error(
                "DAILY_REPORT.EMAIL.SEND_FAILED",
                msg="每日投资报告邮件发送失败",
                error_code="E-DAILY-REPORT-002",
                extra={"date": date}
            )

        return success

    except Exception as e:
        vlogger.error(
            "DAILY_REPORT.EMAIL.ERROR",
            msg="生成或发送每日投资报告邮件时发生异常",
            error_code="E-DAILY-REPORT-003",
            extra={"error": str(e)}
        )
        return False
