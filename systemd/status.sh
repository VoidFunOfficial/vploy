#!/bin/bash

# VoidPoly 服务状态查看脚本
# 用途：查看所有 VoidPoly 系统服务的运行状态

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 打印函数
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# 检查服务状态
check_service() {
    local service=$1
    local name=$2
    
    echo ""
    print_header "$name"
    
    if systemctl is-active --quiet "$service"; then
        echo -e "状态: ${GREEN}运行中${NC}"
    else
        echo -e "状态: ${RED}已停止${NC}"
    fi
    
    if systemctl is-enabled --quiet "$service" 2>/dev/null; then
        echo -e "开机自启: ${GREEN}已启用${NC}"
    else
        echo -e "开机自启: ${YELLOW}未启用${NC}"
    fi
    
    echo ""
    systemctl status "$service" --no-pager -l || true
}

# 主标题
print_header "VoidPoly 系统服务状态"
echo ""

# 检查各个服务
check_service "voidpoly-api.service" "API 服务器"
check_service "voidpoly-worker.service" "Huey Task Worker"
check_service "voidpoly-frontend.service" "前端开发服务器"

# 提示信息
echo ""
print_header "常用命令"
echo "  查看实时日志: sudo journalctl -u voidpoly-api -f"
echo "  启动所有服务: sudo ./systemd/start.sh"
echo "  停止所有服务: sudo ./systemd/stop.sh"
echo "  重启服务: sudo systemctl restart voidpoly-api"

