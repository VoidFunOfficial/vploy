import websocket
import json

# 这里的 task_id 是动态的，必须从第一条收到的消息中提取，或者维护一个全局变量
current_task_id = None
current_token = None  # 存储最新的 token
current_auth_token = None  # 存储 auth_token (登录时返回)
current_access_token = None  # 存储 access_token (后续操作返回)

def parse_table_and_find_green_accounts(contents):
    """解析 contents 中的 table，找出三个状态都是🟢的账号"""
    green_accounts = []

    for item in contents:
        if item.get('type') == 'table':
            data = item.get('data', [])
            # 跳过表头
            for row in data[1:]:
                if len(row) >= 4:
                    # row[0] 是按钮对象，row[1-3] 是状态
                    # 检查三个状态都是🟢
                    if row[2] == "🟢":
                        # 提取按钮信息
                        button_obj = row[0]
                        if isinstance(button_obj, dict) and button_obj.get('type') == 'buttons':
                            callback_id = button_obj.get('callback_id')
                            buttons = button_obj.get('buttons', [])
                            if buttons:
                                label = buttons[0].get('label')
                                value = buttons[0].get('value', 0)
                                green_accounts.append({
                                    'label': label,
                                    'callback_id': callback_id,
                                    'value': value
                                })
    print(f"[*] 找到 {len(green_accounts)} 个全绿账号")
    return green_accounts

def on_message(ws, message):
    global current_task_id, current_token, current_auth_token, current_access_token
    msg = json.loads(message)
    command = msg.get('command')

    # 1. 捕获 Task ID (通常在第一条消息里就有)
    if 'task_id' in msg:
        current_task_id = msg['task_id']

    # 2. 处理环境检测 (应对 第1-4条消息)
    if command == 'run_script':
        spec = msg.get('spec', {})
        code = spec.get('code', '')
        args = spec.get('args', {})
        response_data = None

        # 检测是否是页面跳转命令，返回成功响应
        if 'window.location.href' in code:
            reply = {
                "event": "js_yield",
                "task_id": current_task_id,
                "data": None
            }
            ws.send(json.dumps(reply))
            print(f"[*] 收到页面跳转命令，已忽略: {code.strip()}")
            return

        # 检测是否是 token 认证请求
        if 'token' in args and '/app/api/auth' in args.get('endpoint', ''):
            token = args['token']
            current_token = token

            # 判断是 auth_token 还是 access_token
            # auth_token 的 task_id 通常包含 "callback_coro"
            # access_token 的 task_id 通常包含 "_start_main_task"
            task_id = msg.get('task_id', '')
            current_auth_token = token
            print(f"[+] 提取到 auth_token: {token}")
     
            # 返回认证成功
            reply = {
                "event": "js_yield",
                "task_id": current_task_id,
                "data": True
            }
            ws.send(json.dumps(reply))
            print(f"[->] 已返回认证成功")

            # 获取到 token 后立即关闭连接
            if current_auth_token or current_access_token:
                print(f"[+] Token 已获取，立即关闭连接")
                ws.close()
            return
        if 'token' in args and '/app/api/access' in args.get('endpoint', ''):
            token = args['token']
            current_token = token

            # 判断是 auth_token 还是 access_token
            # auth_token 的 task_id 通常包含 "callback_coro"
            # access_token 的 task_id 通常包含 "_start_main_task"
            task_id = msg.get('task_id', '')
            current_access_token = token
            print(f"[+] 提取到 access_token: {token}")
            # 返回认证成功
            reply = {
                "event": "js_yield",
                "task_id": current_task_id,
                "data": True
            }
            ws.send(json.dumps(reply))
            print(f"[->] 已返回认证成功")

            # 获取到 token 后立即关闭连接
            if current_auth_token or current_access_token:
                print(f"[+] Token 已获取，立即关闭连接")
                ws.close()
            return
        elif 'timeZone' in code:
            response_data = "Asia/Shanghai"
        elif 'location.origin' in code:
            response_data = "https://cc01.plusai.io"

        if response_data:
            # 伪造浏览器回复
            reply = {
                "event": "js_yield",
                "task_id": current_task_id,
                "data": response_data
            }
            ws.send(json.dumps(reply))
            print(f"[-] 已欺骗服务端环境检测: {code}")
        elif not ('token' in args and '/app/api/auth' in args.get('endpoint', '')):
            # 打印其他 run_script 命令
            print(f"[*] 收到 run_script 命令: {json.dumps(msg, ensure_ascii=False, indent=2)}")

    # 3. 处理表单渲染，发送登录包 (应对 第7、10条消息)
    elif command == 'input_group':
        print("[+] 服务端请求登录，正在发送账号密码...")

        login_payload = {
            "event": "from_submit",
            "task_id": current_task_id,  # 必须使用服务端刚才发的 ID
            "data": {
                "username": "vfff2",
                "password": "qw12qw12",
                "action": "submit"
            }
        }
        ws.send(json.dumps(login_payload))

    # 4. 判断结果 (应对 第12条消息)
    elif command == 'toast':
        print(f"[*] 登录结果: {msg['spec']['content']}")

    # 5. 处理 custom_widget 输出，解析表格并模拟点击
    elif command == 'output':
        spec = msg.get('spec', {})
        if spec.get('type') == 'custom_widget':
            data = spec.get('data', {})
            title = data.get('title', '')
            contents = data.get('contents', [])

            print(f"[+] 收到 custom_widget: {title}")

            # 解析表格，找出三个都是🟢的账号
            green_accounts = parse_table_and_find_green_accounts(contents)

            if green_accounts:
                print(f"[+] 找到 {len(green_accounts)} 个全绿账号:")
                for acc in green_accounts:
                    print(f"    - {acc['label']} (callback_id: {acc['callback_id']})")

                    # 模拟点击按钮
                    click_payload = {
                        "event": "callback",
                        "task_id": current_task_id,
                        "data": acc['value']
                    }
                    ws.send(json.dumps(click_payload))
                    print(f"    [->] 已模拟点击 {acc['label']}")
            else:
                print(f"[-] 未找到全绿账号")

