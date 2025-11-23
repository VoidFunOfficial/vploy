"""
API 服务器启动脚本

使用方式：
    python run_api_server.py
"""

if __name__ == '__main__':
    from backend.core.api_server import app, auth_config, vlogger
    
    # 清理过期会话
    auth_config.cleanup_expired_sessions()
    
    vlogger.info("API.SERVER.START", msg="API 服务器启动", extra={
        "host": "0.0.0.0",
        "port": 5000
    })
    
    # 启动 Flask 服务器
    app.run(host='0.0.0.0', port=5000, debug=True)

