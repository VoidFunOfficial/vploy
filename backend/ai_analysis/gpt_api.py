import requests
import json
import uuid
import time
from typing import Optional

"""
关键说明:
__Secure-access_token 为 API账号(GPT账号)的 access_token 有效期2D
__Secure-auth_token   为 中转平台账号   的 auth_token 有效期 14D
_account              为 平台账号唯一标识符 不可更改
"""
ACCOUNT_ID = "f9f24477-3b6b-4a27-a298-c8663fd4edc5"

def parse_cookie_string(cookie_string: str) -> dict:
    """
    解析Cookie字符串为字典

    参数:
        cookie_string: Cookie字符串，格式如 "key1=value1; key2=value2"

    返回:
        dict: Cookie字典
    """
    cookies_dict = {}
    # 同时兼容有空格和无空格的写法: "a=1; b=2" 或 "a=1;b=2"
    for item in cookie_string.split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            cookies_dict[key.strip()] = value
    return cookies_dict


def send_request(
    prompt: str,
    cookie_header: str = '',
    auth_token: str = '',
    access_token: str = '',
    chatgpt_account_id: str = '',
    device_id: str = '',
    model: str = "gpt-5-instant",
    parent_message_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    api_base_url: str = "https://cc01.plusai.io",
    cookies: Optional[dict] = None
) -> dict:
    """
    发送请求到 ChatGPT API（单次请求，不使用 stream=True，内部解析 SSE 文本）

    参数:
        prompt: 用户输入的提示词
        cookie_header: 浏览器复制的 Cookie 头部字符串（优先从这里自动解析各字段）
        auth_token: 认证令牌 (__Secure-auth_token)
        access_token: 访问令牌 (__Secure-access_token)
        chatgpt_account_id: ChatGPT账户ID (_account)
        device_id: 设备ID (oai-did)
        model: 使用的模型，默认 "gpt-5-1"
        parent_message_id: 父消息ID，用于对话上下文
        conversation_id: 对话ID，用于继续现有对话
        api_base_url: API基础URL，默认 "https://cc01.plusai.io"
        cookies: 可选的完整Cookie字典，如果提供则覆盖其他参数

    返回:
        dict: API响应结果
    """

    # API端点
    url = f"{api_base_url}/backend-api/conversation"

    # 生成唯一的消息ID和请求ID（后端只要求合法UUID即可）
    message_id = str(uuid.uuid4())
    websocket_request_id = str(uuid.uuid4())

    # 如果没有提供parent_message_id，生成一个新的
    if parent_message_id is None:
        parent_message_id = str(uuid.uuid4())

    # 如果没有提供device_id，生成一个新的
    if not device_id:
        device_id = str(uuid.uuid4())

    # 获取当前时间戳
    current_timestamp = int(time.time())
    create_time = time.time()

    # 构建 referrer 路径（尽量贴合浏览器 fetch 行为）
    referrer_path = "/"
    if conversation_id:
        referrer_path = f"/c/{conversation_id}"

    # 构建Cookie字典
    if cookies is None:
        if cookie_header:
            # 优先从浏览器复制的 Cookie 头部字符串解析
            cookies = parse_cookie_string(cookie_header)
        else:
            # 兼容老的手动传入 token 方式
            cookies = {
                "oai-locale": "en-US",
                "oai-did": device_id,
                "oai-nav-state": "1",
                "__Secure-auth_token": auth_token,
                "oai-thread-sidebar": '"%257B%2522isOpen%2522%253Afalse%257D"',
                "__Secure-access_token": access_token,
                "_account": chatgpt_account_id,
            }

    # 从cookies中提取access_token用于Authorization header
    token_for_auth = access_token
    if cookies and "__Secure-access_token" in cookies:
        token_for_auth = cookies["__Secure-access_token"]

    # 从cookies中提取account_id
    account_for_header = chatgpt_account_id
    if cookies and "_account" in cookies:
        account_for_header = cookies["_account"]

    # 从cookies中提取device_id
    device_for_header = device_id
    if cookies and "oai-did" in cookies:
        device_for_header = cookies["oai-did"]

    # 构建完整的请求头（参考实际fetch请求）
    headers = {
        "accept": "text/event-stream",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "authorization": f"Bearer {token_for_auth}",  # 使用access_token作为Bearer token
        "chatgpt-account-id": account_for_header,
        "chatgpt-residency-region": "undefined",
        "content-type": "application/json",
        "oai-device-id": device_for_header,
        "oai-language": "en-US",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        "x-timestamp": str(current_timestamp),
        "referer": f"{api_base_url}{referrer_path}",
        "origin": api_base_url,
    }

    # 构建请求体（完全参考实际fetch请求）
    payload = {
        "action": "next",
        "messages": [
            {
                "id": message_id,
                "author": {
                    "role": "user"
                },
                "content": {
                    "content_type": "text",
                    "parts": [prompt]
                },
                "metadata": {
                    "serialization_metadata": {
                        "custom_symbol_offsets": []
                    }
                },
                "create_time": create_time
            }
        ],
        "parent_message_id": parent_message_id,
        "model": model,
        "timezone_offset_min": -480,  # UTC+8 (中国时区)
        "timezone": "Asia/Shanghai",
        "suggestions": [],
        "history_and_training_disabled": False,
        "conversation_mode": {
            "kind": "primary_assistant"
        },
        "force_paragen": False,
        "force_paragen_model_slug": "",
        "force_rate_limit": False,
        "reset_rate_limits": False,
        "websocket_request_id": websocket_request_id,
        "system_hints": [],
        "supported_encodings": [],
        "conversation_origin": None,
        "client_contextual_info": {
            "is_dark_mode": True,
            "time_since_loaded": 61,
            "page_height": 748,
            "page_width": 350,
            "pixel_ratio": 1.25,
            "screen_height": 864,
            "screen_width": 1536
        },
        "paragen_stream_type_override": None,
        "paragen_cot_summary_display_override": "allow"
    }

    # 如果提供了conversation_id，添加到payload中
    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        # 发送POST请求（不使用requests的流模式，直接拿到完整SSE文本）
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            json=payload,
            timeout=60,
            stream=False,
        )

        # 检查响应状态
        response.raise_for_status()

        # 按行手动解析 SSE 文本（等价于浏览器 fetch 接收到的 text/event-stream）
        text = response.text or ""
        events: list[dict] = []
        full_text = ""

        for raw_line in text.splitlines():
            line = raw_line.strip("\r\n")
            if not line:
                continue
            if not line.startswith("data: "):
                continue

            data_str = line[len("data: "):]
            if data_str.strip() == "[DONE]":
                break

            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            # 有些 SSE 事件可能是 list，我们只处理 dict 类型的事件
            if not isinstance(event, dict):
                continue

            events.append(event)

            message = event.get("message") or {}
            content = message.get("content") or {}
            parts = content.get("parts") or []
            if parts:
                # 这里只取第一段，和浏览器 UI 展示的主文本保持一致
                full_text += str(parts[0])

        return {
            "success": True,
            "status_code": response.status_code,
            "text": full_text,
            "events": events,
            "raw_response": text,
            "message_id": message_id,
            "websocket_request_id": websocket_request_id,
        }

    except requests.exceptions.RequestException as e:
        # 处理请求异常，同时尽量把服务端返回的错误内容也带出来，便于排查422等问题
        status_code = None
        response_text = ""
        if hasattr(e, "response") and e.response is not None:
            status_code = e.response.status_code
            try:
                response_text = e.response.text
            except Exception:
                response_text = ""

        return {
            "success": False,
            "error": str(e),
            "status_code": status_code,
            "response_text": response_text,
            "message_id": message_id,
            "websocket_request_id": websocket_request_id,
        }