def refresh_auth_token():
    """
    连接到服务器，完成登录流程，获取并返回 auth_token (登录时返回的 token)

    Args:
        username: 用户名
        password: 密码

    Returns:
        str: 提取到的 auth_token，如果失败返回 None
    """
    username = "vfff2"
    password = "qw12qw12"
    global current_auth_token
    current_auth_token = None

    # 临时修改登录凭据
    original_on_message = on_message

    def temp_on_message(ws, message):
        msg = json.loads(message)
        command = msg.get('command')

        # 修改登录凭据
        if command == 'input_group':
            global current_task_id
            if 'task_id' in msg:
                current_task_id = msg['task_id']

            login_payload = {
                "event": "from_submit",
                "task_id": current_task_id,
                "data": {
                    "username": username,
                    "password": password,
                    "action": "submit"
                }
            }
            ws.send(json.dumps(login_payload))
            print(f"[+] 正在使用账号 {username} 登录...")
        else:
            # 其他消息使用原始处理函数
            original_on_message(ws, message)

        # 如果已经获取到 auth_token，关闭连接
        if current_auth_token:
            print(f"[+] Auth Token 获取成功，准备关闭连接")
            ws.close()

    ws_url = "wss://cc01.plusai.io/app/auth/?app=index&session=NEW"
    ws = websocket.WebSocketApp(ws_url, on_message=temp_on_message)
    ws.run_forever()

    return current_auth_token

