#!/bin/bash

# VoidPoly Nginx 一键配置脚本
# 用于生产环境部署

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}VoidPoly Nginx 一键配置脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 root 权限运行此脚本${NC}"
    echo "使用: sudo $0"
    exit 1
fi

# 获取当前用户和工作目录
CURRENT_USER=${SUDO_USER:-$USER}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}[1/7] 检查 Nginx 是否已安装...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Nginx 未安装，正在安装...${NC}"
    apt-get update
    apt-get install -y nginx
else
    echo -e "${GREEN}✓ Nginx 已安装${NC}"
fi

echo ""
echo -e "${YELLOW}[2/7] 构建前端静态文件...${NC}"
cd "$WORKDIR/frontend"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}安装前端依赖...${NC}"
    npm install
fi
echo -e "${YELLOW}执行构建...${NC}"
npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}错误: 构建失败，dist 目录不存在${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 前端构建完成${NC}"

echo ""
echo -e "${YELLOW}[3/7] 配置 Nginx...${NC}"
# 替换配置文件中的占位符
sed "s|%WORKDIR%|$WORKDIR|g" "$SCRIPT_DIR/nginx/voidpoly.conf" > /tmp/voidpoly.conf

# 复制配置文件
cp /tmp/voidpoly.conf /etc/nginx/sites-available/voidpoly.conf

# 创建软链接
if [ -f /etc/nginx/sites-enabled/voidpoly.conf ]; then
    rm /etc/nginx/sites-enabled/voidpoly.conf
fi
ln -s /etc/nginx/sites-available/voidpoly.conf /etc/nginx/sites-enabled/voidpoly.conf

# 删除默认配置（可选）
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo -e "${YELLOW}删除默认 Nginx 配置...${NC}"
    rm /etc/nginx/sites-enabled/default
fi

echo -e "${GREEN}✓ Nginx 配置完成${NC}"

echo ""
echo -e "${YELLOW}[4/7] 测试 Nginx 配置...${NC}"
nginx -t
echo -e "${GREEN}✓ Nginx 配置测试通过${NC}"

echo ""
echo -e "${YELLOW}[5/7] 创建日志目录...${NC}"
mkdir -p /var/log/nginx
mkdir -p /var/log/voidpoly
chown -R www-data:www-data /var/log/nginx
echo -e "${GREEN}✓ 日志目录创建完成${NC}"

echo ""
echo -e "${YELLOW}[6/7] 重启 Nginx 服务...${NC}"
systemctl restart nginx
systemctl enable nginx
echo -e "${GREEN}✓ Nginx 服务已启动并设置为开机自启${NC}"

echo ""
echo -e "${YELLOW}[7/7] 检查服务状态...${NC}"
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx 运行正常${NC}"
else
    echo -e "${RED}✗ Nginx 启动失败${NC}"
    systemctl status nginx
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Nginx 配置完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "访问地址: ${GREEN}http://$(hostname -I | awk '{print $1}')${NC}"
echo -e "或: ${GREEN}http://localhost${NC}"
echo ""
echo -e "常用命令:"
echo -e "  查看状态: ${YELLOW}sudo systemctl status nginx${NC}"
echo -e "  重启服务: ${YELLOW}sudo systemctl restart nginx${NC}"
echo -e "  查看日志: ${YELLOW}sudo tail -f /var/log/nginx/voidpoly-access.log${NC}"
echo -e "  测试配置: ${YELLOW}sudo nginx -t${NC}"
echo ""
echo -e "${YELLOW}注意: 确保后端 API 服务正在运行！${NC}"
echo -e "启动后端: ${YELLOW}sudo systemctl start voidpoly-api-production${NC}"
echo ""

