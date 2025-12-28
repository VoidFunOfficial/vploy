#!/bin/bash

# 设置 systemd 管理脚本的执行权限
# 用途：为所有 shell 脚本添加可执行权限

# 颜色定义
GREEN='\033[0;32m'
NC='\033[0m'

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="/home/ubuntu/vploy/systemd"

print_info "设置脚本执行权限..."

# 为所有 .sh 脚本添加执行权限
chmod +x "$SCRIPT_DIR"/*.sh

print_info "完成！以下脚本已设置执行权限："
ls -lh "$SCRIPT_DIR"/*.sh | awk '{print "  " $9 " (" $1 ")"}'

echo ""
print_info "现在可以直接运行脚本，例如："
echo "  sudo ./systemd/install.sh"
echo "  sudo ./systemd/start.sh"
echo "  sudo ./systemd/status.sh"

