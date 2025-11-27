# RankPilot 项目结构

## 1. 项目概述
RankPilot 是一个基于 FastAPI 构建的前后端分离编排系统，支持多数据库、消息队列和任务调度等功能。

## 2. 技术栈
- **后端框架**: FastAPI
- **数据库**: PostgreSQL (asyncpg), Redis, MongoDB
- **消息队列**: RabbitMQ
- **任务调度**: APScheduler
- **部署工具**: Gunicorn, Uvicorn
- **配置管理**: Pydantic Settings, YAML
- **日志管理**: Loguru

## 3. 项目目录结构

```
rank-pilot/
├── build/                  # 构建输出目录
├── config/                 # 配置文件目录
│   └── dev.yaml           # 开发环境配置
├── consumers/              # 消息队列消费者
├── scripts/                # 脚本文件
├── src/                    # 源码主目录
│   ├── api/               # API 路由层
│   │   ├── __init__.py    # 路由注册
│   │   ├── base.py        # 基础路由
│   │   └── common.py      # 公共路由
│   ├── app.py             # 应用创建入口
│   ├── config.py          # 配置加载
│   ├── core/              # 核心组件
│   │   ├── db/            # 数据库连接
│   │   │   ├── db_database.py    # PostgreSQL 连接
│   │   │   ├── db_mongodb.py     # MongoDB 连接
│   │   │   └── db_redis.py       # Redis 连接
│   │   ├── exception/     # 异常处理
│   │   ├── lifespan.py    # 应用生命周期管理
│   │   ├── log/           # 日志配置
│   │   ├── middlewares/   # 中间件
│   │   └── mq/            # 消息队列
│   ├── defined/           # 常量定义
│   ├── models/            # 数据模型
│   ├── scheduler/         # 任务调度
│   ├── schemas/           # 数据模式
│   ├── service/           # 业务逻辑层
│   └── utils/             # 工具函数
├── main.py                # 项目入口文件
├── pyproject.toml         # 项目依赖配置
└── test_main.http         # HTTP 测试文件
```

## 4. 核心模块说明

### 4.1 应用入口 (main.py)
- 初始化日志系统
- 创建 FastAPI 应用实例
- 配置并启动 Uvicorn 服务器

### 4.2 应用创建 (src/app.py)
- 定义 `create_app()` 函数，用于创建和配置 FastAPI 应用
- 配置应用元数据 (标题、描述、版本等)
- 设置异常处理器
- 配置中间件
- 注册路由

### 4.3 配置管理 (src/config.py, config/dev.yaml)
- 使用 Pydantic Settings 加载配置
- 支持从环境变量和 YAML 文件加载配置
- 定义了数据库、FastAPI、Redis、MongoDB 等配置类

### 4.4 API 路由层 (src/api/)
- 采用模块化路由设计
- 支持版本控制
- 包含公共路由和基础路由

### 4.5 核心组件 (src/core/)

#### 4.5.1 数据库连接 (src/core/db/)
- 支持 PostgreSQL、Redis、MongoDB 三种数据库
- 采用单例模式管理连接池
- 实现了健康检查机制

#### 4.5.2 异常处理 (src/core/exception/)
- 定义了自定义异常类
- 实现了全局异常处理器

#### 4.5.3 生命周期管理 (src/core/lifespan.py)
- 管理应用启动和关闭时的资源
- 初始化数据库连接
- 启动健康检查
- 管理任务调度

#### 4.5.4 日志管理 (src/core/log/)
- 使用 Loguru 实现日志功能
- 支持多级别日志
- 支持日志拦截

#### 4.5.5 中间件 (src/core/middlewares/)
- 链路追踪中间件
- 日志中间件
- Prometheus 监控中间件

#### 4.5.6 消息队列 (src/core/mq/)
- 集成 RabbitMQ
- 支持消息发布和订阅

### 4.6 数据模型 (src/models/)
- 定义了数据库表结构
- 使用 SQLModel 实现 ORM

### 4.7 任务调度 (src/scheduler/)
- 基于 APScheduler 实现
- 支持定时任务

### 4.8 业务逻辑层 (src/service/)
- 实现核心业务逻辑
- 与数据访问层交互

### 4.9 工具函数 (src/utils/)
- 提供通用工具函数
- 包含 JSON 编码器、请求上下文、单例模式实现等

## 5. 应用启动流程

```
1. main.py 初始化日志系统
2. 调用 src/app.py 中的 create_app() 函数创建应用
   a. 配置应用元数据
   b. 设置异常处理器
   c. 配置中间件
   d. 注册路由
3. 配置 Uvicorn 服务器
4. 启动 Uvicorn 服务器
5. 应用生命周期管理
   a. 启动时：初始化数据库连接、启动健康检查、启动任务调度
   b. 关闭时：关闭数据库连接、停止任务调度
```

## 6. 配置文件说明

### 6.1 系统配置 (system)
- DEBUG: 是否开启调试模式
- LOG_LEVEL: 日志级别

### 6.2 FastAPI 配置 (FASTAPI_CONFIG)
- TITLE: 应用标题
- DESCRIPTION: 应用描述
- HOST: 监听地址
- PORT: 监听端口
- VERSION: 应用版本

### 6.3 数据库配置 (db)
- REDIS_DB: Redis 配置
- ORM_DB: PostgreSQL 配置

### 6.4 RabbitMQ 配置 (RABBITMQ_CONFIG)
- RABBITMQ_URL: RabbitMQ 连接 URL

## 7. 开发与部署

### 7.1 开发环境
- 使用 Uvicorn 作为开发服务器
- 支持热重载

### 7.2 部署环境
- 使用 Gunicorn + Uvicorn 作为生产服务器
- 支持多进程

## 8. 监控与日志

### 8.1 监控
- 集成 Prometheus 监控
- 支持链路追踪

### 8.2 日志
- 使用 Loguru 实现日志
- 支持多级别日志
- 支持日志文件输出

## 9. 总结

RankPilot 是一个结构清晰、功能完整的 FastAPI 应用，采用了模块化设计，支持多数据库、消息队列和任务调度等功能。项目具有良好的扩展性和可维护性，适合作为各种后端服务的基础框架。