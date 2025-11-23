# VoidPoly 管理面板

基于 Vue.js 的 Polymarket 自动化交易系统管理面板。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vue Router** - 官方路由管理器
- **Axios** - HTTP 客户端
- **Vite** - 下一代前端构建工具

## 设计风格

参考宝塔面板（BT Panel）的经典设计风格：
- ✅ 简洁的平面设计（Flat Design）
- ✅ 使用纯色，不使用渐变
- ✅ 无动画效果
- ✅ 界面简约、专业

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口
│   │   ├── request.js    # HTTP 请求封装
│   │   └── auth.js       # 认证 API
│   ├── assets/           # 静态资源
│   │   └── styles/       # 样式文件
│   │       └── global.css # 全局样式
│   ├── router/           # 路由配置
│   │   └── index.js      # 路由定义
│   ├── utils/            # 工具函数
│   │   └── auth.js       # 认证工具
│   ├── views/            # 页面组件
│   │   ├── Login.vue     # 登录页面
│   │   └── Dashboard.vue # 仪表板页面
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
└── package.json          # 项目配置
```

## 快速开始

### 1. 安装后端依赖

```bash
# 安装 API 服务器依赖
pip install -r backend/requirements_api.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 启动服务

**方式一：使用启动脚本（推荐）**

```bash
# Windows
start_admin.bat
```

**方式二：手动启动**

```bash
# 终端 1 - 启动后端 API 服务器
python run_api_server.py

# 终端 2 - 启动前端开发服务器
cd frontend
npm run dev
```

### 4. 访问系统

- 前端界面: http://localhost:3000
- 后端 API: http://localhost:5000

### 5. 登录

- 用户名：`admin`
- 密码：`admin123`

## 构建生产版本

```bash
cd frontend
npm run build
```

## 功能特性

### 已实现

- ✅ 用户登录
- ✅ 会话管理
- ✅ 路由守卫
- ✅ 令牌认证

### 待开发

- [ ] 系统配置管理
- [ ] 交易策略配置
- [ ] 实时交易监控
- [ ] 日志查看
- [ ] 用户管理

## 注意事项

- 所有代码注释使用中文
- 遵循简约设计原则
- 不使用渐变色和动画效果
- 保持界面专业、简洁

