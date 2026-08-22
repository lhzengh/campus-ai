# Campus AI 开发记录

本文件记录项目的重要工作、验证结果与遗留事项。需求变化记录在 `requirements.md`，架构选择后续单独记录在 `adr/`。

## 2026-08-22：补齐生产核心代码英文注释

- 为 Core、Connector SDK、两个官方 Connector 和 Flutter 手写业务代码补充简短英文注释；覆盖模块职责、公共接口以及安全、缓存、认证、游标、任务轮询和路由层级等非显然逻辑。
- 共更新 34 个 Python 文件和 19 个 Dart 文件；审计确认纳入范围的全部 Python 模块、Python 公共类型/方法和手写 Dart 文件均有职责说明。
- 注释只说明职责和设计原因，不逐行复述实现；生成代码、平台模板、数据库迁移和测试文件不在本轮范围内。本轮不修改运行逻辑、协议或 API。
- 43 项 Python 测试通过，Core 综合覆盖率 78%；Flutter 静态分析无问题，13 项测试通过，Linux Release Bundle 构建成功。

## 2026-08-22：修正 Flutter 层级导航与页面动画

- Inbox、Sources 和 Settings 保持为顶层目的地；消息详情、来源创建和来源编辑改用可返回的下钻路由栈。
- 下钻页面使用 280ms 水平滑入、240ms 反向滑出；父页面同步向左退出，并由不透明页面表面避免过渡期间出现旧页面残影。
- 修复 `Back to inbox` 在通过替换式导航进入详情后触发 `There is nothing to pop` 的问题；直接链接进入详情或来源表单时回退到对应顶层页面。
- Flutter 静态分析无问题，13 项测试通过；Linux Release Bundle 构建成功并完成真实 Core 演示联调。

## 2026-08-21：完成 Core Phase 1 来源生命周期与来源级调度

### 已完成

- Core 新增来源读取、编辑、启停、连接检查、异步限量预览、软归档和恢复接口；Connector ID 与固定版本不可在原来源上更换。
- 来源归档会停止调度、清除 Core 凭据引用并保留历史消息、分析和任务；恢复后的来源保持停用。该决定记录于 ADR-0007。
- 全局定时任务改为数据库驱动的来源级 `manual` / `daily` 计划，使用 IANA 时区和下一次 UTC 时间；Scheduler 每分钟扫描并以来源和计划时刻去重，停机后最多补跑一次。
- Job 新增开始/结束时间、耗时和结构化结果；同步记录新增、更新、未变化与分页统计，预览最多返回 10 条裁剪消息且不写入消息或推进游标。
- Flutter 完成来源编辑、启停、计划设置、连接检查、预览、任务结果、归档筛选与恢复；英文仍为完整回退，中文只作为展示层。
- 数据库新增 `0004` 迁移；带现有来源的 `0003` SQLite 数据库已实际升级验证，历史来源获得兼容默认计划。

### 验证结果

- SDK、Connector 与 Core 共 43 项 Python 测试通过，综合覆盖率 77%。
- Flutter 静态分析无问题，12 项测试通过，新增接口编解码、编辑回填和归档恢复测试。
- Flutter Linux Debug Bundle 构建成功；Compose 配置使用一次性测试环境变量解析通过。
- 隔离 Compose 栈实际升级到 `0004` 并启动 API、Worker、Scheduler、PostgreSQL 和静态 Connector。通过本地无害 HTML Fixture 验证连接检查、预览结果、预览不落库、手动同步统计、daily 下一次时间、归档隐藏、历史消息保留和恢复后停用。
- 真链路发现 Compose Worker 允许任务列表漏掉 `preview_source`，已修复并增加配置策略测试；临时容器、网络、PostgreSQL Volume 和 Fixture 文件均已删除，测试镜像缓存保留。

### 后续

- 在目标 Debian 服务器连续运行至少七天，验证真实来源的时区调度、认证失效和诊断记录。
- 下一阶段实现外部 Secret 管理与规则优先的云端 AI 分析闭环，再接设备认证和通知策略。

## 2026-08-21：打通 Flutter Connector 来源管理闭环

### 已完成

- Flutter 新增 Sources 导航、Connector 可用性列表、来源创建和状态卡片，所有 Connector 操作继续只经过 Core Client API。
- Client 根据 Connector Manifest 的 JSON Schema 生成 Material 3 配置表单；首批支持字符串、HTTP(S) URL、数字、整数、布尔值、枚举、字符串列表、必填约束和默认值。
- `x-campus-secret` 字段不进入普通配置；不支持的 Schema 类型显示阻断性错误，不会静默丢弃第三方字段。
- 实现通用认证挑战界面，可表达密码、短信码、普通文本、布尔确认、扫码/浏览器说明和外部登录链接；挑战响应不写入本地缓存。
- 实现来源认证状态检查、人工认证、手动同步和单任务轮询；Core 新增 `GET /v1/jobs/{job_id}`。
- Flutter 消息解析与 `CampusItem` Client API 字段对齐，同时保留 Phase 0 旧字段读取兼容。
- 客户端英文作为完整兼容回退，中文作为可选展示语言；未知系统语言回退英文，协议标识和配置键不本地化。
- Compose Worker 显式合并公共 Backend 环境，修复服务级 `environment` 覆盖导致 Worker 丢失 Connector 注册表的问题，并增加回归测试。

