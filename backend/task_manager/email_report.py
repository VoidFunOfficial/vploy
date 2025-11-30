"""
邮件报告生成模块

生成健康检查报告的HTML邮件和可视化图表。
"""

import base64
from io import BytesIO
from typing import Dict, Any, List
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非GUI后端
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # 配置matplotlib以避免中文字体警告
    # 使用英文标签或者配置中文字体
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..vlogger import get_logger
from .health_check import NodeStats


logger = get_logger("email_report")


# ==================== 图表生成 ====================

def get_latency_color(latency_ms: float) -> str:
    """
    根据延迟获取颜色

    参数:
        latency_ms: 延迟时间（毫秒）

    返回:
        str: 颜色代码
    """
    if latency_ms < 500:
        return '#28a745'  # 绿色 - 良好
    elif latency_ms < 1000:
        return '#ffc107'  # 黄色 - 一般
    elif latency_ms < 2000:
        return '#fd7e14'  # 橙色 - 较慢
    else:
        return '#dc3545'  # 红色 - 严重


def generate_latency_chart(stats_list: List[NodeStats], title: str = "Node Latency Statistics") -> str:
    """
    生成延迟柱状图（base64编码）

    参数:
        stats_list: 节点统计数据列表
        title: 图表标题

    返回:
        str: base64编码的图片数据
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.warn(
            "EMAIL_REPORT.CHART.MATPLOTLIB_UNAVAILABLE",
            msg="matplotlib未安装，无法生成图表"
        )
        return ""

    if not stats_list:
        logger.warn(
            "EMAIL_REPORT.CHART.NO_DATA",
            msg="没有数据可生成图表"
        )
        return ""

    try:
        # 准备数据
        node_names = [stat.node_url.replace("https://", "").replace("http://", "").rstrip("/")
                      for stat in stats_list]
        avg_latencies = [stat.avg_latency for stat in stats_list]
        colors = [get_latency_color(lat) for lat in avg_latencies]

        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 6))

        # 绘制柱状图
        bars = ax.bar(range(len(node_names)), avg_latencies, color=colors, alpha=0.8)

        # 设置标签（使用英文避免字体问题）
        ax.set_xlabel('API Nodes', fontsize=12)
        ax.set_ylabel('Avg Latency (ms)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(node_names)))
        ax.set_xticklabels(node_names, rotation=15, ha='right', fontsize=9)

        # 在柱子上显示数值
        for i, (bar, latency) in enumerate(zip(bars, avg_latencies)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{latency:.1f}ms',
                   ha='center', va='bottom', fontsize=10)

        # 添加网格线
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#28a745', label='Good (<500ms)'),
            Patch(facecolor='#ffc107', label='Fair (500-1000ms)'),
            Patch(facecolor='#fd7e14', label='Slow (1000-2000ms)'),
            Patch(facecolor='#dc3545', label='Critical (>=2000ms)')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        # 调整布局
        plt.tight_layout()

        # 保存到内存
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)

        # 转换为base64
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        plt.close(fig)

        logger.info(
            "EMAIL_REPORT.CHART.GENERATED",
            msg="延迟图表生成成功",
            extra={"node_count": len(stats_list)}
        )

        return image_base64

    except Exception as e:
        logger.error(
            "EMAIL_REPORT.CHART.FAILED",
            msg="生成图表失败",
            error_code="E-REPORT-001",
            extra={"error": str(e)}
        )
        return ""


# ==================== HTML模板 ====================

def generate_stats_table_html(stats_list: List[NodeStats]) -> str:
    """
    生成统计数据表格HTML

    参数:
        stats_list: 节点统计数据列表

    返回:
        str: HTML表格
    """
    if not stats_list:
        return "<p>暂无数据</p>"

    rows_html = ""
    for stat in stats_list:
        node_name = stat.node_url.replace("https://", "").replace("http://", "").rstrip("/")

        # 根据延迟设置行颜色
        if stat.avg_latency < 500:
            row_class = "success"
        elif stat.avg_latency < 1000:
            row_class = "warning"
        elif stat.avg_latency < 2000:
            row_class = "orange"
        else:
            row_class = "danger"

        rows_html += f"""
        <tr class="{row_class}">
            <td>{node_name}</td>
            <td>{stat.avg_latency:.2f} ms</td>
            <td>{stat.max_latency:.2f} ms</td>
            <td>{stat.min_latency:.2f} ms</td>
            <td>{stat.success_rate * 100:.1f}%</td>
            <td>{stat.successful_checks}/{stat.total_checks}</td>
        </tr>
        """

    table_html = f"""
    <table class="stats-table">
        <thead>
            <tr>
                <th>节点</th>
                <th>平均延迟</th>
                <th>最大延迟</th>
                <th>最小延迟</th>
                <th>成功率</th>
                <th>检测次数</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    return table_html


