#!/bin/bash

# VoidPoly 一键重启脚本
# 用途：重启所有 VoidPoly 系统服务

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

print_info "重启 VoidPoly 系统服务..."

# 重启服务
systemctl restart voidpoly-api.service
print_info "✓ API 服务器已重启"

sleep 2

systemctl restart voidpoly-worker.service
print_info "✓ Huey Worker 已重启"

systemctl restart voidpoly-frontend.service
print_info "✓ 前端服务器已重启"

echo ""
print_info "所有服务已重启！"
echo ""
echo "查看服务状态: sudo systemctl status voidpoly-api voidpoly-worker voidpoly-frontend"

