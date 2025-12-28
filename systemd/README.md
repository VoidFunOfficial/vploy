# VoidPoly Systemd 服务配置

本目录包含 VoidPoly 项目的 Linux systemd 服务配置文件和管理脚本，用于实现系统的一键启动和自动维护。

## 📁 文件说明

### 服务单元文件
- `voidpoly-api.service` - API 服务器服务配置
- `voidpoly-worker.service` - Huey 任务队列 Worker 服务配置
- `voidpoly-frontend.service` - 前端开发服务器服务配置

### 管理脚本
- `install.sh` - 服务安装脚本
- `uninstall.sh` - 服务卸载脚本
- `start.sh` - 一键启动所有服务
- `stop.sh` - 一键停止所有服务
- `restart.sh` - 一键重启所有服务
- `status.sh` - 查看服务状态
- `logs.sh` - 查看服务日志

## 🚀 快速开始

### 1. 安装服务

#### 使用 conda 环境（推荐）

```bash
# 激活你的 conda 环境
conda activate your_env_name

# 运行安装脚本
cd /path/to/voidpoly
sudo ./systemd/install.sh
```

安装脚本会自动检测当前激活的 conda 环境，并配置服务使用该环境的 Python。

#### 使用系统 Python

```bash
cd /path/to/voidpoly
sudo ./systemd/install.sh
```

如果未检测到 conda，脚本会自动使用系统 Python。

#### 安装脚本功能

安装脚本会自动：
- 检测 conda 环境或系统 Python 路径
- 检测 npm 路径
- 配置服务文件中的用户、路径和环境变量
- 将服务文件复制到 `/etc/systemd/system/`
- 启用服务开机自启

### 2. 启动服务

```bash
# 方式一：使用管理脚本（推荐）
sudo ./systemd/start.sh

# 方式二：使用 systemctl 命令
sudo systemctl start voidpoly-api voidpoly-worker voidpoly-frontend
```

### 3. 查看服务状态

```bash
# 方式一：使用管理脚本（推荐）
sudo ./systemd/status.sh

# 方式二：使用 systemctl 命令
sudo systemctl status voidpoly-api voidpoly-worker voidpoly-frontend
```

### 4. 查看日志

```bash
# 方式一：使用日志查看工具（推荐）
sudo ./systemd/logs.sh

# 方式二：使用 journalctl 命令
sudo journalctl -u voidpoly-api -f
sudo journalctl -u voidpoly-worker -f
sudo journalctl -u voidpoly-frontend -f

# 查看所有服务日志
sudo journalctl -u voidpoly-api -u voidpoly-worker -u voidpoly-frontend -f
```

### 5. 停止服务

```bash
# 方式一：使用管理脚本（推荐）
sudo ./systemd/stop.sh

# 方式二：使用 systemctl 命令
sudo systemctl stop voidpoly-api voidpoly-worker voidpoly-frontend
```

### 6. 重启服务

```bash
# 方式一：使用管理脚本（推荐）
sudo ./systemd/restart.sh

# 方式二：使用 systemctl 命令
sudo systemctl restart voidpoly-api voidpoly-worker voidpoly-frontend
```

### 7. 卸载服务

```bash
sudo ./systemd/uninstall.sh
```

## ⚙️ 服务配置特性

### 自动重启
所有服务配置了自动重启机制：
- 进程崩溃后 10 秒自动重启
- 5 分钟内最多重启 5 次
- 超过限制后停止重启，防止无限循环

### 服务依赖
服务按以下顺序启动：
1. `voidpoly-api.service` - API 服务器（基础服务）
2. `voidpoly-worker.service` - Huey Worker（依赖 API）
3. `voidpoly-frontend.service` - 前端服务器（依赖 API）

### 日志管理
- 所有日志输出到 systemd journal
- 使用 `journalctl` 命令查看日志
- 支持日志过滤、搜索和实时查看

### 资源限制
- 文件描述符限制：65536
- 进程数限制：4096

### 优雅关闭
- 停止超时时间：30-60 秒
- 使用 SIGTERM 信号优雅关闭
- 超时后使用 SIGKILL 强制终止

## 📊 服务端口

- **API 服务器**: `http://localhost:5000`
- **前端界面**: `http://localhost:3000`

## 🔧 常用命令

```bash
# 启动单个服务
sudo systemctl start voidpoly-api

# 停止单个服务
sudo systemctl stop voidpoly-api

# 重启单个服务
sudo systemctl restart voidpoly-api

# 查看单个服务状态
sudo systemctl status voidpoly-api

# 启用开机自启
sudo systemctl enable voidpoly-api

# 禁用开机自启
sudo systemctl disable voidpoly-api

# 查看服务日志（最近 100 行）
sudo journalctl -u voidpoly-api -n 100

# 查看服务日志（实时）
sudo journalctl -u voidpoly-api -f

# 查看服务日志（指定时间范围）
sudo journalctl -u voidpoly-api --since "2024-01-01" --until "2024-01-02"

# 重新加载 systemd 配置
sudo systemctl daemon-reload
```

## 🛠️ 故障排查

### 服务无法启动

1. 检查服务状态：
```bash
sudo systemctl status voidpoly-api
```

2. 查看详细日志：
```bash
sudo journalctl -u voidpoly-api -n 50
```

3. 检查配置文件：
```bash
sudo systemctl cat voidpoly-api
```

### 服务频繁重启

1. 查看重启历史：
```bash
sudo journalctl -u voidpoly-api | grep "Started\|Stopped"
```

2. 检查错误日志：
```bash
sudo journalctl -u voidpoly-api -p err
```

### 端口被占用

```bash
# 查看端口占用
sudo netstat -tlnp | grep 5000
sudo netstat -tlnp | grep 3000

# 或使用 ss 命令
sudo ss -tlnp | grep 5000
```

## 📝 注意事项

1. **权限要求**：所有管理脚本需要 root 权限（使用 `sudo` 运行）
2. **conda 环境**：
   - 安装前请先激活要使用的 conda 环境
   - 脚本会自动检测并配置 conda 环境的 Python 和 PATH
   - 如果未激活环境，脚本会提示选择环境名称
3. **Python 依赖**：确保已安装所有依赖（`pip install -r requirements.txt`）
4. **Node.js 环境**：确保已安装前端依赖（`cd frontend && npm install`）
5. **生产环境**：建议使用 Gunicorn 或 uWSGI 替代 Flask 开发服务器
6. **前端构建**：生产环境建议使用 `npm run build` 构建静态文件并使用 Nginx 提供服务

## 🔐 安全建议

1. 使用非 root 用户运行服务
2. 配置防火墙规则限制访问
3. 使用反向代理（如 Nginx）处理外部请求
4. 定期更新依赖包
5. 配置日志轮转避免磁盘占满

## 📚 参考资料

- [systemd 官方文档](https://www.freedesktop.org/software/systemd/man/)
- [systemd.service 手册](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [journalctl 手册](https://www.freedesktop.org/software/systemd/man/journalctl.html)