### 验证结果

- 37 项 Python 测试通过；Flutter 静态分析无问题，9 项 Flutter 测试通过。
- 隔离 Compose 栈通过本地无害 HTML Fixture 创建静态来源；认证状态为 `not_required`，手动任务经新单任务接口从 `pending` 变为 `succeeded`。
- Connector 输出的 `Course registration` 消息以标准 `source_url` / `content_text` 字段入库并可由 Client API 读取；第二次同步成功且消息仍只有一条。
- 真链路测试发现并修复 Worker Connector 环境继承问题；临时容器、网络和 PostgreSQL Volume 已删除，不包含真实站点或凭据。

### 后续

- 使用私有运行配置并由用户在场验证真实认证门户，不把网址、账号或会话写入仓库。
- 安装 Android SDK 并完成 FCM 真机测试；随后验证云端 AI 脱敏样本和 Debian 部署。

## 2026-08-21：定义 Core 标准输入格式

- Core 标准输入确定为版本化 `CampusItemBatch` / `CampusItem`，不直接接收学校页面结构或数据库模型。
- Connector 只输出稳定外部 ID、原始标题和正文、原文地址、明确的发布者/时间、附件事实与命名空间扩展；Core 生成数据库 ID、抓取时间、内容指纹、AI 结果和通知状态。
- `(source_id, external_id)` 是幂等键；游标仅在整批持久化成功后提交，同 ID 内容改变才重新分析。
- 登录受限附件使用 `connector_fetch` 不透明引用，来源会话仍由 Connector 持有。
- 密码、验证码、Cookie、浏览器状态、令牌和带凭据 URL 禁止进入 Item、附件、扩展、警告或游标。
- 完整规范记录在 `docs/connectors/campus-item-contract.md`；实现工作位于 `feature/campus-item-contract`。
- SDK、OpenAPI、两个示例 Connector、Core HTTP 客户端、数据库映射和 Client API 已统一使用新字段；旧 Python 类型名仅保留临时迁移别名，旧序列化字段不再接受。
- 数据库新增 `0003` 迁移，拆分信息类型、来源 URL、纯文本/富文本、发布者、来源更新时间、附件和扩展；内容哈希不再错误地去重不同外部 ID。
- 36 项 Python 测试通过，综合覆盖率 73%；OpenAPI、编译、Compose 配置和 `0002` 旧数据升级均通过。
- 三个 Docker 镜像重新构建成功；隔离 Compose 栈确认 Core 就绪、Connector 可发现、PostgreSQL 位于 `0003`，真实 `/v1/sync` 返回带 `contract_version: 1.0` 的标准批次。验证容器、网络和数据库卷已删除。

## 2026-08-21：建立独立 Connector 平台边界

### 已完成

- 需求文档升级到 0.2.0，明确 Monorepo 下 Client、Core、Connector SDK 和 Connector 的可拆分边界。
- 新增 ADR-0006、语言无关的 Connector OpenAPI 契约和 Connector 开发指南。
- 新增独立 Python Connector SDK，包含 Manifest、配置校验、认证状态/挑战、统一消息、增量批次、标准错误、FastAPI 服务包装器和兼容性测试。
- 将静态 HTTP 与 Playwright 实现从 Core 移入两个独立包和 Docker 镜像；Core 不再依赖 Playwright、selectolax 或具体 Connector 实现。
- Core 新增运行时端点注册、内部 Bearer Token、Manifest ID/版本/协议检查、统一同步任务和 Connector 驱动的来源 API。
- 数据库迁移到 `0002`，来源使用 `connector_id`、实现版本、游标、认证状态、凭据引用、最近成功时间和错误字段，不再使用 Core 内部 `kind` 分支。
- 新增域名白名单、跨域重定向阻断、浏览器子请求限制、实例 ID 哈希路径和 Connector 自有加密会话。
- 按用户要求在协议、安全、游标和故障隔离等非显然代码处补充简短英文注释。
- Git 工作流改为功能分支开发；本次工作位于 `feature/connector-platform`。

### 验证结果

- 27 项 Python 测试通过，SDK、两个 Connector 和 Core 综合覆盖率 71%。
- 空 SQLite 数据库成功迁移到 `0002`；Compose 配置校验通过。
- Core、静态 Connector、浏览器 Connector 三个镜像均实际构建成功。
- 浏览器 Connector 镜像内 Chromium 实际启动并渲染页面；Core 镜像确认不包含 Playwright。
- 隔离 Compose 栈完成 PostgreSQL、迁移、静态 Connector、API、Worker 和 Scheduler 健康启动。
- Core 使用内部 Token 成功读取静态 Connector Manifest，并将未启动的浏览器 Connector 标记为 `unavailable`，未影响健康 Connector。
- 通过 Core API 创建并读取经过 Connector Schema 规范化的临时来源；验证栈、临时数据库卷和三个中断构建容器已删除。

### 后续

- Flutter 尚未实现根据 Connector Schema 生成来源配置表单和认证挑战界面。
- 真实门户用户辅助登录、云端 AI 样本、FCM 真机、Windows 构建与 Debian 部署仍待验证。

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