def refresh_access_token():
    """
    连接到服务器，完成登录流程，获取并返回 access_token (后续操作的 token)

    流程:
    1. 先调用 refresh_auth_token() 获取 auth_token
    2. 使用 auth_token 构建 cookie 发起 WebSocket 连接
    3. 执行模拟点击逻辑获取 access_token

    Returns:
        str: 提取到的 access_token，如果失败返回 None
    """
    username = "vfff2"
    password = "qw12qw12"
    global current_access_token
    current_access_token = None

    # 第一步：获取 auth_token
    print("[*] 第一步：获取 auth_token...")
    auth_token = refresh_auth_token()
    if not auth_token:
        print("[-] 获取 auth_token 失败，无法继续")
        return None

    print(f"[+] 成功获取 auth_token: {auth_token}")

    # 第二步：构建带 cookie 的 WebSocket 连接
    print("[*] 第二步：使用 auth_token 构建 cookie 请求...")

    # 构建 cookie 字符串
    cookie_str = f"oai-did=0497d6c3-d651-4743-9f6a-a24399f32ca0; oai-nav-state=1; oai-locale=en-US; __Secure-auth_token={auth_token}"
    print(f"[+] Cookie: {cookie_str}")

    # 临时修改消息处理逻辑
    clicked = [False]  # 使用列表来在闭包中修改值

    def temp_on_message(ws, message):
        global current_task_id, current_access_token
        msg = json.loads(message)
        command = msg.get('command')

        # 捕获 task_id
        if 'task_id' in msg:
            current_task_id = msg['task_id']

        # 处理环境检测
        if command == 'run_script':
            spec = msg.get('spec', {})
            code = spec.get('code', '')
            args = spec.get('args', {})
            response_data = None

            # 检测是否是页面跳转命令
            if 'window.location.href' in code:
                reply = {
                    "event": "js_yield",
                    "task_id": current_task_id,
                    "data": None
                }
                ws.send(json.dumps(reply))
                print(f"[*] 收到页面跳转命令，已忽略")
                return

            # 检测是否是 access_token 请求
            if 'token' in args and '/app/api/access' in args.get('endpoint', ''):
                token = args['token']
                current_access_token = token
                print(f"[+] 提取到 access_token: {token}")

                # 返回认证成功
                reply = {
                    "event": "js_yield",
                    "task_id": current_task_id,
                    "data": True
                }
                ws.send(json.dumps(reply))
                print(f"[->] 已返回认证成功")

                # 获取到 access_token 后关闭连接
                print(f"[+] Access Token 获取成功，准备关闭连接")
                ws.close()
                return

            # 处理其他环境检测
            elif 'timeZone' in code:
                response_data = "Asia/Shanghai"
            elif 'location.origin' in code:
                response_data = "https://cc01.plusai.io"

            if response_data:
                reply = {
                    "event": "js_yield",
                    "task_id": current_task_id,
                    "data": response_data
                }
                ws.send(json.dumps(reply))
                print(f"[-] 已欺骗服务端环境检测: {code}")

        # 处理 custom_widget 输出，解析表格并模拟点击第一个全绿账号
        elif command == 'output':
            spec = msg.get('spec', {})
            if spec.get('type') == 'custom_widget' and not clicked[0] and 'Team-B' in spec.get('data', {}).get('title'):
                data = spec.get('data', {})
                title = data.get('title', '')
                contents = data.get('contents', [])

                print(f"[+] 收到 custom_widget: {title}")

                # 解析表格，找出三个都是🟢的账号
                green_accounts = parse_table_and_find_green_accounts(contents)

                if green_accounts:
                    # 只点击第一个符合条件的账号
                    acc = green_accounts[0]
                    print(f"[+] 找到全绿账号: {acc['label']} (callback_id: {acc['callback_id']})")

                    # 模拟点击按钮，使用 callback_id 作为 task_id
                    click_payload = {
                        "event": "callback",
                        "task_id": acc['callback_id'],
                        "data": acc['value']
                    }
                    ws.send(json.dumps(click_payload))
                    print(f"[->] 已模拟点击 {acc['label']}，等待服务器返回 access_token...")
                    clicked[0] = True
                else:
                    print(f"[-] 未找到全绿账号")
                    ws.close()

    # 第三步：使用带 cookie 的 WebSocket 连接
    ws_url = "wss://cc01.plusai.io/app/user/?app=index&session=NEW"
    print(f"[*] 第三步：连接到 {ws_url} 并执行模拟点击...")

    # 创建带 cookie 的 WebSocket 连接
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=temp_on_message,
        cookie=cookie_str
    )
    ws.run_forever()

    return current_access_token

if __name__ == "__main__":
    # 示例：获取 auth_token (登录时返回)
    auth_token = refresh_auth_token()
    access_token = refresh_access_token()
    print(f"\n[✓] 最终获取的 Auth Token: {auth_token}")
    print(f"\n[✓] 最终获取的 Access Token: {access_token}")
    # 如果需要获取 access_token，可以调用:
    # access_token = refresh_access_token("vfff2", "qw12qw12")
    # if access_token:
    #     print(f"\n[✓] 最终获取的 Access Token: {access_token}")
    # else:
    #     print(f"\n[✗] Access Token 获取失败")