def send_request_stream(
    prompt: str,
    auth_token: str = '',
    access_token: str = '',
    chatgpt_account_id: str = '',
    device_id: str = '',
    model: str = "gpt-5-1",
    parent_message_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    api_base_url: str = "https://cc01.plusai.io",
    cookies: Optional[dict] = None,
    callback=None
):
    """
    发送请求到 ChatGPT API (流式响应，支持回调)

    参数:
        prompt: 用户输入的提示词
        auth_token: 认证令牌 (__Secure-auth_token)
        access_token: 访问令牌 (__Secure-access_token)
        chatgpt_account_id: ChatGPT账户ID (_account)
        device_id: 设备ID (oai-did)
        model: 使用的模型，默认 "gpt-5-1"
        parent_message_id: 父消息ID，用于对话上下文
        conversation_id: 对话ID，用于继续现有对话
        api_base_url: API基础URL，默认 "https://cc01.plusai.io"
        cookies: 可选的完整Cookie字典，如果提供则覆盖其他参数
        callback: 回调函数，接收每个事件数据 callback(event_data)

    返回:
        dict: API响应结果
    """

    # API端点
    url = f"{api_base_url}/backend-api/conversation"

    # 生成唯一的消息ID和请求ID（后端只要求合法UUID即可）
    message_id = str(uuid.uuid4())
    websocket_request_id = str(uuid.uuid4())

    # 如果没有提供parent_message_id，生成一个新的
    if parent_message_id is None:
        parent_message_id = str(uuid.uuid4())

    # 如果没有提供device_id，生成一个新的
    if not device_id:
        device_id = str(uuid.uuid4())

    # 获取当前时间戳
    current_timestamp = int(time.time())
    create_time = time.time()

    # 构建Cookie字典
    if cookies is None:
        cookies = {
            "oai-locale": "en-US",
            "oai-did": device_id,
            "oai-nav-state": "1",
            "__Secure-auth_token": auth_token,
            "oai-thread-sidebar": '"%257B%2522isOpen%2522%253Afalse%257D"',
            "__Secure-access_token": access_token,
            "_account": chatgpt_account_id,
        }

    # 构建完整的请求头
    headers = {
        "accept": "text/event-stream",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "authorization": f"Bearer {access_token}",  # 使用access_token作为Bearer token
        "chatgpt-account-id": chatgpt_account_id,
        "chatgpt-residency-region": "undefined",
        "content-type": "application/json",
        "oai-device-id": device_id,
        "oai-language": "en-US",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-timestamp": str(current_timestamp),
        "referer": f"{api_base_url}/",
        "origin": api_base_url,
    }

    # 构建请求体
    payload = {
        "action": "next",
        "messages": [
            {
                "id": message_id,
                "author": {
                    "role": "user"
                },
                "content": {
                    "content_type": "text",
                    "parts": [prompt]
                },
                "metadata": {
                    "serialization_metadata": {
                        "custom_symbol_offsets": []
                    }
                },
                "create_time": create_time
            }
        ],
        "parent_message_id": parent_message_id,
        "model": model,
        "timezone_offset_min": -480,
        "timezone": "Asia/Shanghai",
        "suggestions": [],
        "history_and_training_disabled": False,
        "conversation_mode": {
            "kind": "primary_assistant"
        },
        "force_paragen": False,
        "force_paragen_model_slug": "",
        "force_rate_limit": False,
        "reset_rate_limits": False,
        "websocket_request_id": websocket_request_id,
        "system_hints": [],
        "supported_encodings": [],
        "conversation_origin": None,
        "client_contextual_info": {
            "is_dark_mode": True,
            "time_since_loaded": 61,
            "page_height": 748,
            "page_width": 350,
            "pixel_ratio": 1.25,
            "screen_height": 864,
            "screen_width": 1536
        },
        "paragen_stream_type_override": None,
        "paragen_cot_summary_display_override": "allow"
    }

    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,  # 添加Cookie
            json=payload,
            timeout=60,
            stream=True
        )

        response.raise_for_status()

        # 处理流式响应并调用回调
        full_response = ""
        events = []

        for line in response.iter_lines(decode_unicode=True):
            if line:
                if line.startswith("data: "):
                    data_str = line[6:]

                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        event_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    # 有些 SSE 事件可能是 list，我们只处理 dict 类型的事件
                    if not isinstance(event_data, dict):
                        continue

                    events.append(event_data)

                    # 调用回调函数
                    if callback:
                        callback(event_data)

                    # 提取消息内容
                    if "message" in event_data:
                        msg = event_data["message"]
                        if "content" in msg and "parts" in msg["content"]:
                            parts = msg["content"]["parts"]
                            if parts:
                                full_response = parts[0]

        return {
            "success": True,
            "status_code": response.status_code,
            "response": full_response,
            "events": events,
            "message_id": message_id,
            "websocket_request_id": websocket_request_id
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message_id": message_id,
            "websocket_request_id": websocket_request_id
        }

