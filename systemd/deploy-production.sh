#!/bin/bash

# VoidPoly 生产环境一键部署脚本
# 包含：后端 API (Gunicorn) + 前端 (Nginx)

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}VoidPoly 生产环境一键部署${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 root 权限运行此脚本${NC}"
    echo "使用: sudo $0"
    exit 1
fi

CURRENT_USER=${SUDO_USER:-$USER}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}工作目录: $WORKDIR${NC}"
echo -e "${BLUE}当前用户: $CURRENT_USER${NC}"
echo ""



# 检查 gunicorn
if ! python -c "import gunicorn" 2>/dev/null; then
    echo -e "${YELLOW}安装 Gunicorn...${NC}"
    pip install gunicorn
fi

echo -e "${GREEN}✓ 系统依赖检查完成${NC}"

# 步骤 2: 构建前端
echo ""
echo -e "${YELLOW}[2/5] 构建前端...${NC}"
cd "$WORKDIR/vploy/frontend"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}安装前端依赖...${NC}"
    npm install
fi
npm run build
echo -e "${GREEN}✓ 前端构建完成${NC}"

# 步骤 3: 配置 Nginx
echo ""
echo -e "${YELLOW}[3/5] 配置 Nginx...${NC}"
sed "s|%WORKDIR%|$WORKDIR|g" "$SCRIPT_DIR/systemd/nginx/voidpoly.conf" > /tmp/voidpoly.conf
cp /tmp/voidpoly.conf /etc/nginx/sites-available/voidpoly.conf

if [ -f /etc/nginx/sites-enabled/voidpoly.conf ]; then
    rm /etc/nginx/sites-enabled/voidpoly.conf
fi
ln -s /etc/nginx/sites-available/voidpoly.conf /etc/nginx/sites-enabled/voidpoly.conf

# 删除默认配置
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi

nginx -t
echo -e "${GREEN}✓ Nginx 配置完成${NC}"

# 步骤 4: 配置后端服务
echo ""
echo -e "${YELLOW}[4/5] 配置后端服务...${NC}"

# 查找 Python 路径
PYTHON_PATH=$(which python)
echo -e "${BLUE}Python 路径: $PYTHON_PATH${NC}"

# 替换 systemd 服务文件中的占位符
sed -e "s|%USER%|$CURRENT_USER|g" \
    -e "s|%WORKDIR%|$WORKDIR|g" \
    -e "s|%PYTHON%|$PYTHON_PATH|g" \
    "$SCRIPT_DIR/systemd/voidpoly-api-production.service" > /tmp/voidpoly-api-production.service

# 复制服务文件
cp /tmp/voidpoly-api-production.service /etc/systemd/system/voidpoly-api-production.service

# 创建日志目录
mkdir -p /var/log/voidpoly
chown -R $CURRENT_USER:$CURRENT_USER /var/log/voidpoly

# 重载 systemd
systemctl daemon-reload
echo -e "${GREEN}✓ 后端服务配置完成${NC}"

# 步骤 5: 启动服务
echo ""
echo -e "${YELLOW}[5/5] 启动服务...${NC}"

# 启动后端
systemctl enable voidpoly-api-production
systemctl restart voidpoly-api-production
sleep 2

if systemctl is-active --quiet voidpoly-api-production; then
    echo -e "${GREEN}✓ 后端 API 服务启动成功${NC}"
else
    echo -e "${RED}✗ 后端 API 服务启动失败${NC}"
    systemctl status voidpoly-api-production
    exit 1
fi

# 启动 Nginx
systemctl enable nginx
systemctl restart nginx

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx 服务启动成功${NC}"
else
    echo -e "${RED}✗ Nginx 启动失败${NC}"
    systemctl status nginx
    exit 1
fi

# 完成
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "访问地址: ${GREEN}http://$(hostname -I | awk '{print $1}')${NC}"
echo ""
echo -e "${YELLOW}服务状态:${NC}"
echo -e "  后端 API: $(systemctl is-active voidpoly-api-production)"
echo -e "  Nginx:    $(systemctl is-active nginx)"
echo ""
echo -e "${YELLOW}常用命令:${NC}"
echo -e "  查看后端状态: ${BLUE}sudo systemctl status voidpoly-api-production${NC}"
echo -e "  查看后端日志: ${BLUE}sudo journalctl -u voidpoly-api-production -f${NC}"
echo -e "  查看 Nginx 日志: ${BLUE}sudo tail -f /var/log/nginx/voidpoly-access.log${NC}"
echo -e "  重启后端: ${BLUE}sudo systemctl restart voidpoly-api-production${NC}"
echo -e "  重启 Nginx: ${BLUE}sudo systemctl restart nginx${NC}"
echo ""

