"""
测试mark和analysis处理函数

演示如何使用任务管理系统处理mark和analysis阶段的任务
"""

from .models import AsyncTask, TaskStage, TaskStatus
from .tasks import submit_task, approve_analysis, db
from ..sys_configs.global_event_reg import vlogger


def test_mark_processing():
    """
    测试MARK阶段的PROCESSING处理
    
    创建一个MARK阶段的PROCESSING任务，包含event_id
    """
    vlogger.info("TEST.MARK", msg="开始测试MARK处理")
    
    # 创建MARK任务
    task = AsyncTask(
        stage=TaskStage.MARK,
        status=TaskStatus.PROCESSING,
        metadata={
            "event_id": "test_event_123",  # 替换为真实的event_id
            "description": "测试标记处理"
        }
    )
    
    # 提交任务
    task_id = submit_task(task)
    
    vlogger.info("TEST.MARK", msg=f"已提交MARK任务，ID: {task_id}")
    
    # 等待一段时间后查询任务状态
    import time
    time.sleep(5)
    
    # 查询任务结果
    updated_task = db.get_async_task(task_id)
    
    vlogger.info("TEST.MARK", msg="MARK任务结果", extra={
        "task_id": task_id,
        "status": updated_task.status.value,
        "result": updated_task.result,
        "metadata": updated_task.metadata
    })
    
    return task_id


def test_analysis_processing():
    """
    测试ANALYSIS阶段的PROCESSING处理
    
    创建一个ANALYSIS阶段的PROCESSING任务，包含event_id
    """
    vlogger.info("TEST.ANALYSIS", msg="开始测试ANALYSIS处理")
    
    # 创建ANALYSIS任务
    task = AsyncTask(
        stage=TaskStage.ANALYSIS,
        status=TaskStatus.PROCESSING,
        metadata={
            "event_id": "test_event_123",  # 替换为真实的event_id
            "mark": "test_mark",
            "description": "测试分析处理"
        }
    )
    
    # 提交任务
    task_id = submit_task(task)
    
    vlogger.info("TEST.ANALYSIS", msg=f"已提交ANALYSIS任务，ID: {task_id}")
    
    # 等待一段时间后查询任务状态
    import time
    time.sleep(10)
    
    # 查询任务结果
    updated_task = db.get_async_task(task_id)
    
    vlogger.info("TEST.ANALYSIS", msg="ANALYSIS任务结果", extra={
        "task_id": task_id,
        "status": updated_task.status.value,
        "result": updated_task.result,
        "metadata": updated_task.metadata
    })
    
    return task_id


def test_full_workflow():
    """
    测试完整的MARK -> ANALYSIS工作流

    创建一个MARK任务，等待其转换为ANALYSIS+WAITING，然后批准开始分析
    """
    vlogger.info("TEST.WORKFLOW", msg="开始测试完整工作流")

    # 创建MARK任务
    mark_task = AsyncTask(
        stage=TaskStage.MARK,
        status=TaskStatus.PROCESSING,
        metadata={
            "event_id": "test_event_123",  # 替换为真实的event_id
            "description": "测试完整工作流"
        }
    )

    # 提交MARK任务
    mark_task_id = submit_task(mark_task)

    vlogger.info("TEST.WORKFLOW", msg=f"已提交MARK任务，ID: {mark_task_id}")

    # 等待MARK任务完成并转换为ANALYSIS+WAITING
    import time
    time.sleep(5)

    # 查询任务状态（应该是ANALYSIS+WAITING）
    updated_task = db.get_async_task(mark_task_id)

    vlogger.info("TEST.WORKFLOW", msg="MARK处理后的任务状态", extra={
        "task_id": mark_task_id,
        "stage": updated_task.stage.value,
        "status": updated_task.status.value,
        "result": updated_task.result,
        "metadata": updated_task.metadata
    })

    # 检查是否转换为ANALYSIS+WAITING
    if updated_task.stage == TaskStage.ANALYSIS and updated_task.status == TaskStatus.WAITING:
        vlogger.info("TEST.WORKFLOW", msg="任务已转换为ANALYSIS+WAITING，等待用户批准")

        # 模拟用户批准
        vlogger.info("TEST.WORKFLOW", msg="用户批准分析任务")
        approve_success = approve_analysis(mark_task_id)

        if approve_success:
            vlogger.info("TEST.WORKFLOW", msg="分析任务已批准，开始处理")

            # 等待ANALYSIS任务完成
            time.sleep(600)  # 等待10分钟

            # 查询分析结果
            final_task = db.get_async_task(mark_task_id)

            vlogger.info("TEST.WORKFLOW", msg="ANALYSIS任务结果", extra={
                "task_id": mark_task_id,
                "stage": final_task.stage.value,
                "status": final_task.status.value,
                "result": final_task.result,
                "metadata": final_task.metadata
            })
        else:
            vlogger.error("TEST.WORKFLOW", msg="批准分析任务失败")
    else:
        vlogger.warn("TEST.WORKFLOW", msg="任务状态不正确", extra={
            "expected_stage": TaskStage.ANALYSIS.value,
            "expected_status": TaskStatus.WAITING.value,
            "actual_stage": updated_task.stage.value,
            "actual_status": updated_task.status.value
        })

    return mark_task_id


if __name__ == "__main__":
    # 运行测试
    print("=" * 80)
    print("测试MARK处理函数")
    print("=" * 80)
    test_mark_processing()
    
    print("\n" + "=" * 80)
    print("测试ANALYSIS处理函数")
    print("=" * 80)
    test_analysis_processing()
    
    print("\n" + "=" * 80)
    print("测试完整工作流")
    print("=" * 80)
    test_full_workflow()