def process_result(result):
    if result["success"]:
        # 从 events 字段提取第一个元素的 conversation_id
        conversation_id = result["events"][0]["conversation_id"]
        return conversation_id
    else:
        print(f"错误: {result['error']}")
        print(result)

def get_result(
    conversation_id: str,
    cookies: dict = None,
    cookie_header: str = '',
    api_base_url: str = "https://cc01.plusai.io"
) -> dict:
    """
    获取并解析conversation的AI助手回答

    参数:
        conversation_id: 对话ID
        cookies: Cookie字典
        cookie_header: 浏览器复制的Cookie头部字符串（优先从这里自动解析）
        api_base_url: API基础URL，默认 "https://cc01.plusai.io"

    返回:
        dict: 包含AI助手的回答内容
            {
                "success": bool,
                "conversation_id": str,
                "title": str,
                "ai_response": str,  # AI助手的最后一条回答
                "all_ai_responses": [str],  # 所有AI助手的回答列表
                "create_time": float,
                "update_time": float
            }
    """
    url = f"{api_base_url}/backend-api/conversation/{conversation_id}"

    # 构建Cookie字典
    if cookies is None:
        if cookie_header:
            cookies = parse_cookie_string(cookie_header)
        else:
            return {
                "success": False,
                "error": "必须提供 cookies 或 cookie_header 参数"
            }

    # 从cookies中提取必要的token
    access_token = cookies.get("__Secure-access_token", "")
    account_id = cookies.get("_account", "")
    device_id = cookies.get("oai-did", str(uuid.uuid4()))

    # 构建请求头
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "oai-device-id": device_id,
        "oai-language": "en-US",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        "referer": f"{api_base_url}/c/{conversation_id}",
        "origin": api_base_url,
    }

    try:
        # 发送GET请求
        response = requests.get(
            url,
            headers=headers,
            cookies=cookies,
            timeout=30
        )

        # 检查响应状态
        response.raise_for_status()

        # 解析JSON响应
        data = response.json()

        # 提取基本信息
        title = data.get("title")
        create_time = data.get("create_time")
        update_time = data.get("update_time")
        current_node = data.get("current_node")

        # 解析mapping中的消息
        mapping = data.get("mapping", {})
        ai_responses = []  # 只保存AI助手的回答

        # 构建消息链：从current_node开始向上追溯
        if current_node and current_node in mapping:
            # 从当前节点向上追溯到根节点
            node_chain = []
            current = current_node

            while current and current in mapping:
                node = mapping[current]
                node_chain.append(node)
                current = node.get("parent")

            # 反转链表，使其从根到叶
            node_chain.reverse()

            # 提取AI助手的回答（只保留assistant角色的消息）
            for node in node_chain:
                message_data = node.get("message")
                if not message_data:
                    continue

                # 提取消息内容
                author = message_data.get("author", {})
                role = author.get("role")

                # 只保留助手的消息
                if role != "assistant":
                    continue

                content_obj = message_data.get("content", {})

                # 检查是否是思考内容（thinking/reasoning）
                content_type = content_obj.get("content_type", "")
                if content_type in ["thinking", "reasoning"]:
                    # 跳过思考内容，不保存
                    continue

                # 处理不同的content格式
                content_text = ""
                if isinstance(content_obj, dict):
                    # 标准格式：{"content_type": "text", "parts": ["..."]}
                    if "parts" in content_obj:
                        parts = content_obj.get("parts", [])
                        if parts and len(parts) > 0:
                            content_text = str(parts[0])
                    # 推理格式：{"content_type": "text", "content": "..."}
                    elif "content" in content_obj:
                        content_text = str(content_obj.get("content", ""))

                # 跳过空消息
                if not content_text or content_text.strip() == "":
                    continue

                # 只保存AI助手的最终回答内容（不包含思考过程）
                ai_responses.append(content_text)

        # 获取最后一条AI回答
        ai_response = ai_responses[-1] if ai_responses else ""
        if len(ai_responses) == 0 and ai_response == "":
            return {
                "success": False,
                "error": "AI is thinking"
            }
        return {
            "success": True,
            "conversation_id": data.get("conversation_id"),
            "title": title,
            "ai_response": ai_response,  # 最后一条AI回答
            "all_ai_responses": ai_responses,  # 所有AI回答列表
            "create_time": create_time,
            "update_time": update_time
        }

    except requests.exceptions.RequestException as e:
        # 处理请求异常
        status_code = None
        response_text = ""
        if hasattr(e, "response") and e.response is not None:
            status_code = e.response.status_code
            try:
                response_text = e.response.text
            except Exception:
                response_text = ""

        return {
            "success": False,
            "error": str(e),
            "status_code": status_code,
            "response_text": response_text
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON解析错误: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"未知错误: {str(e)}"
        }


