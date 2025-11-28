"""
VoidPoly 核心调度器模块

核心调度器负责:
1. 维护监听序列(watching sequence list),跟踪所有需要监控的交易序列
2. 通过 sequence_manager 进行原子级任务管理和状态追踪
3. 持续监听每个 sequence 的状态变化,并根据状态分发到对应的处理函数
4. 定义处理函数接口规范(trade、decision、analysis等)
5. 在处理函数执行后更新对应 sequence 的状态

技术特性:
- 使用 VLogger 进行日志记录
- 线程安全和原子性操作
- 完整的异常处理和错误恢复机制
- 清晰的代码结构,便于后续扩展
"""

import time
import threading
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

# 导入 VLogger
try:
    from ..sys_configs.global_event_reg import vlogger
except ImportError:
    from backend.sys_configs.global_event_reg import vlogger

# 导入 SequenceManager
try:
    from ..sequence_manager import get_sequence_manager, SequenceManager
except ImportError:
    from backend.sequence_manager import get_sequence_manager, SequenceManager

# 导入持仓监听配置
try:
    from ..sys_configs.position_listen_config import get_position_listen_list
except ImportError:
    from backend.sys_configs.position_listen_config import get_position_listen_list


# ==================== 序列状态枚举 ====================

class SequenceState(str, Enum):
    """
    序列状态枚举

    状态流转:
        MARKING -> ANALYSIS -> DECISION -> TRADING -> MONITORING -> COMPLETED
                                                                 -> FAILED
    """
    MARKING = "MARKING"           # 标记中: 新创建的序列,等待标记处理
    ANALYSIS = "ANALYSIS"         # 分析中: 正在进行AI分析
    DECISION = "DECISION"         # 决策中: 正在进行交易决策
    TRADING = "TRADING"           # 交易中: 正在执行交易
    MONITORING = "MONITORING"     # 监控中: 持仓监控阶段
    COMPLETED = "COMPLETED"       # 已完成: 序列处理完成
    FAILED = "FAILED"             # 失败: 处理过程中出现错误


# ==================== 监听序列数据结构 ====================

@dataclass
class WatchingSequence:
    """
    监听序列数据结构

    属性:
        sequence_id: 序列唯一标识符
        market_id: 市场ID
        state: 当前状态
        mark: 标记信息(用于标识序列的特殊属性或分类)
        data: 序列相关数据(事件数据、分析结果、交易指令等)
        created_at: 创建时间
        updated_at: 最后更新时间
        retry_count: 重试次数
        error_message: 错误信息(如果有)
        metadata: 额外元数据
    """
    sequence_id: int
    market_id: str
    state: SequenceState = SequenceState.MARKING
    mark: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)



# ==================== 核心调度器 ====================

