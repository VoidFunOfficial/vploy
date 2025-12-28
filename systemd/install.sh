#!/bin/bash

# VoidPoly 系统服务安装脚本
# 用途：安装 systemd 服务单元文件并配置自动启动

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

# 获取脚本所在目录
PROJECT_DIR="/home/ubuntu/vploy"

# 获取当前用户（非 root）
REAL_USER="${SUDO_USER:-$USER}"
if [ "$REAL_USER" = "root" ]; then
    print_error "无法确定实际用户，请使用 sudo 运行"
    exit 1
fi

print_info "项目目录: $PROJECT_DIR"
print_info "运行用户: $REAL_USER"

# 检测 Python 路径（优先使用 conda）
PYTHON_PATH=""
CONDA_ENV_NAME=""

# 1. 检查是否有 conda 环境
if command -v conda &> /dev/null; then
    print_info "检测到 conda 环境"

    # 尝试获取当前激活的环境
    CURRENT_ENV=$(echo $CONDA_DEFAULT_ENV)

    if [ -n "$CURRENT_ENV" ] && [ "$CURRENT_ENV" != "base" ]; then
        # 使用当前激活的环境
        CONDA_ENV_NAME="$CURRENT_ENV"
        print_info "使用当前 conda 环境: $CONDA_ENV_NAME"
    else
        # 提示用户输入环境名称
        echo ""
        print_warn "未检测到激活的 conda 环境（或当前为 base 环境）"
        read -p "请输入要使用的 conda 环境名称（直接回车使用 base）: " INPUT_ENV

        if [ -n "$INPUT_ENV" ]; then
            CONDA_ENV_NAME="$INPUT_ENV"
        else
            CONDA_ENV_NAME="base"
        fi
        print_info "将使用 conda 环境: $CONDA_ENV_NAME"
    fi

    # 获取 conda 环境的 Python 路径
    CONDA_PYTHON=$(conda run -n "$CONDA_ENV_NAME" which python 2>/dev/null || echo "")

    if [ -n "$CONDA_PYTHON" ] && [ -f "$CONDA_PYTHON" ]; then
        PYTHON_PATH="$CONDA_PYTHON"
        print_info "conda Python 路径: $PYTHON_PATH"
    else
        print_error "conda 环境 '$CONDA_ENV_NAME' 中未找到 Python"
        exit 1
    fi
fi

# 2. 如果没有找到 conda，使用系统 Python
if [ -z "$PYTHON_PATH" ]; then
    print_warn "未检测到 conda，尝试使用系统 Python"
    PYTHON_PATH=$(which python)
    if [ -z "$PYTHON_PATH" ]; then
        print_error "未找到 Python，请先安装 Python 或 conda"
        exit 1
    fi
    print_info "使用系统 Python: $PYTHON_PATH"
fi

# 验证 Python 版本
PYTHON_VERSION=$($PYTHON_PATH --version 2>&1)
print_info "Python 版本: $PYTHON_VERSION"

# 检测 npm 路径
NPM_PATH="/home/ubuntu/.nvm/versions/node/v24.12.0/bin/npm"
if [ ! -f "$NPM_PATH" ]; then
    print_error "未找到 npm: $NPM_PATH"
    exit 1
fi
print_info "npm 路径: $NPM_PATH"

# 设置 Node.js 路径
NODE_PATH="/home/ubuntu/.nvm/versions/node/v24.12.0/bin/node"
if [ ! -f "$NODE_PATH" ]; then
    print_error "未找到 node: $NODE_PATH"
    exit 1
fi
print_info "node 路径: $NODE_PATH"

# 获取 conda 环境的 PATH（如果使用 conda）
CONDA_PATH_ENV=""
if [ -n "$CONDA_ENV_NAME" ]; then
    # 获取 conda 环境的完整 PATH
    CONDA_PATH_ENV=$(conda run -n "$CONDA_ENV_NAME" printenv PATH)
    # 截取前100个字符用于显示（使用 POSIX 兼容的方式）
    CONDA_PATH_PREVIEW=$(echo "$CONDA_PATH_ENV" | cut -c1-100)
    print_info "conda 环境 PATH: ${CONDA_PATH_PREVIEW}..."
else
    # 使用系统 PATH
    CONDA_PATH_ENV="$PATH"
fi

# 复制并配置服务文件
print_info "配置服务文件..."

for service in voidpoly-api voidpoly-worker voidpoly-frontend; do
    SERVICE_FILE="$PROJECT_DIR/systemd/${service}.service"
    TARGET_FILE="/etc/systemd/system/${service}.service"

    if [ ! -f "$SERVICE_FILE" ]; then
        print_error "服务文件不存在: $SERVICE_FILE"
        exit 1
    fi

    # 替换占位符
    sed -e "s|%USER%|$REAL_USER|g" \
        -e "s|%WORKDIR%|$PROJECT_DIR|g" \
        -e "s|%PYTHON%|$PYTHON_PATH|g" \
        -e "s|%NPM%|$NPM_PATH|g" \
        -e "s|%NODE%|$NODE_PATH|g" \
        -e "s|%CONDA_PATH%|$CONDA_PATH_ENV|g" \
        "$SERVICE_FILE" > "$TARGET_FILE"

    print_info "已安装: $TARGET_FILE"
done

# 重新加载 systemd
print_info "重新加载 systemd..."
systemctl daemon-reload

# 启用服务
print_info "启用服务开机自启..."
systemctl enable voidpoly-api.service
systemctl enable voidpoly-worker.service
systemctl enable voidpoly-frontend.service

print_info "安装完成！"
echo ""
echo "使用以下命令管理服务："
echo "  启动所有服务: sudo systemctl start voidpoly-api voidpoly-worker voidpoly-frontend"
echo "  停止所有服务: sudo systemctl stop voidpoly-api voidpoly-worker voidpoly-frontend"
echo "  查看服务状态: sudo systemctl status voidpoly-api voidpoly-worker voidpoly-frontend"
echo "  查看服务日志: sudo journalctl -u voidpoly-api -f"
echo ""
echo "或使用管理脚本："
echo "  启动: ./systemd/start.sh"
echo "  停止: ./systemd/stop.sh"
echo "  状态: ./systemd/status.sh"