# 使用示例
    
if __name__ == "__main__":

    # 从浏览器复制的完整Cookie字符串
    cookie_string =   "__Secure-auth_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjQ0ODg1OTIsInN1YiI6ImFhOGQ3ZmFjNThiNjQ3ZDdhMGIxOGUyOTNlOTZkNGQ1IiwiaWF0IjoxNzYzMjc4OTkyLCJ0b2tlbl90eXBlIjoiYXV0aF90b2tlbiJ9.OybGxLfP3tz6pcclLp2CKcpiEIKxGm3GuliEKu5hp6c;oai-nav-state=1;oai-did=4bc875ef-9530-4184-88c5-0e425f655700;__Secure-access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjM3ODcyNTgsInN1YiI6ImFhOGQ3ZmFjNThiNjQ3ZDdhMGIxOGUyOTNlOTZkNGQ1IiwiaWF0IjoxNzYzNjUyMjU4LCJ0b2tlbl90eXBlIjoiYWNjZXNzX3Rva2VuIiwic3Vic2NyaXB0aW9uX2lkIjoiNjY0MGM3NWMxNDQ4MGI4YWZmZGUxY2VhIiwiYWNjb3VudF9pZCI6IjY4ZTBjMDNmMTNjMTE1ZDM5NWQwNzM2NyJ9.PHhr1dw9Yoizp9iM4bEXUY9BgVw60xoKmEVLdYqWBVA;_account=f9f24477-3b6b-4a27-a298-c8663fd4edc5;oai-locale=en-US" 
    cookies_dict = parse_cookie_string(cookie_string)
    result2 = get_result(
            conversation_id="69199985-e7f8-832f-9db9-03300ba6c101",
            cookies=cookies_dict
        )
    print(json.dumps(result2, indent=4))
    # # 使用辅助函数解析Cookie字符串
    # cookies_dict = parse_cookie_string(cookie_string)

    # # 示例1: 发送请求并获取AI回答
    # print("=== 示例1: 发送请求并获取AI回答 ===")
    # result1 = send_request(
    #     prompt="用一句话介绍Python",
    #     cookies=cookies_dict,
    #     model="gpt-5"
    # )

    # if result1["success"]:
    #     conversation_id = process_result(result1)
    #     print(f"对话ID: {conversation_id}")
    #     print(f"即时回复: {result1['text'][:100]}...")  # 只显示前100个字符

    #     # 示例2: 获取AI助手的完整回答
    #     print("\n" + "="*50)
    #     print("=== 示例2: 获取AI助手的完整回答 ===")

    #     result2 = get_result(
    #         conversation_id=conversation_id,
    #         cookies=cookies_dict
    #     )

    #     if result2["success"]:
    #         print(f"对话标题: {result2['title']}")
    #         print(f"AI回答数量: {len(result2['all_ai_responses'])}")
    #         print(f"\n最后一条AI回答:")
    #         print(result2['ai_response'])

    #         # 如果有多条AI回答，显示所有回答
    #         if len(result2['all_ai_responses']) > 1:
    #             print(f"\n所有AI回答:")
    #             for i, response in enumerate(result2['all_ai_responses'], 1):
    #                 preview = response[:100] + "..." if len(response) > 100 else response
    #                 print(f"\n[{i}] {preview}")
    #     else:
    #         print(f"获取AI回答失败: {result2['error']}")
    # else:
    #     print(f"发送请求失败: {result1['error']}")
    #     if 'response_text' in result1:
    #         print(f"响应内容: {result1['response_text']}")

    # print("\n" + "="*50 + "\n")