def generate_health_report_html(report_data: Dict[str, Any]) -> str:
    """
    生成健康检查报告HTML

    参数:
        report_data: 报告数据

    返回:
        str: HTML内容
    """
    # 生成图表
    chart_12h_base64 = ""
    chart_72h_base64 = ""

    if "12_hours" in report_data and report_data["12_hours"]["nodes"]:
        stats_12h = [NodeStats(**node) for node in report_data["12_hours"]["nodes"]]
        chart_12h_base64 = generate_latency_chart(stats_12h, "Last 12 Hours - Node Latency")

    if "72_hours" in report_data and report_data["72_hours"]["nodes"]:
        stats_72h = [NodeStats(**node) for node in report_data["72_hours"]["nodes"]]
        chart_72h_base64 = generate_latency_chart(stats_72h, "Last 3 Days - Node Latency")

    # 生成表格
    table_12h_html = ""
    table_72h_html = ""

    if "12_hours" in report_data and report_data["12_hours"]["nodes"]:
        stats_12h = [NodeStats(**node) for node in report_data["12_hours"]["nodes"]]
        table_12h_html = generate_stats_table_html(stats_12h)

    if "72_hours" in report_data and report_data["72_hours"]["nodes"]:
        stats_72h = [NodeStats(**node) for node in report_data["72_hours"]["nodes"]]
        table_72h_html = generate_stats_table_html(stats_72h)

    # 生成图表HTML片段
    chart_12h_html = f'<div class="chart-container"><img src="data:image/png;base64,{chart_12h_base64}" alt="近12小时延迟图表"></div>' if chart_12h_base64 else ''
    chart_72h_html = f'<div class="chart-container"><img src="data:image/png;base64,{chart_72h_base64}" alt="近3天延迟图表"></div>' if chart_72h_base64 else ''

    # 生成完整HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1000px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }}
        .container {{ background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 30px; }}
        h2 {{ color: #34495e; margin-top: 30px; margin-bottom: 15px; border-left: 4px solid #3498db; padding-left: 10px; }}
        .stats-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .stats-table th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; font-weight: bold; }}
        .stats-table td {{ padding: 10px 12px; border-bottom: 1px solid #ddd; }}
        .stats-table tr:hover {{ background-color: #f8f9fa; }}
        .stats-table tr.success {{ background-color: #d4edda; }}
        .stats-table tr.warning {{ background-color: #fff3cd; }}
        .stats-table tr.orange {{ background-color: #ffe5cc; }}
        .stats-table tr.danger {{ background-color: #f8d7da; }}
        .chart-container {{ text-align: center; margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; }}
        .chart-container img {{ max-width: 100%; height: auto; border-radius: 4px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #7f8c8d; font-size: 14px; }}
        .legend {{ display: flex; justify-content: center; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 API节点健康检查报告</h1>
        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background-color: #28a745;"></div><span>良好 (&lt;500ms)</span></div>
            <div class="legend-item"><div class="legend-color" style="background-color: #ffc107;"></div><span>一般 (500-1000ms)</span></div>
            <div class="legend-item"><div class="legend-color" style="background-color: #fd7e14;"></div><span>较慢 (1000-2000ms)</span></div>
            <div class="legend-item"><div class="legend-color" style="background-color: #dc3545;"></div><span>严重 (≥2000ms)</span></div>
        </div>
        <h2>📊 近12小时统计</h2>
        {chart_12h_html}
        {table_12h_html}
        <h2>📈 近3天统计</h2>
        {chart_72h_html}
        {table_72h_html}
        <div class="footer">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>VoidPoly 健康检查系统 | Powered by VLogger</p>
        </div>
    </div>
</body>
</html>"""

    return html



def generate_plain_text_report(report_data: Dict[str, Any]) -> str:
    """
    生成纯文本报告（用于邮件的纯文本部分）

    参数:
        report_data: 报告数据

    返回:
        str: 纯文本内容
    """
    lines = [
        "=" * 60,
        "API节点健康检查报告",
        "=" * 60,
        ""
    ]

    # 近12小时统计
    if "12_hours" in report_data and report_data["12_hours"]["nodes"]:
        lines.append("【近12小时统计】")
        lines.append("-" * 60)

        for node_data in report_data["12_hours"]["nodes"]:
            stat = NodeStats(**node_data)
            node_name = stat.node_url.replace("https://", "").replace("http://", "").rstrip("/")

            lines.append(f"节点: {node_name}")
            lines.append(f"  平均延迟: {stat.avg_latency:.2f} ms")
            lines.append(f"  最大延迟: {stat.max_latency:.2f} ms")
            lines.append(f"  最小延迟: {stat.min_latency:.2f} ms")
            lines.append(f"  成功率: {stat.success_rate * 100:.1f}%")
            lines.append(f"  检测次数: {stat.successful_checks}/{stat.total_checks}")
            lines.append("")

    # 近3天统计
    if "72_hours" in report_data and report_data["72_hours"]["nodes"]:
        lines.append("【近3天统计】")
        lines.append("-" * 60)

        for node_data in report_data["72_hours"]["nodes"]:
            stat = NodeStats(**node_data)
            node_name = stat.node_url.replace("https://", "").replace("http://", "").rstrip("/")

            lines.append(f"节点: {node_name}")
            lines.append(f"  平均延迟: {stat.avg_latency:.2f} ms")
            lines.append(f"  最大延迟: {stat.max_latency:.2f} ms")
            lines.append(f"  最小延迟: {stat.min_latency:.2f} ms")
            lines.append(f"  成功率: {stat.success_rate * 100:.1f}%")
            lines.append(f"  检测次数: {stat.successful_checks}/{stat.total_checks}")
            lines.append("")

    lines.append("=" * 60)
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("VoidPoly 健康检查系统 | Powered by VLogger")
    lines.append("=" * 60)

    return "\n".join(lines)

    return html

