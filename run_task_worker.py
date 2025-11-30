"""
Huey任务队列Worker启动脚本

启动Huey worker来处理异步任务和定时任务。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.task_manager import init_task_manager
from backend.vlogger import get_logger


logger = get_logger("task_worker")


def main():
    """主函数"""
    logger.info(
        "TASK_WORKER.START",
        msg="启动任务队列Worker"
    )
    
    logger.info(
        "TASK_WORKER.READY",
        msg="任务队列Worker已就绪"
    )
    
    print("=" * 60)
    print("Huey任务队列Worker已启动")
    print("=" * 60)
    print("\n定时任务:")
    print("  - 健康检查: 每5分钟执行一次节点检测")
    print("  - 健康报告邮件: 每天早上9:00发送")
    print("  - 收益报告邮件: 每天下午18:00发送")
    print("\n按 Ctrl+C 停止Worker")
    print("=" * 60)
    
    # Huey worker会在导入tasks模块时自动启动
    # 这里只需要保持进程运行
    try:
        from backend.task_manager.tasks import huey
        
        # 使用Huey的consumer来运行worker
        from huey.consumer import Consumer
        
        consumer = Consumer(huey)
        consumer.run()
        
    except KeyboardInterrupt:
        logger.info(
            "TASK_WORKER.STOP",
            msg="任务队列Worker已停止"
        )
        print("\n\nWorker已停止")


if __name__ == "__main__":
    main()

