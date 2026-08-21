# Campus AI 开发记录

本文件记录项目的重要工作、验证结果与遗留事项。需求变化记录在 `requirements.md`，架构选择后续单独记录在 `adr/`。

## 2026-08-21：明确通用产品与配置边界

- Campus AI 定位为面向不同学校和来源的通用系统，核心代码和公开文档不绑定具体机构。
- 网站地址、允许域名、账号引用、解析规则和部署端点改为运行时配置；网站、账号、密码、验证码、Cookie 与 Token 不得硬编码。
- Compose 移除默认数据库账号、密码和连接串，缺少 `.env` 配置时直接报错。
- Flutter 移除默认 API 地址，并拒绝缺失、非绝对或内嵌账号密码的服务端 URL。
- 具体来源记录从仓库文档移出，新增通用的 `docs/sources/authenticated-portal.md`。
- 新增 ADR-0005 和 3 项配置策略测试；后端现有 16 项测试通过，Flutter 现有 4 项测试通过。

## 2026-08-21：确认首个实例的认证与部署条件

- 首个私有部署实例使用需要交互验证码的校园门户；机构名称、地址与账号信息只进入私有运行配置。
- 不得自动绕过验证码，采用用户辅助登录与加密会话复用。
- 后端大概率部署在固定 IP 的 Debian 服务器上。
- 会话周期只作为该实例的私有观测数据，通用运行逻辑以来源级失效检测和提醒为准。

## 2026-08-21：完成本机 Docker、Linux 与浏览器运行验证

### 已完成

- 安装后的 Docker 29.7.2、Compose 5.4.0、ADB、JDK 17、clang、CMake、Ninja、pkg-config 与 GTK3 已完成探测。
- 修正 PostgreSQL 18 数据卷挂载点为 `/var/lib/postgresql`，空数据卷可正常初始化。
- 增加一次性 `migrate` 服务，API、Worker、Scheduler 与 Browser Worker 等待迁移完成，消除了首次启动时 Worker 抢先访问未建表数据库的竞态。
- 后端和 Playwright 构建目标均构建成功；Chromium 在 Browser Worker 镜像内实际启动并渲染测试页面。
- API 与 PostgreSQL 健康检查通过；真实 PostgreSQL 队列完成 `fetch_all` 入队、一次消费成功及去重键幂等验证。
- 删除并重建所有容器但保留 Volume 后，验证任务仍可读取，持久化通过。
- Flutter 分析无问题、3 项测试通过，Linux Debug Bundle 构建成功。
- 后端 13 项测试全部通过，覆盖率 76%；Alembic 可在空数据库升级到 `0001`。

### 剩余条件

- Android SDK 尚未安装，故 APK 构建和 ADB 真机连接暂不可执行；FCM 还缺 Firebase 配置、服务账号和 GMS 设备。
- Windows Runner、真实来源、脱敏 AI 标注集与云端 AI 配置仍待提供。
- 本机 Docker 验证数据卷中保留两个验证任务（一个成功、一个不会被生产 Worker 消费的持久化探针）。

## 2026-08-19：完成阶段 0 验证骨架

### 已完成

- 建立 PostgreSQL、FastAPI、Worker、Scheduler 与可选 Browser Worker 的 Compose 编排。
- 实现持久任务、Alembic 数据结构、静态来源、用户辅助登录门户、OpenAI 兼容云端 AI、FCM 和 UnifiedPush 适配层。
- 明确云端 AI API 与 MCP 边界，MCP 不承担模型推理。
- 创建 Windows/Linux/Android Flutter 工程，实现 Material 3 响应式界面、Riverpod 状态、go_router 路由和 Drift 离线缓存。
- 增加 FCM Token 诊断、结构化收件日志、批量发送器和送达指标计算脚本。
- 后端与验证脚本共 13 项测试通过，后端覆盖率 76%；Flutter 静态检查无问题，3 项测试通过。

### 环境阻断与后续输入

- 本机缺少 Docker/Compose、Android SDK/ADB、CMake 和 clang++，安装需要用户在终端授予管理员权限。
- Linux 原生构建已执行到 CMake 检查；Android 真机和 Windows Runner 尚未执行。
- 真实来源、脱敏 AI 标注集、云端 AI 配置、Firebase 配置和 Android 设备仍待提供。

## 2026-08-19：确认基础需求范围

- 用户确认需求草案中的产品方向和基础范围无误。
- `docs/requirements.md` 更新至 0.1.1，状态改为“基础范围已确认”。
- 技术背景、具体信息来源、部署条件和 AI 数据边界仍需在实施前补充。

## 2026-08-19：建立需求草案

### 已完成

- 确立产品目标、MVP 范围、业务流程和边界。
- 定义来源管理、采集、AI 分析、通知、跨端同步和数据管理需求。
- 定义安全、可靠性、性能、Material 3 界面和文档要求。
- 给出 Flutter + Python/FastAPI + PostgreSQL 的建议技术基线。
- 给出验收场景、实施阶段、主要风险和待确认事项。
- 使用 Flutter 与 Firebase 官方文档核对 Windows、Linux、Android、Material 3 和 Android 后台消息相关基线。

### 产出

- `docs/requirements.md` 0.1.0（待用户确认）

### 遗留事项

- 获取用户的技术背景与部署条件，再确认最终技术栈。
- 确认“PC”的具体平台和最低系统版本。
- 获取目标学校门户、认证方式和首批公众号清单。
- 验证公众号的合规、稳定接入方式和 Android 真机推送方案。
