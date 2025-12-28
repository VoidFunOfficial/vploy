# VoidPoly Nginx 配置说明

## 概述

生产环境使用 Nginx 作为 Web 服务器，提供以下功能：
- 托管前端静态文件（Vue.js 构建产物）
- 反向代理后端 API 请求
- Gzip 压缩
- 静态资源缓存
- WebSocket 支持

## 快速部署

### 一键部署（推荐）

```bash
cd systemd
sudo chmod +x deploy-production.sh
sudo ./deploy-production.sh
```

这个脚本会自动完成：
1. 安装 Nginx 和 Gunicorn
2. 构建前端静态文件
3. 配置 Nginx
4. 配置并启动后端 API 服务
5. 启动 Nginx

### 仅配置 Nginx

```bash
cd systemd
sudo chmod +x setup-nginx.sh
sudo ./setup-nginx.sh
```

## 手动配置

### 1. 构建前端

```bash
cd frontend
npm install
npm run build
```

### 2. 安装 Nginx

```bash
sudo apt-get update
sudo apt-get install nginx
```

### 3. 配置 Nginx

```bash
# 复制配置文件（需要先替换 %WORKDIR% 为实际路径）
sudo cp systemd/nginx/voidpoly.conf /etc/nginx/sites-available/voidpoly.conf

# 创建软链接
sudo ln -s /etc/nginx/sites-available/voidpoly.conf /etc/nginx/sites-enabled/

# 删除默认配置（可选）
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 4. 启动后端 API

```bash
sudo systemctl start voidpoly-api-production
```

## 配置文件说明

### voidpoly.conf

主要配置项：
- **监听端口**: 80 (HTTP)
- **静态文件路径**: `%WORKDIR%/frontend/dist`
- **API 代理**: `/api/` -> `http://127.0.0.1:5000`
- **WebSocket**: `/ws/` -> `http://127.0.0.1:5000`

### 缓存策略

- **静态资源** (js/css/图片): 缓存 1 年
- **HTML 文件**: 不缓存
- **API 请求**: 不缓存

## 常用命令

```bash
# 查看 Nginx 状态
sudo systemctl status nginx

# 重启 Nginx
sudo systemctl restart nginx

# 重新加载配置（不中断服务）
sudo systemctl reload nginx

# 测试配置文件
sudo nginx -t

# 查看访问日志
sudo tail -f /var/log/nginx/voidpoly-access.log

# 查看错误日志
sudo tail -f /var/log/nginx/voidpoly-error.log
```

## 故障排查

### Nginx 启动失败

```bash
# 查看详细错误
sudo systemctl status nginx
sudo journalctl -u nginx -n 50

# 检查配置文件
sudo nginx -t
```

### 502 Bad Gateway

原因：后端 API 服务未启动或无法连接

```bash
# 检查后端服务
sudo systemctl status voidpoly-api-production

# 启动后端服务
sudo systemctl start voidpoly-api-production
```

### 静态文件 404

原因：前端未构建或路径配置错误

```bash
# 检查 dist 目录是否存在
ls -la frontend/dist

# 重新构建
cd frontend && npm run build
```

## HTTPS 配置（可选）

使用 Let's Encrypt 免费证书：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书并自动配置
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

## 性能优化

### 1. 启用 HTTP/2

在 `listen` 指令后添加 `http2`：
```nginx
listen 443 ssl http2;
```

### 2. 调整 Worker 进程

编辑 `/etc/nginx/nginx.conf`：
```nginx
worker_processes auto;
worker_connections 2048;
```

### 3. 启用缓存

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g;
```

## 架构说明

```
客户端请求
    ↓
Nginx (80端口)
    ├─ / → 前端静态文件 (frontend/dist)
    ├─ /api/ → 反向代理到后端 (127.0.0.1:5000)
    └─ /ws/ → WebSocket 代理
         ↓
Gunicorn (4 workers)
    ↓
Flask 应用
```