class VCoreScheduler:
    """
    VoidPoly 核心调度器

    功能:
        - 维护监听序列列表
        - 持续监听序列状态变化
        - 根据状态分发到对应的处理函数
        - 更新序列状态
        - 异常处理和错误恢复
    """

    def __init__(
        self,
        polling_interval: int = 10,      # 轮询间隔(秒)
        max_retry: int = 3,              # 最大重试次数
        enable_auto_start: bool = False  # 是否自动启动调度器
    ):
        """
        初始化核心调度器

        参数:
            polling_interval: 轮询间隔(秒)
            max_retry: 最大重试次数
            enable_auto_start: 是否自动启动调度器
        """
        self.polling_interval = polling_interval
        self.max_retry = max_retry

        # 监听序列字典: {sequence_id: WatchingSequence}
        self.watching_sequences: Dict[int, WatchingSequence] = {}

        # 线程安全锁
        self._lock = threading.Lock()

        # 调度器运行状态
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None

        # 获取 SequenceManager 实例
        self.seq_manager = get_sequence_manager()

        vlogger.info("VCORE.SCHEDULER.INIT", msg="核心调度器初始化完成", extra={
            "polling_interval": polling_interval,
            "max_retry": max_retry,
            "enable_auto_start": enable_auto_start
        })

        if enable_auto_start:
            self.start()

    def start(self):
        """启动调度器"""
        if self._running:
            vlogger.warn("VCORE.SCHEDULER.ALREADY_RUNNING", msg="调度器已在运行中")
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

        vlogger.info("VCORE.SCHEDULER.START", msg="核心调度器已启动")

    def stop(self):
        """停止调度器"""
        if not self._running:
            vlogger.warn("VCORE.SCHEDULER.NOT_RUNNING", msg="调度器未在运行")
            return

        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=30)

        vlogger.info("VCORE.SCHEDULER.STOP", msg="核心调度器已停止")

    def _scheduler_loop(self):
        """调度器主循环"""
        vlogger.info("VCORE.SCHEDULER.LOOP_START", msg="调度器主循环开始")

        while self._running:
            try:
                # 从持仓监听列表加载活跃的序列
                self._load_active_sequences()

                # 处理所有监听序列
                self._process_all_sequences()

                # 等待下一次轮询
                time.sleep(self.polling_interval)

            except Exception as e:
                vlogger.error("VCORE.SCHEDULER.LOOP_ERROR", msg="调度器主循环异常",
                             error_code="E-VCORE-001", extra={
                    "error": str(e)
                })
                # 发生异常后等待一段时间再继续
                time.sleep(self.polling_interval)

        vlogger.info("VCORE.SCHEDULER.LOOP_END", msg="调度器主循环结束")

    def _load_active_sequences(self):
        """从持仓监听列表加载活跃的序列"""
        try:
            # 获取所有活跃的持仓监听记录
            active_positions = get_position_listen_list(is_active=True)

            with self._lock:
                # 获取当前已存在的 market_id 集合
                existing_market_ids = {seq.market_id for seq in self.watching_sequences.values()}

                # 添加新的监听序列
                for position in active_positions:
                    market_id = position['market_id']

                    # 如果该 market_id 还未在监听列表中,则添加
                    if market_id not in existing_market_ids:
                        # 获取下一个序列号
                        seq_id = self.seq_manager.get_next_sequence(
                            'position_sequence',
                            result=f'监控市场 {market_id}'
                        )

                        # 创建监听序列
                        watching_seq = WatchingSequence(
                            sequence_id=seq_id,
                            market_id=market_id,
                            state=SequenceState.MONITORING,
                            mark=position.get('marks'),  # 使用持仓的 marks 作为 mark
                            data={
                                'position_id': position['id'],
                                'buy_price': position['buy_price'],
                                'buy_side': position['buy_side'],
                                'shares': position['shares']
                            },
                            metadata={'source': 'position_listen_list'}
                        )

                        self.watching_sequences[seq_id] = watching_seq

                        vlogger.info("VCORE.SEQUENCE.ADDED", msg="添加新的监听序列", extra={
                            "sequence_id": seq_id,
                            "market_id": market_id,
                            "state": SequenceState.MONITORING
                        })

        except Exception as e:
            vlogger.error("VCORE.LOAD_SEQUENCES_ERROR", msg="加载活跃序列失败",
                         error_code="E-VCORE-002", extra={
                "error": str(e)
            })

    def _process_all_sequences(self):
        """处理所有监听序列"""
        with self._lock:
            sequences_to_process = list(self.watching_sequences.values())

        for sequence in sequences_to_process:
            try:
                self._process_sequence(sequence)
            except Exception as e:
                vlogger.error("VCORE.PROCESS_SEQUENCE_ERROR", msg="处理序列异常",
                             error_code="E-VCORE-003", extra={
                    "sequence_id": sequence.sequence_id,
                    "market_id": sequence.market_id,
                    "state": sequence.state,
                    "error": str(e)
                })

                # 更新序列状态为失败
                self._update_sequence_state(
                    sequence,
                    SequenceState.FAILED,
                    error_message=str(e)
                )

    def _process_sequence(self, sequence: WatchingSequence):
        """
        处理单个序列,根据状态分发到对应的处理函数

        参数:
            sequence: 监听序列对象
        """
        vlogger.debug("VCORE.PROCESS_SEQUENCE", msg="处理序列", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id,
            "state": sequence.state
        })

        # 根据状态分发到对应的处理函数
        if sequence.state == SequenceState.MARKING:
            self._handle_marking(sequence)
        elif sequence.state == SequenceState.ANALYSIS:
            self._handle_analysis(sequence)
        elif sequence.state == SequenceState.DECISION:
            self._handle_decision(sequence)
        elif sequence.state == SequenceState.TRADING:
            self._handle_trading(sequence)
        elif sequence.state == SequenceState.MONITORING:
            self._handle_monitoring(sequence)
        elif sequence.state == SequenceState.COMPLETED:
            self._handle_completed(sequence)
        elif sequence.state == SequenceState.FAILED:
            self._handle_failed(sequence)
        else:
            vlogger.warn("VCORE.UNKNOWN_STATE", msg="未知的序列状态", extra={
                "sequence_id": sequence.sequence_id,
                "state": sequence.state
            })

    def _update_sequence_state(
        self,
        sequence: WatchingSequence,
        new_state: SequenceState,
        data_update: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """
        更新序列状态

        参数:
            sequence: 监听序列对象
            new_state: 新状态
            data_update: 数据更新(可选)
            error_message: 错误信息(可选)
        """
        with self._lock:
            old_state = sequence.state
            sequence.state = new_state
            sequence.updated_at = time.time()

            if data_update:
                sequence.data.update(data_update)

            if error_message:
                sequence.error_message = error_message

            # 更新 sequence_manager 中的记录
            self.seq_manager.reset_sequence(
                'position_sequence',
                value=sequence.sequence_id,
                result=f'状态: {old_state} -> {new_state}'
            )

            vlogger.info("VCORE.STATE_UPDATE", msg="序列状态更新", extra={
                "sequence_id": sequence.sequence_id,
                "market_id": sequence.market_id,
                "old_state": old_state,
                "new_state": new_state,
                "error_message": error_message
            })

    def add_sequence(
        self,
        market_id: str,
        initial_state: SequenceState = SequenceState.MARKING,
        mark: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        手动添加监听序列

        参数:
            market_id: 市场ID
            initial_state: 初始状态
            mark: 标记信息
            data: 序列数据
            metadata: 元数据

        返回:
            int: 序列ID
        """
        # 获取下一个序列号
        seq_id = self.seq_manager.get_next_sequence(
            'position_sequence',
            result=f'手动添加市场 {market_id}'
        )

        # 创建监听序列
        watching_seq = WatchingSequence(
            sequence_id=seq_id,
            market_id=market_id,
            state=initial_state,
            mark=mark,
            data=data or {},
            metadata=metadata or {}
        )

        with self._lock:
            self.watching_sequences[seq_id] = watching_seq

        vlogger.info("VCORE.SEQUENCE.MANUAL_ADD", msg="手动添加监听序列", extra={
            "sequence_id": seq_id,
            "market_id": market_id,
            "initial_state": initial_state
        })

        return seq_id

    def remove_sequence(self, sequence_id: int) -> bool:
        """
        移除监听序列

        参数:
            sequence_id: 序列ID

        返回:
            bool: 是否移除成功
        """
        with self._lock:
            if sequence_id in self.watching_sequences:
                sequence = self.watching_sequences.pop(sequence_id)

                vlogger.info("VCORE.SEQUENCE.REMOVED", msg="移除监听序列", extra={
                    "sequence_id": sequence_id,
                    "market_id": sequence.market_id,
                    "state": sequence.state
                })

                return True
            else:
                vlogger.warn("VCORE.SEQUENCE.NOT_FOUND", msg="序列不存在", extra={
                    "sequence_id": sequence_id
                })
                return False

    def get_sequence_status(self, sequence_id: int) -> Optional[Dict[str, Any]]:
        """
        获取序列状态

        参数:
            sequence_id: 序列ID

        返回:
            dict: 序列状态信息,如果不存在则返回 None
        """
        with self._lock:
            if sequence_id in self.watching_sequences:
                sequence = self.watching_sequences[sequence_id]
                return {
                    'sequence_id': sequence.sequence_id,
                    'market_id': sequence.market_id,
                    'state': sequence.state,
                    'mark': sequence.mark,
                    'created_at': sequence.created_at,
                    'updated_at': sequence.updated_at,
                    'retry_count': sequence.retry_count,
                    'error_message': sequence.error_message,
                    'data': sequence.data,
                    'metadata': sequence.metadata
                }
            else:
                return None

    def list_all_sequences(self) -> List[Dict[str, Any]]:
        """
        列出所有监听序列

        返回:
            list: 所有序列的状态信息列表
        """
        with self._lock:
            return [
                {
                    'sequence_id': seq.sequence_id,
                    'market_id': seq.market_id,
                    'state': seq.state,
                    'mark': seq.mark,
                    'created_at': seq.created_at,
                    'updated_at': seq.updated_at,
                    'retry_count': seq.retry_count,
                    'error_message': seq.error_message
                }
                for seq in self.watching_sequences.values()
            ]


    # ==================== 状态处理函数接口 ====================
    # 以下函数定义了各个状态的处理逻辑接口
    # 当前阶段只提供占位符实现,后续可扩展具体业务逻辑

    def _handle_marking(self, sequence: WatchingSequence):
        """
        处理 MARKING 状态的序列

        业务逻辑(待实现):
            - 处理序列的标记信息
            - 根据 mark 进行分类或特殊处理
            - 初始化序列数据
            - 准备进入分析阶段

        参数:
            sequence: 监听序列对象
        """
        vlogger.info("VCORE.HANDLE.MARKING", msg="处理 MARKING 状态序列", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id,
            "mark": sequence.mark
        })

        # TODO: 实现具体的 MARKING 状态处理逻辑
        # 示例:
        # - 根据 mark 进行不同的处理路径
        # - 验证 mark 的有效性
        # - 初始化相关数据
        # if sequence.mark == "high_priority":
        #     # 高优先级处理
        #     pass
        # elif sequence.mark == "low_priority":
        #     # 低优先级处理
        #     pass

        # 占位符: 直接转换到 ANALYSIS 状态
        self._update_sequence_state(sequence, SequenceState.ANALYSIS)

    def _handle_analysis(self, sequence: WatchingSequence):
        """
        处理 ANALYSIS 状态的序列

        业务逻辑(待实现):
            - 调用 AI 分析模块进行深度分析
            - 获取分析结果(p值、a值等)
            - 将分析结果存储到序列数据中

        参数:
            sequence: 监听序列对象
        """
        vlogger.info("VCORE.HANDLE.ANALYSIS", msg="处理 ANALYSIS 状态序列", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id
        })

        # TODO: 实现具体的 AI 分析逻辑
        # 示例:
        # from backend.ai_analysis import AnalysisTaskManager
        # task_manager = AnalysisTaskManager(cookie_string="...")
        # result = await task_manager.submit_analysis_task(sequence.data['event_summary'])
        # self._update_sequence_state(
        #     sequence,
        #     SequenceState.DECISION,
        #     data_update={'analysis_result': result}
        # )

        # 占位符: 直接转换到 DECISION 状态
        self._update_sequence_state(sequence, SequenceState.DECISION)

    def _handle_decision(self, sequence: WatchingSequence):
        """
        处理 DECISION 状态的序列

        业务逻辑(待实现):
            - 调用 auto_decision 模块进行交易决策
            - 基于 AI 分析结果计算最优仓位
            - 生成交易指令

        参数:
            sequence: 监听序列对象
        """
        vlogger.info("VCORE.HANDLE.DECISION", msg="处理 DECISION 状态序列", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id
        })

        # TODO: 实现具体的决策逻辑
        # 示例:
        # from backend.auto_decision import allocate_optimal_positions_pro
        # instructions = allocate_optimal_positions_pro(
        #     gamma_markets=[sequence.data['market']],
        #     ai_analysis=sequence.data['analysis_result'],
        #     M_cents=50000,
        #     kappa=0.7,
        #     xi=0.5
        # )
        # self._update_sequence_state(
        #     sequence,
        #     SequenceState.TRADING,
        #     data_update={'trade_instructions': instructions}
        # )

        # 占位符: 直接转换到 TRADING 状态
        self._update_sequence_state(sequence, SequenceState.TRADING)

    def _handle_trading(self, sequence: WatchingSequence):
        """
        处理 TRADING 状态的序列

        业务逻辑(待实现):
            - 调用 auto_trade 模块执行交易
            - 分析订单簿和滑点
            - 提交限价单
            - 记录交易结果

        参数:
            sequence: 监听序列对象
        """
        vlogger.info("VCORE.HANDLE.TRADING", msg="处理 TRADING 状态序列", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id
        })

        # TODO: 实现具体的交易执行逻辑
        # 示例:
        # from backend.auto_trade import AutoTrader
        # with AutoTrader() as trader:
        #     execution = trader.execute_trade(sequence.data['trade_instructions'][0])
        #     if execution.success:
        #         self._update_sequence_state(
        #             sequence,
        #             SequenceState.MONITORING,
        #             data_update={'execution_result': execution}
        #         )
        #     else:
        #         self._update_sequence_state(
        #             sequence,
        #             SequenceState.FAILED,
        #             error_message=execution.error_message
        #         )

        # 占位符: 直接转换到 MONITORING 状态
        self._update_sequence_state(sequence, SequenceState.MONITORING)

    def _handle_monitoring(self, sequence: WatchingSequence):
        """
        处理 MONITORING 状态的序列

        业务逻辑(待实现):
            - 监控持仓状态
            - 检查止盈止损条件
            - 判断是否需要平仓
            - 更新持仓信息

        参数:
            sequence: 监听序列对象
        """
        vlogger.debug("VCORE.HANDLE.MONITORING", msg="处理 MONITORING 状态序列", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id
        })

        # TODO: 实现具体的持仓监控逻辑
        # 示例:
        # from backend.polymarket_api import PolymarketOrderbookClient
        # with PolymarketOrderbookClient() as client:
        #     current_price = client.get_market_price(sequence.market_id)
        #     buy_price = sequence.data['buy_price']
        #     buy_side = sequence.data['buy_side']
        #
        #     # 检查止盈止损条件
        #     if should_close_position(current_price, buy_price, buy_side):
        #         # 执行平仓操作
        #         self._update_sequence_state(sequence, SequenceState.COMPLETED)

        # 占位符: 保持在 MONITORING 状态,等待条件触发
        pass

    def _handle_completed(self, sequence: WatchingSequence):
        """
        处理 COMPLETED 状态的序列

        业务逻辑(待实现):
            - 记录完成信息
            - 清理资源
            - 从监听列表中移除

        参数:
            sequence: 监听序列对象
        """
        vlogger.info("VCORE.HANDLE.COMPLETED", msg="处理 COMPLETED 状态序列", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id
        })

        # TODO: 实现具体的完成处理逻辑
        # 示例:
        # - 更新数据库中的持仓状态
        # - 记录收益信息
        # - 发送通知

        # 占位符: 从监听列表中移除该序列
        self.remove_sequence(sequence.sequence_id)

    def _handle_failed(self, sequence: WatchingSequence):
        """
        处理 FAILED 状态的序列

        业务逻辑(待实现):
            - 记录失败信息
            - 判断是否需要重试
            - 发送告警通知

        参数:
            sequence: 监听序列对象
        """
        vlogger.error("VCORE.HANDLE.FAILED", msg="处理 FAILED 状态序列",
                     error_code="E-VCORE-004", extra={
            "sequence_id": sequence.sequence_id,
            "market_id": sequence.market_id,
            "error_message": sequence.error_message,
            "retry_count": sequence.retry_count
        })

        # TODO: 实现具体的失败处理逻辑
        # 示例:
        # if sequence.retry_count < self.max_retry:
        #     # 重试: 重置状态到 MARKING
        #     sequence.retry_count += 1
        #     self._update_sequence_state(sequence, SequenceState.MARKING)
        # else:
        #     # 达到最大重试次数,从监听列表中移除
        #     self.remove_sequence(sequence.sequence_id)

        # 占位符: 检查重试次数
        if sequence.retry_count < self.max_retry:
            sequence.retry_count += 1
            vlogger.info("VCORE.RETRY", msg="重试失败的序列", extra={
                "sequence_id": sequence.sequence_id,
                "retry_count": sequence.retry_count
            })
            # 重置到 MARKING 状态
            self._update_sequence_state(sequence, SequenceState.MARKING)
        else:
            vlogger.error("VCORE.MAX_RETRY_REACHED", msg="达到最大重试次数",
                         error_code="E-VCORE-005", extra={
                "sequence_id": sequence.sequence_id,
                "max_retry": self.max_retry
            })
            # 从监听列表中移除
            self.remove_sequence(sequence.sequence_id)



# ==================== 全局实例和辅助函数 ====================

# 全局调度器实例
_scheduler_instance: Optional[VCoreScheduler] = None
_scheduler_lock = threading.Lock()


def get_scheduler(
    polling_interval: int = 10,
    max_retry: int = 3,
    enable_auto_start: bool = False
) -> VCoreScheduler:
    """
    获取核心调度器实例(单例模式)

    参数:
        polling_interval: 轮询间隔(秒)
        max_retry: 最大重试次数
        enable_auto_start: 是否自动启动调度器

    返回:
        VCoreScheduler: 调度器实例
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        with _scheduler_lock:
            if _scheduler_instance is None:
                _scheduler_instance = VCoreScheduler(
                    polling_interval=polling_interval,
                    max_retry=max_retry,
                    enable_auto_start=enable_auto_start
                )

    return _scheduler_instance


def start_scheduler():
    """启动核心调度器"""
    scheduler = get_scheduler()
    scheduler.start()
    vlogger.info("VCORE.GLOBAL.START", msg="全局调度器已启动")


def stop_scheduler():
    """停止核心调度器"""
    global _scheduler_instance

    if _scheduler_instance is not None:
        _scheduler_instance.stop()
        vlogger.info("VCORE.GLOBAL.STOP", msg="全局调度器已停止")


def add_market_to_watch(
    market_id: str,
    initial_state: SequenceState = SequenceState.MARKING,
    mark: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    添加市场到监听列表

    参数:
        market_id: 市场ID
        initial_state: 初始状态
        mark: 标记信息
        data: 序列数据
        metadata: 元数据

    返回:
        int: 序列ID
    """
    scheduler = get_scheduler()
    return scheduler.add_sequence(
        market_id=market_id,
        initial_state=initial_state,
        mark=mark,
        data=data,
        metadata=metadata
    )


def get_watching_status(sequence_id: int) -> Optional[Dict[str, Any]]:
    """
    获取监听序列状态

    参数:
        sequence_id: 序列ID

    返回:
        dict: 序列状态信息,如果不存在则返回 None
    """
    scheduler = get_scheduler()
    return scheduler.get_sequence_status(sequence_id)


def list_all_watching() -> List[Dict[str, Any]]:
    """
    列出所有监听序列

    返回:
        list: 所有序列的状态信息列表
    """
    scheduler = get_scheduler()
    return scheduler.list_all_sequences()


# ==================== 模块导出 ====================

__all__ = [
    # 枚举和数据结构
    'SequenceState',
    'WatchingSequence',

    # 核心类
    'VCoreScheduler',

    # 全局函数
    'get_scheduler',
    'start_scheduler',
    'stop_scheduler',
    'add_market_to_watch',
    'get_watching_status',
    'list_all_watching',
]

