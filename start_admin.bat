@echo off
chcp 65001 >nul
echo ========================================
echo VoidPoly 管理面板启动脚本
echo ========================================
echo.

echo [1/2] 启动后端 API 服务器...
start "VoidPoly Backend API" cmd /k "python run_api_server.py"
timeout /t 3 /nobreak >nul

echo [2/2] 启动前端开发服务器...
start "VoidPoly Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo 启动完成！
echo ========================================
echo 后端 API: http://localhost:5000
echo 前端界面: http://localhost:3000
echo.
echo 默认账号: admin / admin123
echo ========================================
pause

