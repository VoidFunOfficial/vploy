# VoidPoly Systemd 服务快速开始指南

## 📋 前置要求

1. **Linux 系统**（支持 systemd）
2. **conda 环境**（推荐）或系统 Python 3.x
3. **Node.js 和 npm**
4. **sudo 权限**

## 🚀 5 分钟快速部署

### 步骤 1：激活 conda 环境

```bash
# 激活你的 conda 环境
conda activate your_env_name

# 验证 Python 环境
python --version
which python
```

### 步骤 2：安装依赖

```bash
# 进入项目目录
cd /path/to/voidpoly

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 步骤 3：安装系统服务

```bash
# 运行安装脚本（保持 conda 环境激活状态）
sudo ./systemd/install.sh
```

安装过程中会显示：
- 检测到的 conda 环境名称
- Python 路径和版本
- npm 路径
- 服务文件安装位置

### 步骤 4：启动服务

```bash
# 启动所有服务
sudo ./systemd/start.sh
```

### 步骤 5：验证服务

```bash
# 查看服务状态
sudo ./systemd/status.sh

# 或使用 systemctl
sudo systemctl status voidpoly-api voidpoly-worker voidpoly-frontend
```

## 🌐 访问系统

服务启动后，可以通过以下地址访问：

- **前端管理界面**: http://localhost:3000
- **后端 API**: http://localhost:5000

默认登录账号：
- 用户名：`admin`
- 密码：`admin123`

## 📊 常用操作

### 查看日志

```bash
# 使用日志查看工具（交互式）
sudo ./systemd/logs.sh

# 或直接查看特定服务日志
sudo journalctl -u voidpoly-api -f
sudo journalctl -u voidpoly-worker -f
sudo journalctl -u voidpoly-frontend -f
```

### 重启服务

```bash
# 重启所有服务
sudo ./systemd/restart.sh

# 或重启单个服务
sudo systemctl restart voidpoly-api
```

### 停止服务

```bash
# 停止所有服务
sudo ./systemd/stop.sh
```

## 🔧 故障排查

### 问题 1：服务启动失败

```bash
# 查看详细错误信息
sudo journalctl -u voidpoly-api -n 50

# 检查服务配置
sudo systemctl cat voidpoly-api
```

### 问题 2：Python 模块找不到

这通常是因为 conda 环境配置不正确。解决方法：

```bash
# 1. 卸载服务
sudo ./systemd/uninstall.sh

# 2. 重新激活 conda 环境
conda activate your_env_name

# 3. 验证依赖
python -c "import flask; import huey; print('依赖正常')"

# 4. 重新安装服务
sudo ./systemd/install.sh
```

### 问题 3：端口被占用

```bash
# 检查端口占用
sudo netstat -tlnp | grep 5000
sudo netstat -tlnp | grep 3000

# 或使用 ss 命令
sudo ss -tlnp | grep 5000
```

### 问题 4：权限问题

确保服务以正确的用户运行：

```bash
# 检查服务配置中的用户
sudo systemctl cat voidpoly-api | grep User

# 检查项目目录权限
ls -la /path/to/voidpoly
```

## 🔄 更新服务配置

如果修改了服务配置文件，需要重新加载：

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 重启服务
sudo systemctl restart voidpoly-api voidpoly-worker voidpoly-frontend
```

## 🗑️ 卸载服务

```bash
# 停止并卸载所有服务
sudo ./systemd/uninstall.sh
```

## 💡 高级配置

### 修改服务端口

编辑 `run_api_server.py` 修改 API 端口：
```python
app.run(host='0.0.0.0', port=5000, debug=True)  # 修改 port 参数
```

编辑 `frontend/vite.config.js` 修改前端端口：
```javascript
server: {
  port: 3000,  // 修改此处
  ...
}
```

修改后需要重启服务。

### 配置开机自启

服务安装后默认已启用开机自启。如需禁用：

```bash
sudo systemctl disable voidpoly-api voidpoly-worker voidpoly-frontend
```

重新启用：

```bash
sudo systemctl enable voidpoly-api voidpoly-worker voidpoly-frontend
```

## 📚 更多信息

详细文档请参考：[README.md](./README.md)

