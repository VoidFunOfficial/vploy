from ..polymarket_api import Event, Market, GammaMarketsAPI
from cozepy import COZE_CN_BASE_URL
# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger
coze_api_token = 'pat_7WIJOd6lO8cDox7ciTFaL4CX2dJdBrb0P5qMZLRdng2IvjgKSpJtobzmlIEtJ8D'
coze_api_base = COZE_CN_BASE_URL

from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType, ChatEventType  # noqa

# Init the Coze client through the access_token.
coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)

filter_bot_id = '7572964851103350847'
user_id = 'vpolymarket-filter'

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
    """
    result = []
    
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

def ai_filter_event(event: Event) -> bool:
    """
    使用Coze AI进行事件过滤
    
    参数:
        event (Event): 事件信息
    
    返回:
        bool: 是否通过过滤
    """
    prompt = event.title
    try:
        response = chat_with_coze(bot_id=filter_bot_id, prompt=prompt)
        return "Yes" in response
    except Exception as e:
        vlogger.error("EVT-8063", msg="Coze AI调用失败", error_code="E-FILTER-005", extra={"error": str(e)})
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
