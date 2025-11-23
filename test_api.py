"""
测试 API 服务器

使用方式：
    python test_api.py
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """测试健康检查接口"""
    print("\n=== 测试健康检查接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_login():
    """测试登录接口"""
    print("\n=== 测试登录接口 ===")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['data']['token']
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_verify(token):
    """测试令牌验证接口"""
    print("\n=== 测试令牌验证接口 ===")
    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/verify",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_logout(token):
    """测试登出接口"""
    print("\n=== 测试登出接口 ===")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/logout",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("API 服务器测试")
    print("=" * 50)
    
    # 测试健康检查
    if not test_health():
        print("\n❌ 健康检查失败，请确保 API 服务器正在运行")
        print("启动命令: python run_api_server.py")
        exit(1)
    
    print("\n✅ 健康检查通过")
    
    # 测试登录
    token = test_login()
    if not token:
        print("\n❌ 登录测试失败")
        exit(1)
    
    print("\n✅ 登录测试通过")
    print(f"获取到令牌: {token[:20]}...")
    
    # 测试令牌验证
    if not test_verify(token):
        print("\n❌ 令牌验证失败")
        exit(1)
    
    print("\n✅ 令牌验证通过")
    
    # 测试登出
    if not test_logout(token):
        print("\n❌ 登出测试失败")
        exit(1)
    
    print("\n✅ 登出测试通过")
    
    print("\n" + "=" * 50)
    print("所有测试通过！✅")
    print("=" * 50)

