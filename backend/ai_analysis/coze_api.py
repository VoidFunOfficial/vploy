from ..polymarket_api import Event, Market, GammaMarketsAPI
from cozepy import COZE_CN_BASE_URL
# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger
from ..sys_configs.token_refresher import get_token_refresher, TokenType

coze_api_base = COZE_CN_BASE_URL

# 获取 TokenRefresher 实例
token_refresher = get_token_refresher()

from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType, ChatEventType  # noqa

def _get_coze_token() -> str:
    """
    从 TokenRefresher 获取最新的 Coze API Token

    返回:
        str: Coze API Token

    异常:
        ValueError: 如果 token 不存在或已过期
    """
    token_status = token_refresher.get_token_status(TokenType.COZE_TOKEN.value)

    if not token_status:
        vlogger.error("EVT-8065", msg="Coze Token 未配置", error_code="E-COZE-002")
        raise ValueError("Coze Token 未配置，请先在系统中配置 Token")

    if token_status.get('is_expired'):
        vlogger.error("EVT-8066", msg="Coze Token 已过期", error_code="E-COZE-003")
        raise ValueError("Coze Token 已过期，请更新 Token")

    token_value = token_status.get('token_value')
    if not token_value:
        vlogger.error("EVT-8067", msg="Coze Token 值为空", error_code="E-COZE-004")
        raise ValueError("Coze Token 值为空")

    return token_value

def _get_coze_client() -> Coze:
    """
    获取 Coze 客户端实例，使用最新的 token

    返回:
        Coze: Coze 客户端实例
    """
    token = _get_coze_token()
    return Coze(auth=TokenAuth(token=token), base_url=coze_api_base)

filter_bot_id = '7572964851103350847'
user_id = 'vpolymarket-filter'

def handle_coze_error(error: Exception) -> None:
    """
    处理Coze API错误,立即标记coze_token为过期

    参数:
        error: 异常对象
    """
    # 立即标记 coze_token 为过期
    token_refresher.set_expired_immediate(TokenType.COZE_TOKEN.value)
    vlogger.error("EVT-8064", msg="Coze API错误,已标记token为过期", error_code="E-COZE-001", extra={"error": str(error)})

# Call the coze.chat.stream method to create a chat. The create method is a streaming
# chat and will return a Chat Iterator. Developers should iterate the iterator to get
# chat event and handle them.
def chat_with_coze(bot_id: str, prompt: str, user_id: str = 'vpolymarket-filter') -> str:
    """
    与Coze AI进行对话

    参数:
        bot_id (str): Bot ID
        prompt (str): 用户输入的提示词
        user_id (str): 用户ID，默认为'vpolymarket-filter'

    返回:
        str: AI返回的完整响应内容

    异常:
        如果发生错误,会调用handle_coze_error标记token为过期并重新抛出异常
    """
    result = []

    try:
        # 每次调用时获取最新的 Coze 客户端（使用最新 token）
        coze = _get_coze_client()

        for event in coze.chat.stream(
            bot_id=bot_id,
            user_id=user_id,
            additional_messages=[
                Message.build_user_question_text(prompt),
            ],
        ):
            if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                result.append(event.message.content)
                print(event.message.content, end="", flush=True)

            if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                print()
                print("token usage:", event.chat.usage.token_count)

        return ''.join(result)

    except Exception as e:
        # 处理错误并标记token为过期
        handle_coze_error(e)
        raise

def ai_filter_event(event: Event) -> bool:
    """
    使用Coze AI进行事件过滤

    参数:
        event (Event): 事件信息

    返回:
        bool: 是否通过过滤
    """
    prompt = event.title
    event_id = getattr(event, 'id', 'unknown')

    vlogger.debug("EVT-8062", msg="开始 AI 过滤事件", extra={
        "event_id": event_id,
        "title": prompt[:100]
    })

    try:
        response = chat_with_coze(bot_id=filter_bot_id, prompt=prompt)
        print(response)
        is_passed = "Yes" in response

        vlogger.info("EVT-8061", msg="AI 过滤完成", extra={
            "event_id": event_id,
            "title": prompt[:100],
            "response": response[:200],
            "is_passed": is_passed
        })

        return is_passed

    except Exception as e:
        vlogger.error("EVT-8063", msg="Coze AI调用失败，默认通过", error_code="E-FILTER-005", extra={
            "event_id": event_id,
            "title": prompt[:100],
            "error": str(e)
        })
        return True

# 示例调用
if __name__ == "__main__":
    # response = chat_with_coze(bot_id=filter_bot_id, prompt="Earth is not blue")
    a = GammaMarketsAPI()
    from filter.event_filter import EventFilter
    filter_instance = EventFilter()
    events = a.get_new_events(limit=30)
    filtered_events = filter_instance.filter_events(events)
    for event in filtered_events:
        print(ai_filter_event(event))
