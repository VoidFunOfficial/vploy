#!/bin/bash

# VoidPoly 一键启动脚本
# 用途：启动所有 VoidPoly 系统服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用 sudo 运行此脚本"
    exit 1
fi

print_info "启动 VoidPoly 系统服务..."

# 启动服务（按依赖顺序）
systemctl start voidpoly-api.service
print_info "✓ API 服务器已启动"

sleep 2

systemctl start voidpoly-worker.service
print_info "✓ Huey Worker 已启动"

systemctl start voidpoly-frontend.service
print_info "✓ 前端服务器已启动"

echo ""
print_info "所有服务已启动！"
echo ""
echo "访问地址："
echo "  前端界面: http://localhost:3000"
echo "  后端 API: http://localhost:5000"
echo ""
echo "查看服务状态: sudo systemctl status voidpoly-api voidpoly-worker voidpoly-frontend"
echo "查看实时日志: sudo journalctl -u voidpoly-api -u voidpoly-worker -u voidpoly-frontend -f"

