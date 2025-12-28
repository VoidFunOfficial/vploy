from .coze_api import chat_with_coze
from ..sys_configs.global_event_reg import vlogger
from ..record.core import RecordManager

def generate_summary_report() -> str:
    """
    生成总结报告

    参数:
        report (str): 报告内容

    返回:
        str: 总结报告
    """
    manager = RecordManager()
    report = manager.get_today_detail_report()
    try:
        response = chat_with_coze(bot_id="7588747127879876671", prompt=str(report))
        return {
            "report": report,
            "summary": response
        }

    except Exception as e:
        vlogger.error("EVT-8067", msg="Coze AI调用失败", error_code="E-SUMMARY-001", extra={"error": str(e)})
        return "unknown"
