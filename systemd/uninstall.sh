#!/bin/bash

# VoidPoly 系统服务卸载脚本
# 用途：停止并卸载 systemd 服务单元文件

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

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用 sudo 运行此脚本"
    exit 1
fi

print_info "开始卸载 VoidPoly 系统服务..."

# 停止并禁用服务
for service in voidpoly-api voidpoly-worker voidpoly-frontend; do
    SERVICE_NAME="${service}.service"
    
    # 停止服务
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_info "停止服务: $SERVICE_NAME"
        systemctl stop "$SERVICE_NAME"
    fi
    
    # 禁用服务
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_info "禁用服务: $SERVICE_NAME"
        systemctl disable "$SERVICE_NAME"
    fi
    
    # 删除服务文件
    SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
    if [ -f "$SERVICE_FILE" ]; then
        print_info "删除服务文件: $SERVICE_FILE"
        rm -f "$SERVICE_FILE"
    fi
done

# 重新加载 systemd
print_info "重新加载 systemd..."
systemctl daemon-reload
systemctl reset-failed

print_info "卸载完成！"

