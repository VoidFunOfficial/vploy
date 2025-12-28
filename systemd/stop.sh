#!/bin/bash

# VoidPoly 一键停止脚本
# 用途：停止所有 VoidPoly 系统服务

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

print_info "停止 VoidPoly 系统服务..."

# 停止服务（逆序停止）
systemctl stop voidpoly-frontend.service
print_info "✓ 前端服务器已停止"

systemctl stop voidpoly-worker.service
print_info "✓ Huey Worker 已停止"

systemctl stop voidpoly-api.service
print_info "✓ API 服务器已停止"

echo ""
print_info "所有服务已停止！"

